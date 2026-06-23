"""
应用配置管理器 - 管理应用级别的设置（非预设信息）

- 被 main.py 和 ui/ 各模块调用
- 数据存储在 %APPDATA%/QQSurveyAssistant/settings.json
"""
import json
import os
from dataclasses import dataclass, field, asdict
from typing import Optional


@dataclass
class AppSettings:
    """应用设置"""
    # 监控设置
    poll_interval_ms: int = 2000          # QQ消息轮询间隔（毫秒）
    max_message_count: int = 20           # 每次读取的最大消息数

    # 填写设置
    auto_submit: bool = False             # 是否自动提交（False=手动确认）
    fill_delay_ms: int = 500              # 每个字段填写间隔（毫秒）
    headless_browser: bool = False        # 是否无头浏览器（False=可见）

    # 通用设置
    language: str = "zh_CN"               # 界面语言

    # 窗口状态
    window_width: int = 1024
    window_height: int = 720
    window_x: Optional[int] = None
    window_y: Optional[int] = None


class ConfigManager:
    """应用配置管理器"""

    SETTINGS_FILE = "settings.json"

    def __init__(self):
        self._settings: AppSettings = AppSettings()
        self._data_dir = self._get_data_dir()
        self._load()

    @staticmethod
    def _get_data_dir() -> str:
        appdata = os.environ.get("APPDATA", os.path.expanduser("~"))
        return os.path.join(appdata, "QQSurveyAssistant")

    @property
    def settings(self) -> AppSettings:
        return self._settings

    @property
    def data_dir(self) -> str:
        return self._data_dir

    @property
    def settings_path(self) -> str:
        return os.path.join(self._data_dir, self.SETTINGS_FILE)

    def update(self, **kwargs):
        """批量更新设置"""
        for key, value in kwargs.items():
            if hasattr(self._settings, key):
                setattr(self._settings, key, value)
        self._save()

    def get(self, key: str, default=None):
        """获取单个设置值"""
        return getattr(self._settings, key, default)

    def set(self, key: str, value):
        """设置单个设置值"""
        if hasattr(self._settings, key):
            setattr(self._settings, key, value)
            self._save()

    def _save(self):
        os.makedirs(self._data_dir, exist_ok=True)
        data = asdict(self._settings)
        with open(self.settings_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    def _load(self):
        if os.path.exists(self.settings_path):
            try:
                with open(self.settings_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                for key, value in data.items():
                    if hasattr(self._settings, key):
                        setattr(self._settings, key, value)
            except (json.JSONDecodeError, KeyError):
                self._save()
        else:
            self._save()
