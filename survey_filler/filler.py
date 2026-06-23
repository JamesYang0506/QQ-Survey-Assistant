"""
问卷填写主控制器 - 整合解析、匹配、填充的完整流程

被 main.py 或 MonitorTab 调用（检测到问卷链接时）
使用 Playwright 控制浏览器完成自动填写

依赖: parser.py (所有解析器统一返回容器作为 raw_element)
"""
import asyncio
import logging
from datetime import datetime
from typing import Optional, Callable

from profiles.manager import ProfileManager
from .parser import SurveyParser, Question, QuestionType, describe_questions
from .matcher import QuestionMatcher
from .submitter import SurveySubmitter, FillResult, HistoryRecorder

logger = logging.getLogger("QQSurveyAssistant.Filler")


class SurveyFiller:
    """问卷自动填写器"""

    def __init__(self, profile_manager: ProfileManager,
                 headless: bool = False,
                 fill_delay_ms: int = 500):
        self._pm = profile_manager
        self._headless = headless
        self._fill_delay = fill_delay_ms
        self._parser = SurveyParser()
        self._matcher = QuestionMatcher()
        self._submitter = SurveySubmitter()
        self._recorder = HistoryRecorder()

        self._on_log: Optional[Callable[[str], None]] = None
        self._on_question_filled: Optional[Callable[[int, int, str], None]] = None
        self._on_finished: Optional[Callable[[FillResult], None]] = None

    def set_callbacks(self, on_log=None, on_question_filled=None, on_finished=None):
        self._on_log = on_log
        self._on_question_filled = on_question_filled
        self._on_finished = on_finished

    def _log(self, msg: str):
        logger.info(msg)
        if self._on_log:
            self._on_log(msg)

    async def fill_survey(self, url: str, auto_submit: bool = False,
                          browser=None) -> FillResult:
        """
        填写一个问卷。

        Args:
            url: 问卷链接
            auto_submit: 是否自动提交
            browser: 可复用的Playwright Browser对象

        Returns: FillResult
        """
        profile = self._pm.active_profile
        if profile is None:
            return FillResult(
                success=False, url=url,
                error_message="没有可用的预设信息",
                timestamp=datetime.now().isoformat()
            )

        result = FillResult(
            url=url, profile_name=profile.name,
            timestamp=datetime.now().isoformat()
        )

        self._log(f"开始填写问卷: {url}")
        self._log(f"使用预设: {profile.name}")

        own_browser = False
        playwright = None

        try:
            if browser is None:
                from playwright.async_api import async_playwright
                playwright = await async_playwright().start()
                browser = await playwright.chromium.launch(headless=self._headless)
                own_browser = True

            context = await browser.new_context(
                viewport={"width": 1280, "height": 900},
                user_agent=(
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/120.0.0.0 Safari/537.36"
                )
            )
            page = await context.new_page()

            self._log("正在加载问卷页面...")
            await page.goto(url, wait_until="networkidle", timeout=30000)
            await page.wait_for_timeout(2000)

            # 解析问卷
            self._log("解析问卷结构...")
            questions = await self._parser.parse(page)
            result.fields_total = len(questions)

            self._log(f"检测到 {len(questions)} 个题目:")
            self._log(describe_questions(questions))

            # 逐个填写
            filled_count = 0
            for q in questions:
                try:
                    info = await self._fill_question(page, q, profile)
                    if info:
                        filled_count += 1
                        self._log(f"  [{q.index}] ✓ {q.title[:30]}... → {info}")
                        if self._on_question_filled:
                            self._on_question_filled(q.index, len(questions), info)
                    else:
                        self._log(f"  [{q.index}] ? {q.title[:30]}... → 未匹配")
                except Exception as e:
                    self._log(f"  [{q.index}] ✗ {q.title[:30]}... → 失败: {e}")
                    logger.warning(f"填写题目{q.index}失败: {e}", exc_info=True)

            result.fields_filled = filled_count
            self._log(f"填写完成: {filled_count}/{len(questions)}")

            if auto_submit:
                self._log("自动提交问卷...")
                result = await self._submitter.submit(page, result)
                if result.success:
                    self._log(f"提交成功! 截图: {result.screenshot_path}")
                else:
                    self._log(f"提交异常: {result.error_message}")
            else:
                result.success = True
                self._log("手动模式: 请在浏览器中确认后手动提交")

            self._recorder.add(result)

            if self._on_finished:
                self._on_finished(result)

            # 浏览器始终保留，方便手动确认和修改
            self._log("浏览器保持打开，可手动确认或修改后提交")

        except Exception as e:
            logger.error(f"填写问卷出错: {e}", exc_info=True)
            result.success = False
            result.error_message = str(e)
            if self._on_finished:
                self._on_finished(result)

        return result

    # ===== 填写单个题目 =====

    async def _fill_question(self, page, q: Question, profile) -> Optional[str]:
        if q.is_choice_question():
            return await self._fill_choice_question(page, q, profile)
        elif q.is_fill_question():
            return await self._fill_text_question(page, q, profile)
        elif q.is_matrix_question():
            return await self._fill_matrix_question(page, q, profile)
        return None

    async def _fill_choice_question(self, page, q: Question, profile) -> Optional[str]:
        """填写选择题（单选/多选/下拉）"""
        el = q.raw_element  # 容器

        # DesktopSelect 特殊处理 — 选项不在 DOM 中，需先匹配字段再点击下拉
        if q.type == QuestionType.SELECT and q.input_type == "desktop_select":
            field_result = self._matcher.find_best_field(q, profile)
            if not field_result:
                return None
            answer = field_result[1]
            await self._fill_desktop_select(page, el, answer)
            await page.wait_for_timeout(self._fill_delay)
            return f"选择 → {answer}"

        # 找答案
        answer = self._matcher.find_best_choice(q, profile)
        if not answer:
            field_result = self._matcher.find_best_field(q, profile)
            if field_result:
                answer = self._matcher.find_best_option_by_keyword(
                    q, field_result[1]
                )
        if not answer:
            return None

        if q.type == QuestionType.SELECT:
            # 原生 <select> 或 Ant Design Select
            native_select = await el.query_selector("select")
            if native_select:
                await native_select.select_option(label=answer)
            elif q.platform == 'jinshuju' and q.field_class:
                await self._fill_antd_select(page, el, answer)
            else:
                return None
        else:
            # 单选/多选：在容器内找 label 并点击
            if q.platform == 'jinshuju' and q.field_class:
                # Ant Design
                wrapper_sel = (
                    'label.ant-radio-wrapper' if q.type == QuestionType.RADIO
                    else 'label.ant-checkbox-wrapper'
                )
                labels = await el.query_selector_all(wrapper_sel) or \
                         await el.query_selector_all("label")
            else:
                labels = await el.query_selector_all("label")

            clicked = False
            for label in labels:
                try:
                    text = (await label.inner_text()).strip()
                    if answer in text or text in answer:
                        await label.click()
                        clicked = True
                        break
                except Exception:
                    continue

            if not clicked:
                return None

        await page.wait_for_timeout(self._fill_delay)
        return f"选择 → {answer}"

    async def _fill_antd_select(self, page, el, answer: str):
        """填写Ant Design Select"""
        trigger = await el.query_selector('.ant-select-selector, .ant-select')
        if trigger:
            await trigger.click()
            await page.wait_for_timeout(600)
            options = await page.query_selector_all(
                '.ant-select-dropdown:not(.ant-select-dropdown-hidden) '
                '.ant-select-item-option'
            )
            for opt in options:
                text = (await opt.inner_text()).strip()
                if answer in text or text in answer:
                    await opt.click()
                    break
            await page.keyboard.press('Escape')
            await page.wait_for_timeout(200)

    async def _fill_desktop_select(self, page, el, answer: str):
        """填写 jsjform DesktopSelect 自定义下拉组件"""
        # 点击触发按钮
        trigger = await el.query_selector(
            '[class*="DesktopSelect-module"][class*="trigger"]'
        )
        if not trigger:
            return

        await trigger.click()
        await page.wait_for_timeout(800)

        # 下拉选项渲染在 body 下的 SelectOptions-module__root 中
        option_items = await page.query_selector_all(
            '[class*="SelectOptions-module"][class*="item"]'
        )
        if not option_items:
            # 备用：通过 role="option" 查找
            option_items = await page.query_selector_all('[role="option"]')

        clicked = False
        for opt in option_items:
            try:
                text = (await opt.inner_text()).strip()
                if answer in text or text in answer:
                    await opt.click()
                    clicked = True
                    break
            except Exception:
                continue

        if not clicked:
            # 关闭下拉
            await page.keyboard.press('Escape')
            await page.wait_for_timeout(200)

    async def _fill_text_question(self, page, q: Question, profile) -> Optional[str]:
        """填写填空题"""
        field_result = self._matcher.find_best_field(q, profile)
        if not field_result:
            return None

        key, value = field_result
        el = q.raw_element  # 容器

        # 在容器中找 input/textarea
        input_el = (await el.query_selector("input")) or \
                   (await el.query_selector("textarea"))
        if not input_el:
            return None

        await input_el.click()
        await page.wait_for_timeout(100)
        await input_el.fill("")
        await input_el.type(value, delay=50)
        await page.wait_for_timeout(self._fill_delay)

        return f"{key} = {value}"

    async def _fill_matrix_question(self, page, q: Question, profile) -> Optional[str]:
        """填写矩阵题"""
        if q.type != QuestionType.MATRIX_RADIO:
            return None

        filled_rows = 0
        el = q.raw_element
        table = await el.query_selector("table")
        if not table:
            return None

        body_rows = await table.query_selector_all("tbody tr, tr")
        for tr in body_rows:
            cells = await tr.query_selector_all("td, th")
            if len(cells) < 2:
                continue
            row_label = (await cells[0].inner_text()).strip()
            if not row_label:
                continue
            for field in profile.fields.values():
                if not field.value:
                    continue
                if field.key in row_label or \
                   any(a in row_label for a in field.aliases):
                    for ci in range(1, len(cells)):
                        col_text = (await cells[ci].inner_text()).strip()
                        if field.value in col_text or col_text in field.value:
                            radio = await cells[ci].query_selector(
                                "input[type='radio']"
                            )
                            if radio:
                                await radio.click()
                                filled_rows += 1
                            break

        if filled_rows > 0:
            await page.wait_for_timeout(self._fill_delay)
            return f"矩阵填写 {filled_rows} 行"
        return None


# 同步包装器 - 供非async环境使用
def fill_survey_sync(url: str, profile_manager: ProfileManager,
                     auto_submit: bool = False,
                     headless: bool = False,
                     fill_delay_ms: int = 500,
                     on_log=None, on_finished=None) -> FillResult:
    """同步方式填写问卷（内部创建事件循环）"""
    filler = SurveyFiller(profile_manager, headless=headless,
                          fill_delay_ms=fill_delay_ms)
    filler.set_callbacks(on_log=on_log, on_finished=on_finished)
    return asyncio.run(filler.fill_survey(url, auto_submit=auto_submit))
