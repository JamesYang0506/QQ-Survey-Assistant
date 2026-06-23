"""
问卷提交与结果记录

被 survey_filler/filler.py 调用
点击提交按钮、处理提交结果、记录填写历史
"""
from dataclasses import dataclass
from datetime import datetime
from typing import Optional
import os


@dataclass
class FillResult:
    """填写结果"""
    success: bool = False
    url: str = ""
    profile_name: str = ""
    timestamp: str = ""
    screenshot_path: str = ""
    error_message: str = ""
    fields_filled: int = 0
    fields_total: int = 0


class SurveySubmitter:
    """问卷提交器"""

    SUBMIT_SELECTORS = [
        # 金数据 (Ant Design)
        "button.ant-btn-primary",
        "button[type='submit']",
        "button:has-text('提交')",
        # 问卷星
        "#submit_button",
        "#ctlNext",
        "input[type='submit']",
        ".submitbutton",
        "#submitBut",
        "a#submit_button",
        "input.submitbutton",
        "input:has-text('提交')",
        # 通用
        "button",
        "input[type='button']",
    ]

    SUCCESS_INDICATORS = [
        "提交成功", "感谢", "报名成功",
        "问卷已提交", "提交完成", "谢谢",
    ]

    @staticmethod
    def get_screenshot_dir() -> str:
        appdata = os.environ.get("APPDATA", os.path.expanduser("~"))
        return os.path.join(appdata, "QQSurveyAssistant", "screenshots")

    async def submit(self, page, fill_result: FillResult) -> FillResult:
        """提交问卷并处理结果"""
        try:
            # 查找并点击提交按钮
            clicked = False
            for selector in self.SUBMIT_SELECTORS:
                btn = await page.query_selector(selector)
                if btn and await btn.is_visible():
                    await btn.click()
                    clicked = True
                    break

            if not clicked:
                fill_result.success = False
                fill_result.error_message = "未找到提交按钮"
                return fill_result

            # 等待页面响应
            await page.wait_for_timeout(2000)

            # 检查是否提交成功
            page_text = await page.inner_text("body")
            success = any(ind in page_text for ind in self.SUCCESS_INDICATORS)

            if success:
                fill_result.success = True
                os.makedirs(self.get_screenshot_dir(), exist_ok=True)
                ts = datetime.now().strftime("%Y%m%d_%H%M%S")
                sp = os.path.join(self.get_screenshot_dir(), f"submit_{ts}.png")
                await page.screenshot(path=sp, full_page=True)
                fill_result.screenshot_path = sp
            else:
                error_el = await page.query_selector(
                    ".error, .warning, .alert, [class*='error'], [class*='warn']"
                )
                if error_el:
                    fill_result.error_message = await error_el.inner_text()
                else:
                    fill_result.error_message = "提交状态未知（可能需手动确认）"
                fill_result.success = False

        except Exception as e:
            fill_result.success = False
            fill_result.error_message = str(e)

        return fill_result


from storage.history_db import HistoryDB


class HistoryRecorder:
    """历史记录器（SQLite存储）"""

    def __init__(self):
        self._db = HistoryDB()

    def add(self, result: FillResult):
        self._db.add_record(
            timestamp=result.timestamp,
            url=result.url,
            profile_name=result.profile_name,
            success=result.success,
            fields_filled=result.fields_filled,
            fields_total=result.fields_total,
            screenshot_path=result.screenshot_path,
            error_message=result.error_message
        )

    def get_all(self) -> list:
        return self._db.get_records()

    def clear(self):
        self._db.clear_all()
