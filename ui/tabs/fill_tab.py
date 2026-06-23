"""
填写面板 - 粘贴链接或从剪贴板读取，点击填写
"""
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel,
    QGroupBox, QLineEdit, QTextEdit, QApplication
)
from PyQt6.QtCore import Qt, pyqtSignal


class FillTab(QWidget):
    """问卷填写面板"""

    fill_requested = pyqtSignal(str)  # url

    def __init__(self, config_manager, parent=None):
        super().__init__(parent)
        self._cm = config_manager
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)

        # ===== 链接输入 =====
        input_group = QGroupBox("问卷链接")
        input_layout = QHBoxLayout(input_group)

        self._url_input = QLineEdit()
        self._url_input.setPlaceholderText(
            "在此粘贴问卷链接，或点击右侧按钮从剪贴板读取..."
        )
        self._url_input.returnPressed.connect(self._on_fill_clicked)
        input_layout.addWidget(self._url_input)

        self._clipboard_btn = QPushButton("📋 读取剪贴板")
        self._clipboard_btn.setToolTip("从剪贴板读取最近复制的链接")
        self._clipboard_btn.clicked.connect(self._read_clipboard)
        input_layout.addWidget(self._clipboard_btn)

        self._fill_btn = QPushButton("▶ 填写")
        self._fill_btn.setMinimumWidth(100)
        self._fill_btn.setStyleSheet(
            "QPushButton { background-color: #1890ff; color: white; "
            "font-size: 14px; padding: 8px 16px; border-radius: 4px; }"
            "QPushButton:hover { background-color: #40a9ff; }"
        )
        self._fill_btn.clicked.connect(self._on_fill_clicked)
        input_layout.addWidget(self._fill_btn)

        layout.addWidget(input_group)

        # ===== 填写日志 =====
        log_group = QGroupBox("填写日志")
        log_layout = QVBoxLayout(log_group)
        self._msg_log = QTextEdit()
        self._msg_log.setReadOnly(True)
        self._msg_log.document().setMaximumBlockCount(500)
        self._msg_log.setPlaceholderText("填写进度将在此显示...")
        log_layout.addWidget(self._msg_log)
        layout.addWidget(log_group)

        layout.addStretch()

    def _on_fill_clicked(self):
        url = self._url_input.text().strip()
        if not url:
            self._read_clipboard()
            url = self._url_input.text().strip()
        if not url:
            return
        if not (url.startswith("http://") or url.startswith("https://")):
            url = "https://" + url
            self._url_input.setText(url)
        self.fill_requested.emit(url)

    def _read_clipboard(self):
        """从剪贴板读取链接"""
        text = QApplication.clipboard().text()
        if text:
            text = text.strip()
            # 提取第一个 URL
            import re
            urls = re.findall(
                r'https?://[^\s]+', text
            )
            if urls:
                url = urls[0].rstrip('.,;:!?）)')
                self._url_input.setText(url)
                self._append_log(f"从剪贴板读取: {url}")
            else:
                # 可能是纯文本链接或短链接
                lines = [l.strip() for l in text.split('\n') if l.strip()]
                for line in lines:
                    if any(d in line for d in ['wjx.cn', 'wjx.top', 'jinshuju.com', 'jinshuju.net', 'jsjform.com', 'wj.qq.com']):
                        url = line if line.startswith('http') else 'https://' + line
                        self._url_input.setText(url)
                        self._append_log(f"从剪贴板读取: {url}")
                        return
                # 最后手段：取第一行非空
                if lines:
                    first = lines[0]
                    if len(first) > 10 and not first.startswith('http'):
                        first = 'https://' + first
                    self._url_input.setText(first)
                    self._append_log(f"从剪贴板读取: {first}")

    def add_detected_link(self, url: str):
        self._url_input.setText(url)
        self._append_log(f"检测到链接: {url}")

    def get_log_text(self) -> str:
        return self._msg_log.toPlainText()

    def _append_log(self, msg: str):
        from datetime import datetime
        timestamp = datetime.now().strftime("%H:%M:%S")
        self._msg_log.append(f"[{timestamp}] {msg}")
