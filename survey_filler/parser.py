"""
表单DOM解析器 - 多平台支持

被 survey_filler/filler.py 调用
支持: 金数据(jinshuju/Ant Design + jsjform field_N)、问卷星(wjx.cn)
通过Playwright page对象解析表单结构

所有解析器统一约定: raw_element 指向一个容器元素（包含 label + input）
"""
from dataclasses import dataclass, field
from typing import List, Optional, Any
from enum import Enum
import logging

logger = logging.getLogger("QQSurveyAssistant.Parser")


class QuestionType(Enum):
    RADIO = "radio"
    CHECKBOX = "checkbox"
    TEXT = "text"
    TEXTAREA = "textarea"
    SELECT = "select"
    MATRIX_RADIO = "matrix_radio"
    MATRIX_CHECKBOX = "matrix_checkbox"
    STAR = "star"
    SORT = "sort"
    UNKNOWN = "unknown"


@dataclass
class QuestionOption:
    text: str
    value: str
    is_other: bool = False


@dataclass
class MatrixRow:
    label: str
    columns: List[str] = field(default_factory=list)
    col_values: List[str] = field(default_factory=list)


@dataclass
class Question:
    id: str
    index: int
    type: QuestionType
    title: str
    is_required: bool = False
    options: List[QuestionOption] = field(default_factory=list)
    matrix_rows: List[MatrixRow] = field(default_factory=list)
    input_type: str = ""
    placeholder: str = ""
    platform: str = ""           # 'jinshuju' | 'wjx' | 'generic'
    raw_element: Any = None      # 容器元素（统一约定）
    api_code: str = ""           # data-api-code 或 field name
    field_class: str = ""        # Ant Design field class name

    def is_choice_question(self) -> bool:
        return self.type in (
            QuestionType.RADIO, QuestionType.CHECKBOX, QuestionType.SELECT,
        )

    def is_fill_question(self) -> bool:
        return self.type in (QuestionType.TEXT, QuestionType.TEXTAREA)

    def is_matrix_question(self) -> bool:
        return self.type in (QuestionType.MATRIX_RADIO, QuestionType.MATRIX_CHECKBOX)


