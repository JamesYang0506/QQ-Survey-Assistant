"""
主窗口 - 应用主界面，整合所有Tab和模块

被 main.py 实例化
"""
import asyncio
import logging

from PyQt6.QtWidgets import (
    QMainWindow, QTabWidget, QStatusBar, QMessageBox
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal

from .tabs.fill_tab import FillTab
from .tabs.profile_tab import ProfileTab
from .tabs.settings_tab import SettingsTab
from .tabs.log_tab import LogTab
from .tabs.history_tab import HistoryTab

from survey_filler.filler import SurveyFiller
from survey_filler.submitter import FillResult

logger = logging.getLogger("QQSurveyAssistant.MainWindow")


class FillWorker(QThread):
    """问卷填写工作线程"""
    log_message = pyqtSignal(str)
    finished = pyqtSignal(object)  # FillResult

    def __init__(self, url: str, profile_manager, config_manager, parent=None):
        super().__init__(parent)
        self._url = url
        self._pm = profile_manager
        self._cm = config_manager

    def run(self):
        s = self._cm.settings
        try:
            filler = SurveyFiller(
                self._pm,
                headless=s.headless_browser,
                fill_delay_ms=s.fill_delay_ms
            )
            filler.set_callbacks(
                on_log=lambda msg: self.log_message.emit(msg),
                on_question_filled=lambda i, t, info:
                    self.log_message.emit(f"  [{i}/{t}] {info}"),
            )

            result = asyncio.run(filler.fill_survey(
                self._url, auto_submit=s.auto_submit
            ))
            self.finished.emit(result)

        except Exception as e:
            logger.error(f"填写线程出错: {e}", exc_info=True)
            result = FillResult(
                success=False, url=self._url,
                error_message=str(e)
            )
            self.finished.emit(result)


class MainWindow(QMainWindow):
    """QQ问卷星报名助手主窗口"""

    def __init__(self, profile_manager, config_manager):
        super().__init__()
        self._pm = profile_manager
        self._cm = config_manager
        self._fill_worker: FillWorker = None

        self._init_ui()
        self._restore_window_state()

    def _init_ui(self):
        self.setWindowTitle("QQ问卷星报名助手")
        self.resize(1024, 720)

        self._tab_widget = QTabWidget()
        self.setCentralWidget(self._tab_widget)

        # 创建各Tab
        self._fill_tab = FillTab(self._cm)
        self._profile_tab = ProfileTab(self._pm)
        self._settings_tab = SettingsTab(self._cm)
        self._log_tab = LogTab()
        self._history_tab = HistoryTab()

        self._tab_widget.addTab(self._fill_tab, "📝 填写问卷")
        self._tab_widget.addTab(self._profile_tab, "👤 预设管理")
        self._tab_widget.addTab(self._settings_tab, "⚙ 设置")
        self._tab_widget.addTab(self._log_tab, "📋 日志")
        self._tab_widget.addTab(self._history_tab, "📊 历史记录")

        self._log_tab.setup_handler()

        self._status_bar = QStatusBar()
        self.setStatusBar(self._status_bar)
        self._update_status_bar()

        # 信号连接
        self._profile_tab.profile_changed.connect(self._on_profile_changed)
        self._fill_tab.fill_requested.connect(self._on_fill_requested)

    def _update_status_bar(self):
        active = self._pm.active_profile
        name = active.name if active else "无"
        self._status_bar.showMessage(f"就绪 | 当前预设: {name}")

    def _on_profile_changed(self):
        self._update_status_bar()

    def _restore_window_state(self):
        s = self._cm.settings
        if s.window_width:
            self.resize(s.window_width, s.window_height)
        if s.window_x is not None and s.window_y is not None:
            self.move(s.window_x, s.window_y)

    def closeEvent(self, event):
        self._log_tab.remove_handler()
        self._cm.update(
            window_width=self.width(),
            window_height=self.height(),
            window_x=self.x(),
            window_y=self.y()
        )
        event.accept()

    # ===== 问卷填写 =====

    def _on_fill_requested(self, url: str):
        if self._fill_worker and self._fill_worker.isRunning():
            QMessageBox.warning(self, "提示", "当前有正在进行的填写任务，请等待完成")
            return

        self._status_bar.showMessage(f"正在填写: {url[:60]}...")
        self._tab_widget.setCurrentWidget(self._log_tab)

        self._log(f"======== 开始填写 ========")
        self._log(f"链接: {url}")
        self._log(f"预设: {self._pm.active_profile.name if self._pm.active_profile else '无'}")

        self._fill_worker = FillWorker(url, self._pm, self._cm)
        self._fill_worker.log_message.connect(self._log)
        self._fill_worker.finished.connect(self._on_fill_finished)
        self._fill_worker.start()

    def _on_fill_finished(self, result: FillResult):
        if result.success:
            self._status_bar.showMessage(
                f"填写完成 | {result.fields_filled}/{result.fields_total} 个字段已填充"
            )
            self._log(f"✓ 填写完成: {result.fields_filled}/{result.fields_total} 个字段")
            if result.screenshot_path:
                self._log(f"  截图: {result.screenshot_path}")
        else:
            self._status_bar.showMessage(f"填写失败: {result.error_message}")
            self._log(f"✗ 填写失败: {result.error_message}")

        self._log("======== 填写结束 ========")
        self._history_tab.refresh()
        self._fill_worker = None

    def _log(self, msg: str):
        self._log_tab.append_log(msg)
