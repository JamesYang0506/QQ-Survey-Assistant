"""
预设信息数据模型

- 被 profiles/manager.py 和 ui/tabs/profile_tab.py 调用
- 定义 Profile 和 ProfileField 两个核心数据结构
"""
from dataclasses import dataclass, field
from typing import Dict, List, Optional


@dataclass
class ProfileField:
    """预设信息中的一个字段"""
    key: str          # 字段键名，如 "姓名"
    value: str        # 字段值，如 "张三"
    aliases: List[str] = field(default_factory=list)  # 别名列表，如 ["你的名字", "请填写姓名"]


@dataclass
class Profile:
    """一套完整的预设信息"""
    name: str                              # 预设名称，如 "张三-默认"
    fields: Dict[str, ProfileField] = field(default_factory=dict)  # key -> ProfileField
    default_choices: Dict[str, str] = field(default_factory=dict)  # 默认选择题答案，如 {"性别": "男"}

    def get_field_by_key(self, key: str) -> Optional[ProfileField]:
        """通过精确key获取字段"""
        return self.fields.get(key)

    def find_field(self, text: str) -> Optional[ProfileField]:
        """
        通过文本模糊匹配字段 - 先匹配key，再匹配别名。

        Args:
            text: 问卷中的题目文本

        Returns:
            匹配到的ProfileField，如果未找到则返回None
        """
        if not text:
            return None

        # 1. 精确匹配key
        for field in self.fields.values():
            if field.key in text:
                return field

        # 2. 匹配别名
        for field in self.fields.values():
            for alias in field.aliases:
                if alias in text:
                    return field

        return None

    def to_dict(self) -> dict:
        """序列化为字典"""
        return {
            "name": self.name,
            "fields": {
                key: {
                    "key": f.key,
                    "value": f.value,
                    "aliases": f.aliases
                }
                for key, f in self.fields.items()
            },
            "default_choices": dict(self.default_choices)
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Profile":
        """从字典反序列化"""
        fields = {}
        for key, fdata in data.get("fields", {}).items():
            fields[key] = ProfileField(
                key=fdata["key"],
                value=fdata["value"],
                aliases=fdata.get("aliases", [])
            )
        return cls(
            name=data["name"],
            fields=fields,
            default_choices=data.get("default_choices", {})
        )
