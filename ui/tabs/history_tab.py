"""
历史记录Tab - 查看已填写的问卷记录（SQLite存储）

被 ui/main_window.py 引用
"""
import os

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel,
    QTableWidget, QTableWidgetItem, QHeaderView, QGroupBox,
    QMessageBox, QSplitter, QTextEdit
)
from PyQt6.QtCore import Qt

from storage.history_db import HistoryDB


class HistoryTab(QWidget):
    """历史记录页面"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._db = HistoryDB()
        self._init_ui()
        self.refresh()

    def _init_ui(self):
        layout = QVBoxLayout(self)

        # 统计信息
        self._stats_label = QLabel("共 0 条记录 | 成功: 0 | 失败: 0")
        self._stats_label.setStyleSheet("color: #666; padding: 4px;")
        layout.addWidget(self._stats_label)

        # 表格
        history_group = QGroupBox("填写记录")
        history_layout = QVBoxLayout(history_group)

        self._table = QTableWidget()
        self._table.setColumnCount(6)
        self._table.setHorizontalHeaderLabels([
            "时间", "问卷链接", "预设方案", "结果", "填写进度", "备注"
        ])
        self._table.horizontalHeader().setSectionResizeMode(
            0, QHeaderView.ResizeMode.ResizeToContents
        )
        self._table.horizontalHeader().setSectionResizeMode(
            1, QHeaderView.ResizeMode.Stretch
        )
        self._table.horizontalHeader().setSectionResizeMode(
            2, QHeaderView.ResizeMode.ResizeToContents
        )
        self._table.horizontalHeader().setSectionResizeMode(
            3, QHeaderView.ResizeMode.ResizeToContents
        )
        self._table.horizontalHeader().setSectionResizeMode(
            4, QHeaderView.ResizeMode.ResizeToContents
        )
        self._table.horizontalHeader().setSectionResizeMode(
            5, QHeaderView.ResizeMode.Stretch
        )
        self._table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self._table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self._table.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        self._table.itemSelectionChanged.connect(self._on_selection_changed)
        history_layout.addWidget(self._table)

        layout.addWidget(history_group)

        # 工具栏
        toolbar = QHBoxLayout()
        self._view_btn = QPushButton("查看详情")
        self._view_btn.setEnabled(False)
        self._view_btn.clicked.connect(self._view_detail)
        self._delete_btn = QPushButton("删除选中")
        self._delete_btn.setEnabled(False)
        self._delete_btn.clicked.connect(self._delete_selected)
        toolbar.addWidget(self._view_btn)
        toolbar.addWidget(self._delete_btn)
        toolbar.addStretch()
        self._refresh_btn = QPushButton("刷新")
        self._refresh_btn.clicked.connect(self.refresh)
        toolbar.addWidget(self._refresh_btn)
        self._clear_btn = QPushButton("清空全部")
        self._clear_btn.clicked.connect(self._clear_all)
        toolbar.addWidget(self._clear_btn)
        layout.addLayout(toolbar)

        # 详情面板（下方）
        self._detail_text = QTextEdit()
        self._detail_text.setReadOnly(True)
        self._detail_text.setMaximumHeight(150)
        self._detail_text.setPlaceholderText("选中一条记录查看详情...")
        layout.addWidget(self._detail_text)

    # ===== 数据加载 =====

    def refresh(self):
        """从数据库刷新记录"""
        records = self._db.get_records()
        self._table.setRowCount(0)

        for record in records:
            row = self._table.rowCount()
            self._table.insertRow(row)

            # 时间
            ts = record.get("created_at", record.get("timestamp", ""))
            self._table.setItem(row, 0, QTableWidgetItem(str(ts)[:19]))

            # 链接
            url = record.get("url", "")
            self._table.setItem(row, 1, QTableWidgetItem(url[:80]))

            # 方案
            profile = record.get("profile_name", "")
            self._table.setItem(row, 2, QTableWidgetItem(profile))

            # 结果
            success = record.get("success", 0)
            result_text = "✓ 成功" if success else "✗ 失败"
            result_item = QTableWidgetItem(result_text)
            result_item.setForeground(
                Qt.GlobalColor.darkGreen if success else Qt.GlobalColor.red
            )
            self._table.setItem(row, 3, result_item)

            # 进度
            filled = record.get("fields_filled", 0)
            total = record.get("fields_total", 0)
            self._table.setItem(row, 4, QTableWidgetItem(f"{filled}/{total}"))

            # 备注
            note = record.get("error_message", "") or record.get("note", "")
            self._table.setItem(row, 5, QTableWidgetItem(note[:100]))

            # 存储数据库ID（隐藏）
            self._table.item(row, 0).setData(
                Qt.ItemDataRole.UserRole, record.get("id")
            )

        self._update_stats()

    def _update_stats(self):
        stats = self._db.get_stats()
        self._stats_label.setText(
            f"共 {stats['total']} 条记录 | "
            f"成功: {stats['success']} | 失败: {stats['failed']} | "
            f"已填字段: {stats['total_fields_filled']}"
        )

    def add_record(self, timestamp: str, url: str, profile_name: str,
                   status: str, note: str = ""):
        """添加记录后刷新（外部调用入口）"""
        self.refresh()

    # ===== 操作 =====

    def _on_selection_changed(self):
        has_selection = self._table.currentRow() >= 0
        self._view_btn.setEnabled(has_selection)
        self._delete_btn.setEnabled(has_selection)

    def _get_selected_id(self) -> int:
        row = self._table.currentRow()
        if row < 0:
            return -1
        item = self._table.item(row, 0)
        if item is None:
            return -1
        return item.data(Qt.ItemDataRole.UserRole) or -1

    def _view_detail(self):
        rid = self._get_selected_id()
        if rid < 0:
            return
        record = self._db.get_record(rid)
        if not record:
            return

        detail = (
            f"时间: {record.get('created_at', '')}\n"
            f"问卷: {record.get('url', '')}\n"
            f"方案: {record.get('profile_name', '')}\n"
            f"结果: {'成功' if record.get('success') else '失败'}\n"
            f"进度: {record.get('fields_filled', 0)}/{record.get('fields_total', 0)}\n"
            f"截图: {record.get('screenshot_path', '无')}\n"
            f"错误: {record.get('error_message', '无')}"
        )
        self._detail_text.setPlainText(detail)

    def _delete_selected(self):
        rid = self._get_selected_id()
        if rid < 0:
            return
        reply = QMessageBox.question(
            self, "确认删除", "确定删除选中的记录吗？",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if reply == QMessageBox.StandardButton.Yes:
            self._db.delete_record(rid)
            self.refresh()

    def _clear_all(self):
        reply = QMessageBox.question(
            self, "确认清空", "确定清空所有历史记录吗？此操作不可恢复。",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if reply == QMessageBox.StandardButton.Yes:
            self._db.clear_all()
            self.refresh()
            self._detail_text.clear()
