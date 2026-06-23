"""
日志Tab - 显示应用运行日志，集成Python logging

被 ui/main_window.py 引用
"""
import logging

from PyQt6.QtWidgets import QWidget, QVBoxLayout, QTextEdit, QHBoxLayout, QPushButton
from PyQt6.QtCore import Qt, pyqtSignal


class QTextEditHandler(logging.Handler):
    """将Python logging消息转发到QTextEdit"""
    def __init__(self, widget: QTextEdit):
        super().__init__()
        self._widget = widget
        self.setFormatter(logging.Formatter(
            "%(asctime)s [%(levelname)s] %(message)s",
            datefmt="%H:%M:%S"
        ))

    def emit(self, record):
        try:
            msg = self.format(record)
            # 颜色标记
            if record.levelno >= logging.ERROR:
                msg = f'<span style="color:red">{msg}</span>'
            elif record.levelno >= logging.WARNING:
                msg = f'<span style="color:orange">{msg}</span>'
            self._widget.append(msg)
        except Exception:
            pass


class LogTab(QWidget):
    """日志查看页面"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._handler: QTextEditHandler = None
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)

        toolbar = QHBoxLayout()
        toolbar.addStretch()
        self._clear_btn = QPushButton("清空日志")
        self._clear_btn.clicked.connect(lambda: self._log_view.clear())
        toolbar.addWidget(self._clear_btn)
        layout.addLayout(toolbar)

        self._log_view = QTextEdit()
        self._log_view.setReadOnly(True)
        self._log_view.document().setMaximumBlockCount(2000)
        self._log_view.setPlaceholderText("应用日志将在此显示...")
        # 允许HTML渲染颜色
        layout.addWidget(self._log_view)

    def setup_handler(self) -> QTextEditHandler:
        """创建并注册logging handler"""
        if self._handler is None:
            self._handler = QTextEditHandler(self._log_view)
            self._handler.setLevel(logging.INFO)
            logging.getLogger("QQSurveyAssistant").addHandler(self._handler)
            # 也捕获root logger
            logging.getLogger().addHandler(self._handler)
        return self._handler

    def remove_handler(self):
        """移除handler（关闭时调用）"""
        if self._handler:
            logging.getLogger("QQSurveyAssistant").removeHandler(self._handler)
            logging.getLogger().removeHandler(self._handler)
            self._handler = None

    def append_log(self, message: str, level: str = "INFO"):
        """手动追加日志条目"""
        from datetime import datetime
        ts = datetime.now().strftime("%H:%M:%S")
        color = "red" if level == "ERROR" else ("orange" if level == "WARN" else "white")
        self._log_view.append(
            f'<span style="color:{color}">[{ts}] [{level}] {message}</span>'
        )
