"""
预设信息管理器 - 负责多套预设信息的增删改查和持久化

- 被 ui/tabs/profile_tab.py 和 main.py 调用
- 数据存储在 %APPDATA%/QQSurveyAssistant/profiles.json
"""
import json
import os
import copy
from typing import List, Optional
from .models import Profile, ProfileField


def _get_profiles_dir() -> str:
    """获取预设信息存储目录"""
    appdata = os.environ.get("APPDATA", os.path.expanduser("~"))
    return os.path.join(appdata, "QQSurveyAssistant")


def _get_profiles_path() -> str:
    """获取预设信息文件路径"""
    return os.path.join(_get_profiles_dir(), "profiles.json")


def _get_default_profile_data() -> dict:
    """返回默认预设信息模板数据"""
    return {
        "name": "默认预设",
        "fields": {
            "姓名": {
                "key": "姓名",
                "value": "",
                "aliases": ["你的名字", "请填写姓名", "学生姓名", "您的姓名"]
            },
            "学号": {
                "key": "学号",
                "value": "",
                "aliases": ["你的学号", "请填写学号", "学生学号", "工号"]
            },
            "手机号": {
                "key": "手机号",
                "value": "",
                "aliases": ["你的手机号", "请填写手机号", "联系电话", "手机号码", "电话"]
            },
            "班级": {
                "key": "班级",
                "value": "",
                "aliases": ["你的班级", "请填写班级", "所在班级", "行政班"]
            },
            "QQ号": {
                "key": "QQ号",
                "value": "",
                "aliases": ["你的QQ", "请填写QQ号", "QQ号码"]
            },
            "邮箱": {
                "key": "邮箱",
                "value": "",
                "aliases": ["你的邮箱", "请填写邮箱", "电子邮箱", "Email", "E-mail"]
            }
        },
        "default_choices": {}
    }


class ProfileManager:
    """预设信息管理器"""

    def __init__(self):
        self._profiles: List[Profile] = []
        self._active_index: int = 0  # 当前使用的预设索引
        self._load()

    # ===== 属性 =====

    @property
    def profiles(self) -> List[Profile]:
        """获取所有预设列表"""
        return self._profiles

    @property
    def active_profile(self) -> Optional[Profile]:
        """获取当前激活的预设"""
        if 0 <= self._active_index < len(self._profiles):
            return self._profiles[self._active_index]
        return None

    @property
    def active_index(self) -> int:
        return self._active_index

    # ===== CRUD =====

    def add_profile(self, name: str) -> Profile:
        """添加一个新的空预设"""
        profile = Profile(name=name)
        self._profiles.append(profile)
        self._save()
        return profile

    def remove_profile(self, index: int) -> bool:
        """删除指定索引的预设"""
        if 0 <= index < len(self._profiles):
            del self._profiles[index]
            if self._active_index >= len(self._profiles):
                self._active_index = max(0, len(self._profiles) - 1)
            self._save()
            return True
        return False

    def duplicate_profile(self, index: int) -> Optional[Profile]:
        """复制指定索引的预设"""
        if 0 <= index < len(self._profiles):
            original = self._profiles[index]
            new_profile = copy.deepcopy(original)
            new_profile.name = f"{original.name} (副本)"
            self._profiles.append(new_profile)
            self._save()
            return new_profile
        return None

    def set_active_profile(self, index: int):
        """设置当前使用的预设"""
        if 0 <= index < len(self._profiles):
            self._active_index = index
            self._save()

    def update_profile_name(self, index: int, name: str):
        """更新预设名称"""
        if 0 <= index < len(self._profiles):
            self._profiles[index].name = name
            self._save()

    def add_field(self, profile_index: int, key: str, value: str = "", aliases: List[str] = None):
        """向指定预设添加字段"""
        if 0 <= profile_index < len(self._profiles):
            profile = self._profiles[profile_index]
            field = ProfileField(key=key, value=value, aliases=aliases or [])
            profile.fields[key] = field
            self._save()

    def remove_field(self, profile_index: int, key: str):
        """从指定预设删除字段"""
        if 0 <= profile_index < len(self._profiles):
            profile = self._profiles[profile_index]
            if key in profile.fields:
                del profile.fields[key]
                self._save()

    def update_field(self, profile_index: int, key: str,
                     value: str = None, aliases: List[str] = None):
        """更新字段值或别名"""
        if 0 <= profile_index < len(self._profiles):
            profile = self._profiles[profile_index]
            if key in profile.fields:
                field = profile.fields[key]
                if value is not None:
                    field.value = value
                if aliases is not None:
                    field.aliases = aliases
                self._save()

    def add_default_choice(self, profile_index: int, question_key: str, answer: str):
        """添加默认选择题答案"""
        if 0 <= profile_index < len(self._profiles):
            self._profiles[profile_index].default_choices[question_key] = answer
            self._save()

    def remove_default_choice(self, profile_index: int, question_key: str):
        """删除默认选择题答案"""
        if 0 <= profile_index < len(self._profiles):
            profile = self._profiles[profile_index]
            if question_key in profile.default_choices:
                del profile.default_choices[question_key]
                self._save()

    # ===== 导入导出 =====

    def export_to_file(self, filepath: str):
        """导出所有预设到文件"""
        data = {
            "active_index": self._active_index,
            "profiles": [p.to_dict() for p in self._profiles]
        }
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    def import_from_file(self, filepath: str):
        """从文件导入预设"""
        with open(filepath, "r", encoding="utf-8") as f:
            data = json.load(f)
        self._profiles = [Profile.from_dict(p) for p in data.get("profiles", [])]
        self._active_index = data.get("active_index", 0)
        if self._active_index >= len(self._profiles):
            self._active_index = max(0, len(self._profiles) - 1)
        self._save()

    # ===== 持久化 =====

    def _save(self):
        """保存到文件"""
        os.makedirs(_get_profiles_dir(), exist_ok=True)
        data = {
            "active_index": self._active_index,
            "profiles": [p.to_dict() for p in self._profiles]
        }
        with open(_get_profiles_path(), "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    def _load(self):
        """从文件加载"""
        path = _get_profiles_path()
        if os.path.exists(path):
            try:
                with open(path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                self._profiles = [Profile.from_dict(p) for p in data.get("profiles", [])]
                self._active_index = data.get("active_index", 0)
                if self._active_index >= len(self._profiles):
                    self._active_index = max(0, len(self._profiles) - 1)
            except (json.JSONDecodeError, KeyError):
                self._init_default()
        else:
            self._init_default()

    def _init_default(self):
        """初始化默认预设"""
        default_data = _get_default_profile_data()
        default_profile = Profile.from_dict(default_data)
        self._profiles = [default_profile]
        self._active_index = 0
        self._save()
