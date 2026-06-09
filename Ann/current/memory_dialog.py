"""
memory_dialog.py — Memory management dialog for Ann GUI.

Opens a scrollable panel listing all active memories with
Edit and Delete controls.  Launched via the /memory ui command.
"""
from __future__ import annotations

try:
    from PyQt6.QtWidgets import (
        QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
        QScrollArea, QWidget, QComboBox, QLineEdit, QFrame, QMessageBox,
    )
    from PyQt6.QtCore import Qt
except ImportError:
    from PySide6.QtWidgets import (
        QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
        QScrollArea, QWidget, QComboBox, QLineEdit, QFrame, QMessageBox,
    )
    from PySide6.QtCore import Qt

_DARK_BG = "#1A1D24"
_CARD_BG = "#22262F"
_BORDER  = "#2D3748"
_TEXT    = "#E2E8F0"
_MUTED   = "#A0AEC0"
_RED     = "#E53E3E"
_BLUE    = "#63B3ED"

_DIALOG_STYLE = f"""
QDialog {{ background-color: {_DARK_BG}; }}
QLabel {{ color: {_TEXT}; font-family: 'Segoe UI', Arial; font-size: 13px; }}
QComboBox {{
    background-color: {_CARD_BG}; color: {_TEXT}; border: 1px solid {_BORDER};
    border-radius: 6px; padding: 4px 8px; font-size: 12px;
}}
QComboBox QAbstractItemView {{ background-color: {_CARD_BG}; color: {_TEXT}; }}
QScrollArea {{ border: none; background-color: transparent; }}
QScrollBar:vertical {{ border: none; background: {_DARK_BG}; width: 8px; }}
QScrollBar::handle:vertical {{ background: #4A5568; border-radius: 4px; }}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0px; }}
"""

_BTN_EDIT = (
    f"QPushButton {{ background-color: #2B4A7A; color: {_BLUE}; border: 1px solid {_BLUE}33; "
    "border-radius: 5px; padding: 3px 10px; font-size: 11px; }"
    f"QPushButton:hover {{ background-color: #3A5F8A; }}"
)
_BTN_DEL = (
    f"QPushButton {{ background-color: #4A1A1A; color: {_RED}; border: 1px solid {_RED}33; "
    "border-radius: 5px; padding: 3px 10px; font-size: 11px; }"
    f"QPushButton:hover {{ background-color: #5E2222; }}"
)
_BTN_CLOSE = (
    f"QPushButton {{ background-color: #2D3748; color: {_TEXT}; border: none; "
    "border-radius: 8px; padding: 6px 20px; font-size: 12px; }"
    f"QPushButton:hover {{ background-color: #4A5568; }}"
)