class SurveyParser:
    """多平台表单解析器"""

    @staticmethod
    def _clean_text(text: str) -> str:
        import re
        text = text.strip()
        text = re.sub(r'^[\d]+[\.\、\))\s]+', '', text)
        text = text.replace('*', '').strip()
        return text

    @staticmethod
    def _detect_platform(page) -> str:
        try:
            url = page.url.lower()
            if 'jinshuju.com' in url or 'jinshuju.net' in url or 'jsjform.com' in url:
                return 'jinshuju'
            if 'wjx.cn' in url or 'wjx.top' in url:
                return 'wjx'
        except Exception:
            pass
        return 'generic'

    async def parse(self, page) -> List[Question]:
        """解析表单页面，返回题目列表"""
        platform = self._detect_platform(page)

        if platform == 'jinshuju':
            result = await self._parse_jinshuju(page)
            if not result:
                result = await self._parse_jsjform_fields(page)
            if not result:
                result = await self._parse_generic(page)
            return result
        elif platform == 'wjx':
            return await self._parse_wjx(page)
        else:
            return await self._parse_generic(page)

    # ================================================================
    # 金数据 (Ant Design) 解析 — [data-api-code] 容器
    # ================================================================

    JS_FIELD_SELECTOR = '[data-api-code]'
    JS_FIELD_CLASS_MAP = {
        'NameField': QuestionType.TEXT,
        'TextField': QuestionType.TEXT,
        'MobileField': QuestionType.TEXT,
        'NumberField': QuestionType.TEXT,
        'EmailField': QuestionType.TEXT,
        'TextareaField': QuestionType.TEXTAREA,
        'RadioButton': QuestionType.RADIO,
        'CheckboxButton': QuestionType.CHECKBOX,
        'DropDown': QuestionType.SELECT,
        'DateField': QuestionType.TEXT,
        'TimeField': QuestionType.TEXT,
    }

    async def _parse_jinshuju(self, page) -> List[Question]:
        """解析金数据 Ant Design 表单"""
        questions = []
        containers = await page.query_selector_all(self.JS_FIELD_SELECTOR)

        index = 0
        for el in containers:
            try:
                api_code = (await el.get_attribute('data-api-code')) or ""
                class_str = (await el.get_attribute('class')) or ""

                field_type = self._extract_js_field_type(class_str)
                if field_type == QuestionType.UNKNOWN:
                    continue

                index += 1

                # 提取标题
                label_el = await el.query_selector(
                    '.ant-form-item-label label span.label-item, label span'
                )
                title = (await label_el.inner_text()).strip() if label_el else ""

                # 是否必答
                req_el = await el.query_selector(
                    '.ant-form-item-required, label.ant-form-item-required'
                )
                is_required = req_el is not None

                q = Question(
                    id=api_code,
                    index=index,
                    type=field_type,
                    title=self._clean_text(title),
                    is_required=is_required,
                    platform='jinshuju',
                    raw_element=el,  # ← 容器
                    api_code=api_code,
                    field_class=self._extract_js_field_name(class_str)
                )

                if field_type == QuestionType.RADIO:
                    q.options = await self._parse_js_radio_options(el)
                elif field_type == QuestionType.CHECKBOX:
                    q.options = await self._parse_js_checkbox_options(el)
                elif field_type == QuestionType.SELECT:
                    q.options = await self._parse_js_select_options(page, el)

                questions.append(q)

            except Exception:
                continue

        return questions

    def _extract_js_field_type(self, class_str: str) -> QuestionType:
        for class_name, qtype in self.JS_FIELD_CLASS_MAP.items():
            if class_name in class_str:
                return qtype
        return QuestionType.UNKNOWN

    def _extract_js_field_name(self, class_str: str) -> str:
        for name in self.JS_FIELD_CLASS_MAP:
            if name in class_str:
                return name
        return ""

    async def _parse_js_radio_options(self, el) -> List[QuestionOption]:
        options = []
        labels = await el.query_selector_all('label.ant-radio-wrapper, label')
        for label in labels:
            input_el = await label.query_selector('input[type="radio"]')
            if not input_el:
                continue
            text = (await label.inner_text()).strip()
            value = (await input_el.get_attribute('value')) or ""
            if text:
                options.append(QuestionOption(
                    text=text, value=value,
                    is_other=("其他" in text or "其它" in text)
                ))
        return options

    async def _parse_js_checkbox_options(self, el) -> List[QuestionOption]:
        options = []
        labels = await el.query_selector_all('label.ant-checkbox-wrapper, label')
        for label in labels:
            input_el = await label.query_selector('input[type="checkbox"]')
            if not input_el:
                continue
            text = (await label.inner_text()).strip()
            value = (await input_el.get_attribute('value')) or ""
            if text:
                options.append(QuestionOption(
                    text=text, value=value,
                    is_other=("其他" in text or "其它" in text)
                ))
        return options

    async def _parse_js_select_options(self, page, el) -> List[QuestionOption]:
        options = []
        option_els = await el.query_selector_all('.ant-select-item-option')
        if not option_els:
            select_trigger = await el.query_selector(
                '.ant-select-selector, .ant-select'
            )
            if select_trigger:
                await select_trigger.click()
                await page.wait_for_timeout(500)
                option_els = await page.query_selector_all(
                    '.ant-select-dropdown:not(.ant-select-dropdown-hidden) '
                    '.ant-select-item-option'
                )
        for opt in option_els:
            try:
                text = (await opt.inner_text()).strip()
                if text:
                    options.append(QuestionOption(text=text, value=text))
            except Exception:
                continue
        if option_els:
            await page.keyboard.press('Escape')
            await page.wait_for_timeout(200)
        return options

    # ================================================================
    # 金数据 field_N / jsjform 格式解析
    # 使用 FieldLabel div 匹配字段，而非依赖 name 属性
    # ================================================================

    async def _parse_jsjform_fields(self, page) -> List[Question]:
        """
        解析金数据/jsjform Next.js 表单（ClassicForm / FormField 结构）。

        策略：
        1. 查找所有 FormField-module__SUWzNG__root 容器
        2. 每个容器有唯一的 j-field-field_N class → 精确获取 Playwright 元素
        3. 从 FieldLabel 提取标题，从 inputs 区提取输入控件
        4. 检测 DesktopSelect 自定义下拉组件 → SELECT 类型
        """
        try:
            fields_data = await page.evaluate(r"""
                () => {
                    const roots = document.querySelectorAll(
                        '[class*="FormField-module"][class*="root"]'
                    );
                    if (roots.length === 0) return [];

                    const pairs = [];

                    for (const root of roots) {
                        // 唯一标识：j-field-field_N
                        const jFieldClass = [...root.classList].find(
                            c => c.startsWith('j-field-')
                        );
                        if (!jFieldClass) continue;

                        // 提取标题
                        const labelEl = root.querySelector('[class*="FieldLabel"]');
                        if (!labelEl) continue;
                        const title = labelEl.textContent.trim();
                        if (!title || title.length < 2 || title.length > 80) continue;
                        if (title === '请同学们扫码入群') continue;

                        // 检查是否是 DesktopSelect 自定义下拉
                        const desktopSelectTrigger = root.querySelector(
                            '[class*="DesktopSelect-module"][class*="trigger"]'
                        );
                        const isDesktopSelect = !!desktopSelectTrigger;

                        // 取第一个输入控件确定类型
                        const inputs = root.querySelectorAll(
                            'input:not([type="hidden"]), select, textarea'
                        );
                        if (inputs.length === 0 && !isDesktopSelect) continue;

                        let qtype, name, tag, type, placeholder;

                        if (isDesktopSelect) {
                            qtype = 'select';
                            name = jFieldClass;  // 用 j-field 类名当 ID
                            tag = 'div';  // 非标准控件
                            type = 'desktop_select';
                            placeholder = '请选择';
                        } else {
                            const firstInput = inputs[0];
                            tag = firstInput.tagName.toLowerCase();
                            type = firstInput.getAttribute('type') || 'text';
                            name = firstInput.getAttribute('name') || '';
                            placeholder = firstInput.getAttribute('placeholder') || '';

                            if (tag === 'select') {
                                qtype = 'select';
                            } else if (type === 'radio') {
                                qtype = 'radio';
                            } else if (type === 'checkbox') {
                                qtype = 'checkbox';
                            } else if (tag === 'textarea') {
                                qtype = 'textarea';
                            } else {
                                qtype = 'text';
                            }
                        }

                        // 收集选项
                        let options = [];
                        let allDisabled = true;

                        if (isDesktopSelect) {
                            // DesktopSelect 选项不在 DOM 中（点击后才加载）
                            // 在填充时动态获取
                            options = [];
                        } else if (tag === 'select') {
                            for (const opt of inputs[0].options) {
                                const t = opt.textContent.trim();
                                if (t && t !== '请选择' && t !== '请选择...') {
                                    options.push({text: t, value: opt.value});
                                }
                            }
                        } else if (qtype === 'radio' || qtype === 'checkbox') {
                            // 在根容器内找所有同类型 input
                            const selector = name
                                ? `input[name="${CSS.escape(name)}"]`
                                : `input[type="${type}"]`;
                            const allInputs = root.querySelectorAll(selector);
                            for (const inp of allInputs) {
                                const val = inp.getAttribute('value') || '';
                                const isDisabled = inp.disabled;
                                if (!isDisabled) allDisabled = false;
                                let txt = '';
                                const lbl = inp.closest('label');
                                if (lbl) txt = lbl.textContent.trim();
                                if (!txt) txt = val;
                                if (txt) {
                                    options.push({
                                        text: txt, value: val,
                                        disabled: isDisabled
                                    });
                                }
                            }
                        }

                        pairs.push({
                            title,
                            name: name || '',
                            qtype,
                            tag,
                            type,
                            placeholder,
                            options,
                            jFieldClass,
                            isDesktopSelect,
                            allDisabled,
                        });
                    }
                    return pairs;
                }
            """)

            if not fields_data:
                return []

            questions = []
            index = 0
            for fd in fields_data:
                try:
                    title = self._clean_text(fd["title"])
                    name = fd.get("name", "")
                    j_field_class = fd.get("jFieldClass", "")
                    qtype_str = fd.get("qtype", "text")
                    is_desktop_select = fd.get("isDesktopSelect", False)

                    # 类型映射
                    qtype_map = {
                        "text": QuestionType.TEXT,
                        "textarea": QuestionType.TEXTAREA,
                        "radio": QuestionType.RADIO,
                        "checkbox": QuestionType.CHECKBOX,
                        "select": QuestionType.SELECT,
                    }
                    qtype = qtype_map.get(qtype_str, QuestionType.TEXT)

                    # 通过唯一 j-field 类名获取容器
                    container = await page.query_selector(
                        f'[class*="{j_field_class}"]'
                    )
                    if not container:
                        continue

                    index += 1
                    q = Question(
                        id=name or j_field_class,
                        index=index,
                        type=qtype,
                        title=title,
                        is_required=False,
                        platform='jinshuju',
                        raw_element=container,
                        api_code=name if name else "",
                    )

                    # DesktopSelect 标记
                    if is_desktop_select:
                        q.input_type = "desktop_select"

                    # 只添加未禁用的选项
                    for opt_data in fd.get("options", []):
                        if opt_data.get("disabled"):
                            continue
                        q.options.append(QuestionOption(
                            text=opt_data["text"],
                            value=opt_data.get("value", ""),
                            is_other=("其他" in opt_data["text"] or "其它" in opt_data["text"])
                        ))

                    questions.append(q)
                except Exception as e:
                    logger.debug(f"构建Question失败: {e}")
                    continue

            return questions

        except Exception as e:
            logger.error(f"_parse_jsjform_fields失败: {e}")
            return []

    # ================================================================
    # 问卷星解析
    # ================================================================

    WJX_FIELD_SELECTORS = [
        "fieldset.field", "div.field", "div.ui-field",
    ]

    async def _parse_wjx(self, page) -> List[Question]:
        questions = []
        elements = []

        for selector in self.WJX_FIELD_SELECTORS:
            elements = await page.query_selector_all(selector)
            if len(elements) > 0:
                break

        if not elements:
            elements = await page.query_selector_all(
                "fieldset, div.field, div.ui-field"
            )

        index = 0
        for el in elements:
            try:
                qtype = await self._detect_wjx_type(el)
                if qtype == QuestionType.UNKNOWN:
                    continue

                index += 1
                title = await self._extract_wjx_title(el)
                is_required = (
                    await el.query_selector(".req, .required")
                ) is not None

                q = Question(
                    id=(await el.get_attribute("id")) or f"wjx_{index}",
                    index=index, type=qtype,
                    title=self._clean_text(title),
                    is_required=is_required,
                    platform='wjx', raw_element=el  # ← 容器
                )

                if q.is_choice_question():
                    q.options = await self._extract_wjx_options(el)
                elif q.type in (QuestionType.TEXT, QuestionType.TEXTAREA):
                    attrs = await self._extract_wjx_input_attrs(el)
                    q.input_type = attrs["input_type"]
                    q.placeholder = attrs["placeholder"]

                questions.append(q)
            except Exception:
                continue

        return questions

    async def _detect_wjx_type(self, el) -> QuestionType:
        class_str = (await el.get_attribute("class")) or ""
        if "ui-radio" in class_str: return QuestionType.RADIO
        if "ui-checkbox" in class_str: return QuestionType.CHECKBOX
        if "ui-textarea" in class_str: return QuestionType.TEXTAREA
        if "ui-text" in class_str: return QuestionType.TEXT
        if "ui-select" in class_str: return QuestionType.SELECT
        if "ui-matrix" in class_str:
            return (
                QuestionType.MATRIX_CHECKBOX if "checkbox" in class_str
                else QuestionType.MATRIX_RADIO
            )
        inner = await el.inner_html()
        if "<select" in inner: return QuestionType.SELECT
        if 'type="radio"' in inner: return QuestionType.RADIO
        if 'type="checkbox"' in inner: return QuestionType.CHECKBOX
        return QuestionType.UNKNOWN

    async def _extract_wjx_title(self, el) -> str:
        label = await el.query_selector(".field-label")
        if label: return await label.inner_text()
        text = await el.inner_text()
        return text.split("\n")[0] if text else ""

    async def _extract_wjx_options(self, el) -> List[QuestionOption]:
        options = []
        for opt in await el.query_selector_all("label"):
            text = (await opt.inner_text()).strip()
            if not text: continue
            input_el = await opt.query_selector("input")
            value = (
                (await input_el.get_attribute("value")) or ""
            ) if input_el else ""
            options.append(QuestionOption(
                text=text, value=value,
                is_other=("其他" in text or "其它" in text)
            ))
        return options

    async def _extract_wjx_input_attrs(self, el) -> dict:
        target = (
            await el.query_selector("input")
        ) or (
            await el.query_selector("textarea")
        )
        if target:
            return {
                "input_type": (await target.get_attribute("type")) or "",
                "placeholder": (await target.get_attribute("placeholder")) or ""
            }
        return {"input_type": "", "placeholder": ""}

    # ================================================================
    # 通用解析（兜底）
    # ================================================================

    async def _parse_generic(self, page) -> List[Question]:
        """通用表单解析 — 查找所有 label，以 label 的父容器作为 raw_element"""
        questions = []
        seen_titles = set()
        index = 0

        labels = await page.query_selector_all("label")
        for label in labels:
            try:
                text = (await label.inner_text()).strip()
                if not text or len(text) < 2:
                    continue
                if text in seen_titles:
                    continue

                # 查找关联的input
                for_attr = await label.get_attribute("for")
                if for_attr:
                    input_el = await page.query_selector(f"#{for_attr}")
                else:
                    input_el = await label.query_selector("input, textarea, select")

                if not input_el:
                    continue

                # 使用 label 的父容器作为 raw_element
                container = await label.evaluate_handle(
                    "el => el.closest('.form-group, .control-group, .field, .form-item, .question-item') || el.parentElement"
                )
                if container:
                    container = container.as_element()
                else:
                    container = label

                tag = await input_el.evaluate("el => el.tagName.toLowerCase()")
                itype = (await input_el.get_attribute("type")) or ""

                if tag == "select":
                    qtype = QuestionType.SELECT
                elif itype == "radio":
                    qtype = QuestionType.RADIO
                elif itype == "checkbox":
                    qtype = QuestionType.CHECKBOX
                elif tag == "textarea":
                    qtype = QuestionType.TEXTAREA
                else:
                    qtype = QuestionType.TEXT

                index += 1
                seen_titles.add(text)

                q = Question(
                    id=f"gen_{index}", index=index, type=qtype,
                    title=self._clean_text(text),
                    platform='generic',
                    raw_element=container  # ← 容器
                )

                if qtype == QuestionType.SELECT:
                    opts = await input_el.query_selector_all("option")
                    q.options = [
                        QuestionOption(
                            text=(await o.inner_text()).strip(),
                            value=(await o.get_attribute("value")) or ""
                        )
                        for o in opts
                    ]

                questions.append(q)

            except Exception:
                continue

        return questions


def describe_questions(questions: List[Question]) -> str:
    """生成题目描述文本（用于日志/调试）"""
    type_names = {
        QuestionType.RADIO: "单选", QuestionType.CHECKBOX: "多选",
        QuestionType.TEXT: "填空", QuestionType.TEXTAREA: "多行填空",
        QuestionType.SELECT: "下拉", QuestionType.MATRIX_RADIO: "矩阵单选",
        QuestionType.MATRIX_CHECKBOX: "矩阵多选", QuestionType.STAR: "评分",
        QuestionType.SORT: "排序",
    }
    lines = []
    for q in questions:
        tn = type_names.get(q.type, "未知")
        req = " *必答" if q.is_required else ""
        plat = f" [{q.platform}]" if q.platform else ""
        lines.append(f"  [{q.index}] {tn}: {q.title[:50]}{req}{plat}")
        if q.options:
            for opt in q.options[:5]:
                lines.append(f"      ○ {opt.text[:30]}")
            if len(q.options) > 5:
                lines.append(f"      ... 共{len(q.options)}个选项")
    return "\n".join(lines)
