"""
设置Tab - 应用配置（监听参数、填写选项等）

被 ui/main_window.py 引用，操作 ConfigManager
"""
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QFormLayout, QGroupBox, QSpinBox,
    QCheckBox
)
from PyQt6.QtCore import Qt


class SettingsTab(QWidget):
    """设置页面"""

    def __init__(self, config_manager, parent=None):
        super().__init__(parent)
        self._cm = config_manager
        self._init_ui()
        self._load_settings()

    def _init_ui(self):
        layout = QVBoxLayout(self)

        # 监听设置
        monitor_group = QGroupBox("QQ监听设置")
        monitor_layout = QFormLayout(monitor_group)

        self._poll_interval = QSpinBox()
        self._poll_interval.setRange(500, 10000)
        self._poll_interval.setSuffix(" ms")
        self._poll_interval.setSingleStep(500)
        self._poll_interval.valueChanged.connect(
            lambda v: self._cm.set("poll_interval_ms", v)
        )
        monitor_layout.addRow("轮询间隔:", self._poll_interval)

        self._max_messages = QSpinBox()
        self._max_messages.setRange(5, 100)
        self._max_messages.valueChanged.connect(
            lambda v: self._cm.set("max_message_count", v)
        )
        monitor_layout.addRow("每次读取消息数:", self._max_messages)

        layout.addWidget(monitor_group)

        # 填写设置
        fill_group = QGroupBox("问卷填写设置")
        fill_layout = QFormLayout(fill_group)

        self._auto_submit = QCheckBox("检测到链接后自动提交（关闭则手动确认）")
        self._auto_submit.toggled.connect(
            lambda v: self._cm.set("auto_submit", v)
        )
        fill_layout.addRow(self._auto_submit)

        self._fill_delay = QSpinBox()
        self._fill_delay.setRange(100, 5000)
        self._fill_delay.setSuffix(" ms")
        self._fill_delay.setSingleStep(100)
        self._fill_delay.valueChanged.connect(
            lambda v: self._cm.set("fill_delay_ms", v)
        )
        fill_layout.addRow("填写间隔:", self._fill_delay)

        self._headless = QCheckBox("使用无头浏览器（后台运行，不显示浏览器窗口）")
        self._headless.toggled.connect(
            lambda v: self._cm.set("headless_browser", v)
        )
        fill_layout.addRow(self._headless)

        layout.addWidget(fill_group)

        layout.addStretch()

    def _load_settings(self):
        s = self._cm.settings
        self._poll_interval.setValue(s.poll_interval_ms)
        self._max_messages.setValue(s.max_message_count)
        self._auto_submit.setChecked(s.auto_submit)
        self._fill_delay.setValue(s.fill_delay_ms)
        self._headless.setChecked(s.headless_browser)

    def refresh_settings(self):
        self._load_settings()
