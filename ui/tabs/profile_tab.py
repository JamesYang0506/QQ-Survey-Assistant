"""
预设信息管理Tab - 管理多套预设信息，编辑字段和别名

被 ui/main_window.py 引用，操作 ProfileManager 的CRUD接口
"""
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QTableWidget,
    QTableWidgetItem, QHeaderView, QGroupBox, QLabel, QLineEdit,
    QComboBox, QMessageBox, QInputDialog, QSplitter, QTextEdit,
    QFormLayout, QFileDialog
)
from PyQt6.QtCore import Qt, pyqtSignal


class ProfileTab(QWidget):
    """预设信息管理Tab"""

    # 当预设信息变更时通知其他模块
    profile_changed = pyqtSignal()

    def __init__(self, profile_manager, parent=None):
        super().__init__(parent)
        self._pm = profile_manager
        self._current_field_key = None
        self._init_ui()
        self._refresh_all()

    def _init_ui(self):
        main_layout = QHBoxLayout(self)

        # ===== 左侧：预设列表 =====
        left_panel = QVBoxLayout()

        # 预设选择
        preset_group = QGroupBox("预设方案")
        preset_layout = QVBoxLayout(preset_group)

        selector_layout = QHBoxLayout()
        selector_layout.addWidget(QLabel("当前方案:"))
        self._preset_combo = QComboBox()
        self._preset_combo.currentIndexChanged.connect(self._on_preset_changed)
        selector_layout.addWidget(self._preset_combo, 1)
        preset_layout.addLayout(selector_layout)

        btn_layout = QHBoxLayout()
        self._add_preset_btn = QPushButton("新建")
        self._add_preset_btn.clicked.connect(self._add_preset)
        self._dup_preset_btn = QPushButton("复制")
        self._dup_preset_btn.clicked.connect(self._duplicate_preset)
        self._del_preset_btn = QPushButton("删除")
        self._del_preset_btn.clicked.connect(self._delete_preset)
        btn_layout.addWidget(self._add_preset_btn)
        btn_layout.addWidget(self._dup_preset_btn)
        btn_layout.addWidget(self._del_preset_btn)
        preset_layout.addLayout(btn_layout)

        # 激活按钮
        self._activate_btn = QPushButton("✅ 设为当前使用")
        self._activate_btn.clicked.connect(self._activate_preset)
        preset_layout.addWidget(self._activate_btn)

        left_panel.addWidget(preset_group)

        # 导入导出
        io_group = QGroupBox("导入/导出")
        io_layout = QHBoxLayout(io_group)
        self._import_btn = QPushButton("导入...")
        self._import_btn.clicked.connect(self._import_profiles)
        self._export_btn = QPushButton("导出...")
        self._export_btn.clicked.connect(self._export_profiles)
        io_layout.addWidget(self._import_btn)
        io_layout.addWidget(self._export_btn)
        left_panel.addWidget(io_group)

        left_panel.addStretch()
        main_layout.addLayout(left_panel)

        # ===== 中间：字段表格 =====
        center_panel = QVBoxLayout()

        field_group = QGroupBox("预设字段")
        field_layout = QVBoxLayout(field_group)

        self._field_table = QTableWidget()
        self._field_table.setColumnCount(2)
        self._field_table.setHorizontalHeaderLabels(["字段名", "字段值"])
        self._field_table.horizontalHeader().setSectionResizeMode(
            0, QHeaderView.ResizeMode.Stretch
        )
        self._field_table.horizontalHeader().setSectionResizeMode(
            1, QHeaderView.ResizeMode.Stretch
        )
        self._field_table.itemSelectionChanged.connect(self._on_field_selected)
        self._field_table.cellChanged.connect(self._on_field_cell_changed)
        field_layout.addWidget(self._field_table)

        field_btn_layout = QHBoxLayout()
        self._add_field_btn = QPushButton("添加字段")
        self._add_field_btn.clicked.connect(self._add_field)
        self._del_field_btn = QPushButton("删除字段")
        self._del_field_btn.clicked.connect(self._delete_field)
        field_btn_layout.addWidget(self._add_field_btn)
        field_btn_layout.addWidget(self._del_field_btn)
        field_layout.addLayout(field_btn_layout)

        center_panel.addWidget(field_group)

        # 默认选择题
        choice_group = QGroupBox("默认选择题答案")
        choice_layout = QVBoxLayout(choice_group)

        self._choice_table = QTableWidget()
        self._choice_table.setColumnCount(2)
        self._choice_table.setHorizontalHeaderLabels(["题目关键词", "默认选项"])
        self._choice_table.horizontalHeader().setSectionResizeMode(
            0, QHeaderView.ResizeMode.Stretch
        )
        self._choice_table.horizontalHeader().setSectionResizeMode(
            1, QHeaderView.ResizeMode.Stretch
        )
        self._choice_table.cellChanged.connect(self._on_choice_cell_changed)
        choice_layout.addWidget(self._choice_table)

        choice_btn_layout = QHBoxLayout()
        self._add_choice_btn = QPushButton("添加")
        self._add_choice_btn.clicked.connect(self._add_choice)
        self._del_choice_btn = QPushButton("删除")
        self._del_choice_btn.clicked.connect(self._delete_choice)
        choice_btn_layout.addWidget(self._add_choice_btn)
        choice_btn_layout.addWidget(self._del_choice_btn)
        choice_layout.addLayout(choice_btn_layout)

        center_panel.addWidget(choice_group)
        main_layout.addLayout(center_panel, 1)

        # ===== 右侧：别名编辑 =====
        right_panel = QVBoxLayout()

        alias_group = QGroupBox("字段别名（用于匹配问卷题目）")
        alias_layout = QVBoxLayout(alias_group)

        self._alias_label = QLabel("选择左侧字段编辑别名")
        self._alias_label.setWordWrap(True)
        alias_layout.addWidget(self._alias_label)

        self._alias_edit = QTextEdit()
        self._alias_edit.setPlaceholderText("每行一个别名\n例如：\n你的名字\n请填写姓名\n学生姓名")
        self._alias_edit.textChanged.connect(self._on_alias_changed)
        alias_layout.addWidget(self._alias_edit)

        right_panel.addWidget(alias_group)
        right_panel.addStretch()
        main_layout.addLayout(right_panel)

    # ===== 刷新 =====

    def _refresh_all(self):
        """刷新所有UI组件"""
        self._refresh_preset_combo()
        self._refresh_field_table()
        self._refresh_choice_table()
        self._refresh_alias_editor()
        self._refresh_activate_button()

    def _refresh_preset_combo(self):
        self._preset_combo.blockSignals(True)
        self._preset_combo.clear()
        for i, profile in enumerate(self._pm.profiles):
            marker = " ★" if i == self._pm.active_index else ""
            self._preset_combo.addItem(f"{profile.name}{marker}", i)
        self._preset_combo.blockSignals(False)

    def _refresh_field_table(self):
        self._field_table.blockSignals(True)
        profile = self._get_current_profile()
        if profile is None:
            self._field_table.setRowCount(0)
            self._field_table.blockSignals(False)
            return

        fields = list(profile.fields.values())
        self._field_table.setRowCount(len(fields))
        for row, field in enumerate(fields):
            key_item = QTableWidgetItem(field.key)
            key_item.setFlags(key_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            self._field_table.setItem(row, 0, key_item)
            self._field_table.setItem(row, 1, QTableWidgetItem(field.value))
        self._field_table.blockSignals(False)

    def _refresh_choice_table(self):
        self._choice_table.blockSignals(True)
        profile = self._get_current_profile()
        if profile is None:
            self._choice_table.setRowCount(0)
            self._choice_table.blockSignals(False)
            return

        choices = list(profile.default_choices.items())
        self._choice_table.setRowCount(len(choices))
        for row, (key, value) in enumerate(choices):
            self._choice_table.setItem(row, 0, QTableWidgetItem(key))
            self._choice_table.setItem(row, 1, QTableWidgetItem(value))
        self._choice_table.blockSignals(False)

    def _refresh_alias_editor(self):
        self._alias_edit.blockSignals(True)
        profile = self._get_current_profile()
        if profile is None or self._current_field_key is None:
            self._alias_edit.clear()
            self._alias_label.setText("选择左侧字段编辑别名")
            self._alias_edit.setEnabled(False)
        else:
            field = profile.fields.get(self._current_field_key)
            if field:
                self._alias_edit.setPlainText("\n".join(field.aliases))
                self._alias_label.setText(f"字段「{field.key}」的别名:")
                self._alias_edit.setEnabled(True)
        self._alias_edit.blockSignals(False)

    def _refresh_activate_button(self):
        current = self._get_current_index()
        if current == self._pm.active_index:
            self._activate_btn.setText("★ 当前正在使用")
            self._activate_btn.setEnabled(False)
        else:
            self._activate_btn.setText("✅ 设为当前使用")
            self._activate_btn.setEnabled(True)

    def _get_current_index(self) -> int:
        idx = self._preset_combo.currentData()
        return idx if idx is not None else -1

    def _get_current_profile(self):
        idx = self._get_current_index()
        if 0 <= idx < len(self._pm.profiles):
            return self._pm.profiles[idx]
        return None

    # ===== 事件处理 =====

    def _on_preset_changed(self, index):
        self._current_field_key = None
        self._refresh_all()

    def _add_preset(self):
        name, ok = QInputDialog.getText(self, "新建预设", "请输入预设名称:")
        if ok and name.strip():
            self._pm.add_profile(name.strip())
            self._refresh_all()
            self._preset_combo.setCurrentIndex(len(self._pm.profiles) - 1)

    def _duplicate_preset(self):
        idx = self._get_current_index()
        if idx >= 0:
            self._pm.duplicate_profile(idx)
            self._refresh_all()
            self._preset_combo.setCurrentIndex(len(self._pm.profiles) - 1)

    def _delete_preset(self):
        idx = self._get_current_index()
        if idx < 0:
            return
        if len(self._pm.profiles) <= 1:
            QMessageBox.warning(self, "提示", "至少保留一个预设方案")
            return
        name = self._pm.profiles[idx].name
        reply = QMessageBox.question(
            self, "确认删除",
            f"确定要删除预设「{name}」吗？此操作不可恢复。",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if reply == QMessageBox.StandardButton.Yes:
            self._pm.remove_profile(idx)
            self._current_field_key = None
            self._refresh_all()
            self.profile_changed.emit()

    def _activate_preset(self):
        idx = self._get_current_index()
        if idx >= 0:
            self._pm.set_active_profile(idx)
            self._refresh_all()
            self.profile_changed.emit()

    def _add_field(self):
        idx = self._get_current_index()
        if idx < 0:
            return
        key, ok = QInputDialog.getText(self, "添加字段", "字段名（如：身份证号）:")
        if ok and key.strip():
            key = key.strip()
            profile = self._pm.profiles[idx]
            if key in profile.fields:
                QMessageBox.warning(self, "提示", f"字段「{key}」已存在")
                return
            self._pm.add_field(idx, key)
            self._refresh_field_table()
            self.profile_changed.emit()

    def _delete_field(self):
        idx = self._get_current_index()
        if idx < 0:
            return
        current_row = self._field_table.currentRow()
        if current_row < 0:
            return
        key_item = self._field_table.item(current_row, 0)
        if key_item is None:
            return
        key = key_item.text()
        self._pm.remove_field(idx, key)
        if self._current_field_key == key:
            self._current_field_key = None
        self._refresh_all()
        self.profile_changed.emit()

    def _on_field_selected(self):
        current_row = self._field_table.currentRow()
        if current_row >= 0:
            key_item = self._field_table.item(current_row, 0)
            if key_item:
                self._current_field_key = key_item.text()
                self._refresh_alias_editor()
        else:
            self._current_field_key = None
            self._refresh_alias_editor()

    def _on_field_cell_changed(self, row, col):
        if col != 1:
            return
        idx = self._get_current_index()
        if idx < 0:
            return
        key_item = self._field_table.item(row, 0)
        value_item = self._field_table.item(row, 1)
        if key_item and value_item:
            self._pm.update_field(idx, key_item.text(), value=value_item.text())
            self.profile_changed.emit()

    def _on_alias_changed(self):
        idx = self._get_current_index()
        if idx < 0 or self._current_field_key is None:
            return
        text = self._alias_edit.toPlainText()
        aliases = [line.strip() for line in text.split("\n") if line.strip()]
        self._pm.update_field(idx, self._current_field_key, aliases=aliases)
        self.profile_changed.emit()

    def _add_choice(self):
        idx = self._get_current_index()
        if idx < 0:
            return
        key, ok = QInputDialog.getText(self, "添加默认选择", "题目关键词（如：性别）:")
        if not ok or not key.strip():
            return
        answer, ok = QInputDialog.getText(self, "添加默认选择", f"当题目包含「{key}」时的默认选项:")
        if ok and answer.strip():
            self._pm.add_default_choice(idx, key.strip(), answer.strip())
            self._refresh_choice_table()
            self.profile_changed.emit()

    def _delete_choice(self):
        idx = self._get_current_index()
        if idx < 0:
            return
        current_row = self._choice_table.currentRow()
        if current_row < 0:
            return
        key_item = self._choice_table.item(current_row, 0)
        if key_item:
            self._pm.remove_default_choice(idx, key_item.text())
            self._refresh_choice_table()
            self.profile_changed.emit()

    def _on_choice_cell_changed(self, row, col):
        idx = self._get_current_index()
        if idx < 0:
            return
        key_item = self._choice_table.item(row, 0)
        value_item = self._choice_table.item(row, 1)
        if key_item and value_item:
            self._pm.remove_default_choice(idx, key_item.text())
            self._pm.add_default_choice(idx, key_item.text(), value_item.text())
            self.profile_changed.emit()

    def _import_profiles(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "导入预设", "", "JSON文件 (*.json);;所有文件 (*)"
        )
        if path:
            try:
                self._pm.import_from_file(path)
                self._current_field_key = None
                self._refresh_all()
                self.profile_changed.emit()
                QMessageBox.information(self, "导入成功", "预设信息已成功导入")
            except Exception as e:
                QMessageBox.critical(self, "导入失败", f"导入失败：{e}")

    def _export_profiles(self):
        path, _ = QFileDialog.getSaveFileName(
            self, "导出预设", "profiles.json", "JSON文件 (*.json);;所有文件 (*)"
        )
        if path:
            try:
                self._pm.export_to_file(path)
                QMessageBox.information(self, "导出成功", f"已导出到：{path}")
            except Exception as e:
                QMessageBox.critical(self, "导出失败", f"导出失败：{e}")
