"""
题目-预设字段模糊匹配器

被 survey_filler/filler.py 调用
将问卷题目文本匹配到预设信息的字段和默认选择
"""
from typing import Optional, Tuple
from thefuzz import fuzz, process

from profiles.models import Profile
from .parser import Question, QuestionType


class QuestionMatcher:
    """题目匹配器 - 将问卷题目映射到预设字段"""

    MIN_MATCH_SCORE = 60  # 模糊匹配最低阈值

    @staticmethod
    def find_best_field(question: Question, profile: Profile) -> Optional[Tuple[str, str]]:
        """
        为题目找到最匹配的预设字段。

        匹配策略：
        1. 先子串匹配（key和别名）
        2. 再用 thefuzz 进行模糊匹配

        Returns: (字段key, 字段value) 或 None
        """
        # 策略1: 子串精确匹配
        field = profile.find_field(question.title)
        if field and field.value:
            return (field.key, field.value)

        # 策略2: 模糊匹配
        if not profile.fields:
            return None

        best_score = 0
        best_field = None

        for f in profile.fields.values():
            if not f.value:
                continue
            # 匹配key
            score = fuzz.partial_ratio(question.title, f.key)
            if score > best_score:
                best_score = score
                best_field = f
            # 匹配别名
            for alias in f.aliases:
                score = fuzz.partial_ratio(question.title, alias)
                if score > best_score:
                    best_score = score
                    best_field = f

        if best_field and best_score >= QuestionMatcher.MIN_MATCH_SCORE and best_field.value:
            return (best_field.key, best_field.value)

        return None

    @staticmethod
    def find_best_choice(question: Question, profile: Profile) -> Optional[str]:
        """
        为选择题找到默认选项。

        在 profile.default_choices 中查找匹配的关键词，
        然后在选项中模糊匹配对应值。

        Returns: 选项文本 或 None
        """
        if not question.options or not profile.default_choices:
            return None

        for key, answer in profile.default_choices.items():
            if key in question.title:
                # 精确匹配选项
                for opt in question.options:
                    if answer in opt.text or opt.text in answer:
                        return opt.text
                # 模糊匹配选项
                texts = [opt.text for opt in question.options]
                best, score = process.extractOne(answer, texts) if texts else (None, 0)
                if best and score >= 60:
                    return best

        return None

    @staticmethod
    def find_best_option_by_keyword(question: Question, keyword: str) -> Optional[str]:
        """根据关键词在选项中找到最佳匹配"""
        if not question.options or not keyword:
            return None
        texts = [opt.text for opt in question.options]
        best, score = process.extractOne(keyword, texts) if texts else (None, 0)
        if best and score >= QuestionMatcher.MIN_MATCH_SCORE:
            return best
        return None