class MemoryDialog(QDialog):
    """
    Scrollable memory management dialog.

    Shows all active memories with optional category filter.
    Each row has an Edit button (inline summary edit) and a Delete button.
    """

    def __init__(self, memory_manager, parent=None):
        super().__init__(parent)
        self.memory_manager = memory_manager
        self.setWindowTitle("Memory Management")
        self.setMinimumSize(560, 500)
        self.setStyleSheet(_DIALOG_STYLE)
        self.setWindowFlags(
            Qt.WindowType.Dialog | Qt.WindowType.WindowCloseButtonHint
        )
        self._build_ui()
        self._populate()

    # ------------------------------------------------------------------
    # UI construction
    # ------------------------------------------------------------------

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(14, 14, 14, 14)
        root.setSpacing(10)

        # Header
        header = QHBoxLayout()
        title = QLabel("🧠  Memory Management")
        title.setStyleSheet(f"color: {_TEXT}; font-size: 16px; font-weight: bold; font-family: 'Segoe UI';")
        header.addWidget(title)
        header.addStretch()

        self.stats_label = QLabel("")
        self.stats_label.setStyleSheet(f"color: {_MUTED}; font-size: 11px;")
        header.addWidget(self.stats_label)
        root.addLayout(header)

        # Filter bar
        filter_bar = QHBoxLayout()
        filter_bar.addWidget(QLabel("Filter:"))
        self.category_filter = QComboBox()
        self.category_filter.addItem("All")
        for cat in sorted(["profile", "preference", "project", "todo", "event", "skill", "correction", "system"]):
            self.category_filter.addItem(cat)
        self.category_filter.currentTextChanged.connect(self._on_filter_changed)
        filter_bar.addWidget(self.category_filter)
        filter_bar.addStretch()
        root.addLayout(filter_bar)

        # Scroll area for memory rows
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setStyleSheet(
            f"QScrollArea {{ border: 1px solid {_BORDER}; border-radius: 8px; background-color: {_CARD_BG}; }}"
        )
        self.list_widget = QWidget()
        self.list_widget.setStyleSheet(f"background-color: {_CARD_BG};")
        self.list_layout = QVBoxLayout(self.list_widget)
        self.list_layout.setContentsMargins(8, 8, 8, 8)
        self.list_layout.setSpacing(6)
        self.list_layout.addStretch()
        self.scroll_area.setWidget(self.list_widget)
        root.addWidget(self.scroll_area)

        # Close button
        btn_row = QHBoxLayout()
        btn_row.addStretch()
        close_btn = QPushButton("Close")
        close_btn.setStyleSheet(_BTN_CLOSE)
        close_btn.clicked.connect(self.accept)
        btn_row.addWidget(close_btn)
        root.addLayout(btn_row)

    # ------------------------------------------------------------------
    # Data loading
    # ------------------------------------------------------------------

    def _populate(self) -> None:
        """Load memories from manager and render rows."""
        self._all_memories = self.memory_manager.list_memories()
        stats = self.memory_manager.get_stats()
        self.stats_label.setText(
            f"Active: {stats['active']}  |  Total: {stats['total']}  |  {stats['size_kb']} KB"
        )
        self._render_rows(self._all_memories)

    def _render_rows(self, memories: list[dict]) -> None:
        """Clear list and render *memories*."""
        # Remove all existing rows (keep the trailing stretch)
        while self.list_layout.count() > 1:
            item = self.list_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        if not memories:
            empty = QLabel("No memories found.")
            empty.setStyleSheet(f"color: {_MUTED}; font-size: 12px; padding: 8px;")
            self.list_layout.insertWidget(0, empty)
            return

        for idx, unit in enumerate(memories):
            row = self._make_row(unit)
            self.list_layout.insertWidget(idx, row)

    def _make_row(self, unit: dict) -> QFrame:
        """Build a single memory row widget."""
        frame = QFrame()
        frame.setStyleSheet(
            f"QFrame {{ background-color: #262B35; border: 1px solid {_BORDER}; border-radius: 8px; }}"
        )
        layout = QVBoxLayout(frame)
        layout.setContentsMargins(10, 8, 10, 8)
        layout.setSpacing(4)

        # Top row: id + category tag
        top = QHBoxLayout()
        id_label = QLabel(unit["id"])
        id_label.setStyleSheet(f"color: {_MUTED}; font-size: 11px; font-family: monospace;")
        top.addWidget(id_label)

        cat_label = QLabel(unit["category"])
        cat_label.setStyleSheet(
            f"color: #68D391; font-size: 10px; border: 1px solid #276749; "
            f"border-radius: 4px; padding: 1px 5px; background: #1C4532;"
        )
        top.addWidget(cat_label)
        top.addStretch()

        conf_text = f"conf {unit.get('confidence', 0):.2f}"
        conf_label = QLabel(conf_text)
        conf_label.setStyleSheet(f"color: {_MUTED}; font-size: 10px;")
        top.addWidget(conf_label)
        layout.addLayout(top)

        # Summary (editable on demand; located by layout index in _on_edit)
        summary_label = QLabel(unit["summary"])
        summary_label.setStyleSheet(f"color: {_TEXT}; font-size: 12px;")
        summary_label.setWordWrap(True)
        layout.addWidget(summary_label)

        # Keywords
        kw_label = QLabel("  ".join(f"#{k}" for k in unit.get("keywords", [])))
        kw_label.setStyleSheet(f"color: #76E4F7; font-size: 10px;")
        layout.addWidget(kw_label)

        # Action buttons
        btn_row = QHBoxLayout()
        btn_row.addStretch()

        edit_btn = QPushButton("✏ Edit")
        edit_btn.setStyleSheet(_BTN_EDIT)
        edit_btn.clicked.connect(lambda _, u=unit, f=frame: self._on_edit(u, f))
        btn_row.addWidget(edit_btn)

        del_btn = QPushButton("🗑 Delete")
        del_btn.setStyleSheet(_BTN_DEL)
        del_btn.clicked.connect(lambda _, u=unit: self._on_delete(u))
        btn_row.addWidget(del_btn)
        layout.addLayout(btn_row)

        return frame

    # ------------------------------------------------------------------
    # Actions
    # ------------------------------------------------------------------

    def _on_filter_changed(self, category: str) -> None:
        if category == "All":
            self._render_rows(self._all_memories)
        else:
            filtered = [m for m in self._all_memories if m["category"] == category]
            self._render_rows(filtered)

    def _on_edit(self, unit: dict, frame: QFrame) -> None:
        """Replace summary label with an inline edit field inside *frame*."""
        layout = frame.layout()

        # Find and remove the existing summary label (index 1)
        summary_item = layout.itemAt(1)
        if summary_item and summary_item.widget():
            old_label = summary_item.widget()
            current_text = old_label.text()
            layout.removeWidget(old_label)
            old_label.deleteLater()

            edit_field = QLineEdit(current_text)
            edit_field.setStyleSheet(
                f"QLineEdit {{ background-color: {_DARK_BG}; color: {_TEXT}; "
                f"border: 1px solid {_BLUE}; border-radius: 4px; padding: 3px 6px; font-size: 12px; }}"
            )
            layout.insertWidget(1, edit_field)

            # Swap edit button to Save
            btn_row_item = layout.itemAt(layout.count() - 1)
            if btn_row_item:
                btn_layout = btn_row_item.layout()
                if btn_layout and btn_layout.count() >= 2:
                    edit_btn_item = btn_layout.itemAt(1)
                    if edit_btn_item and edit_btn_item.widget():
                        edit_btn = edit_btn_item.widget()
                        edit_btn.setText("💾 Save")
                        try:
                            edit_btn.clicked.disconnect()
                        except Exception:
                            pass
                        edit_btn.clicked.connect(
                            lambda _, u=unit, ef=edit_field, eb=edit_btn, fr=frame:
                                self._on_save(u, ef, eb, fr)
                        )

    def _on_save(self, unit: dict, edit_field: QLineEdit, save_btn: QPushButton, frame: QFrame) -> None:
        new_summary = edit_field.text().strip()
        if not new_summary:
            return
        success = self.memory_manager.edit_memory(unit["id"], summary=new_summary)
        if success:
            unit["summary"] = new_summary
            # Replace edit field back with label
            layout = frame.layout()
            edit_item = layout.itemAt(1)
            if edit_item and edit_item.widget():
                layout.removeWidget(edit_item.widget())
                edit_item.widget().deleteLater()
            new_label = QLabel(new_summary)
            new_label.setStyleSheet(f"color: {_TEXT}; font-size: 12px;")
            new_label.setWordWrap(True)
            layout.insertWidget(1, new_label)
            save_btn.setText("✏ Edit")
            try:
                save_btn.clicked.disconnect()
            except Exception:
                pass
            save_btn.clicked.connect(lambda _, u=unit, f=frame: self._on_edit(u, f))
        else:
            QMessageBox.warning(self, "Edit Failed", f"Could not edit memory {unit['id']}.")

    def _on_delete(self, unit: dict) -> None:
        confirm = QMessageBox.question(
            self,
            "Delete Memory",
            f"Delete memory {unit['id']}?\n\n{unit['summary']}",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if confirm == QMessageBox.StandardButton.Yes:
            success = self.memory_manager.delete_memory(unit["id"])
            if success:
                self._all_memories = [m for m in self._all_memories if m["id"] != unit["id"]]
                self._on_filter_changed(self.category_filter.currentText())
                stats = self.memory_manager.get_stats()
                self.stats_label.setText(
                    f"Active: {stats['active']}  |  Total: {stats['total']}  |  {stats['size_kb']} KB"
                )
            else:
                QMessageBox.warning(self, "Delete Failed", f"Could not delete memory {unit['id']}.")
