#!/usr/bin/env python3
"""
Ann GUI frontend — PyQt6 implementation of Scheme B.
Features a draggable floating bubble that expands into a sleek dark-mode chat window.
"""
import sys
import logging
from pathlib import Path
try:
    from PyQt6.QtWidgets import (
        QApplication, QWidget, QVBoxLayout, QHBoxLayout, QLineEdit,
        QPushButton, QLabel, QScrollArea, QFrame, QSizePolicy, QDialog, QTextEdit, QFileDialog
    )
    from PyQt6.QtCore import Qt, QPoint, QPropertyAnimation, QEasingCurve, pyqtSignal, QObject, QThread, QTimer
    from PyQt6.QtGui import QPainter, QColor, QLinearGradient, QPen, QBrush, QPixmap
except ImportError:
    from PySide6.QtWidgets import (
        QApplication, QWidget, QVBoxLayout, QHBoxLayout, QLineEdit,
        QPushButton, QLabel, QScrollArea, QFrame, QSizePolicy, QDialog, QTextEdit, QFileDialog
    )
    from PySide6.QtCore import Qt, QPoint, QPropertyAnimation, QEasingCurve, Signal, QObject, QThread, QTimer
    from PySide6.QtGui import QPainter, QColor, QLinearGradient, QPen, QBrush, QPixmap
    # Map PySide6 Signal to pyqtSignal name
    pyqtSignal = Signal

# Import core elements from assistant.py and moral_evaluator.py
from alarm_handler import detect_update_intent, handle_alarm_intent
from assistant import load_config, call_ollama, SYSTEM_PROMPT, BASE_DIR, EXIT_UPDATE, EXIT_RESTART
from moral_evaluator import MoralEvaluator, Decision

# Set up logging for GUI
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] (GUI) %(message)s")


class OllamaWorker(QThread):
    """Worker thread to handle blocking Ollama requests without freezing the GUI."""
    finished = pyqtSignal(str, str)  # Emits (reply_text, error_message)

    def __init__(self, base_url: str, model: str, messages: list[dict], images: list = None):
        super().__init__()
        self.base_url = base_url
        self.model = model
        self.messages = messages
        self.images = images

    def run(self) -> None:
        try:
            from ollama_client import OllamaClient
            client = OllamaClient(self.base_url)
            reply = client.chat(self.model, self.messages, self.images)
            self.finished.emit(reply, "")
        except Exception as e:
            self.finished.emit("", str(e))


class UpdateCheckWorker(QThread):
    """Worker thread to run GitHub update check asynchronously without freezing the GUI."""
    finished = pyqtSignal(str, str)  # Emits (new_version, error_message)

    def __init__(self, config: dict, base_dir: Path):
        super().__init__()
        self.config = config
        self.base_dir = base_dir

    def run(self) -> None:
        try:
            from version_check import check_for_update
            new_tag = check_for_update(self.config, self.base_dir)
            self.finished.emit(new_tag or "", "")
        except Exception as e:
            self.finished.emit("", str(e))


class NewsWorker(QThread):
    """Worker thread to handle news parsing, fetching, and summarization asynchronously."""
    finished = pyqtSignal(str, str)  # Emits (reply_text, error_message)

    def __init__(self, news_manager, user_text: str):
        super().__init__()
        self.news_manager = news_manager
        self.user_text = user_text

    def run(self) -> None:
        try:
            parsed = self.news_manager.intent_parser.parse_intent(self.user_text)
            if parsed["intent"] != "none":
                reply = self.news_manager.handle_intent(self.user_text, parsed)
                self.finished.emit(reply, "")
            else:
                self.finished.emit("", "not_news")
        except Exception as e:
            logging.error("NewsWorker error: %s", e)
            self.finished.emit("", str(e))


class DragDropOverlay(QWidget):
    """Semi-transparent overlay shown when files are dragged over the window."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
        self.hide()
        
    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        # Semitransparent background matching the sleek dark theme
        painter.fillRect(self.rect(), QColor(26, 29, 36, 210))
        
        # Draw dashed border
        pen = QPen(QColor(72, 187, 120), 2, Qt.PenStyle.DashLine)
        painter.setPen(pen)
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawRoundedRect(10, 10, self.width() - 20, self.height() - 20, 12, 12)
        
        # Draw text
        painter.setPen(QColor(226, 232, 240))
        font = painter.font()
        font.setPointSize(14)
        font.setBold(True)
        font.setFamily("Segoe UI")
        painter.setFont(font)
        painter.drawText(self.rect(), Qt.AlignmentFlag.AlignCenter, "(Drop files to load)")


class AttachmentViewerDialog(QDialog):
    """Dialog to preview attached text contents or images."""
    def __init__(self, file_path: Path, parent=None):
        super().__init__(parent)
        self.setWindowTitle(f"Preview: {file_path.name}")
        self.resize(600, 500)
        self.setStyleSheet("background-color: #1A1D24; color: #E2E8F0; border: 1px solid #2D3748;")
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(15, 15, 15, 15)
        layout.setSpacing(10)
        
        # Title text (file name)
        title_lbl = QLabel(file_path.name)
        title_lbl.setStyleSheet("font-size: 15px; font-weight: bold; color: #E2E8F0; border: none;")
        layout.addWidget(title_lbl)
        
        suffix = file_path.suffix.lower()
        is_image = suffix in ['.png', '.jpg', '.jpeg', '.webp', '.bmp']
        
        if is_image:
            scroll_area = QScrollArea()
            scroll_area.setStyleSheet("QScrollArea { border: 1px solid #2D3748; background-color: #111317; border-radius: 8px; }")
            scroll_area.setWidgetResizable(True)
            
            img_label = QLabel()
            img_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            img_label.setStyleSheet("background-color: transparent; border: none;")
            
            pixmap = QPixmap(str(file_path))
            if not pixmap.isNull():
                img_label.setPixmap(pixmap)
                img_label.setScaledContents(False)
            else:
                img_label.setText("Failed to load image.")
                
            scroll_area.setWidget(img_label)
            layout.addWidget(scroll_area)
        else:
            # Assume text file
            text_edit = QTextEdit()
            text_edit.setReadOnly(True)
            text_edit.setStyleSheet(
                "QTextEdit { background-color: #2D3748; border: 1px solid #4A5568; "
                "border-radius: 8px; color: #E2E8F0; font-family: 'Consolas', 'Courier New', monospace; "
                "font-size: 13px; padding: 10px; }"
            )
            
            # Read file safely
            try:
                if file_path.stat().st_size > 5 * 1024 * 1024:
                    text_content = "File is too large to preview (limit 5MB)."
                else:
                    try:
                        text_content = file_path.read_text(encoding='utf-8')
                    except UnicodeDecodeError:
                        try:
                            text_content = file_path.read_text(encoding='utf-8-sig')
                        except UnicodeDecodeError:
                            text_content = file_path.read_text(encoding='latin-1')
            except Exception as e:
                text_content = f"Error reading file: {str(e)}"
                
            text_edit.setPlainText(text_content)
            layout.addWidget(text_edit)
            
        # Action Row containing Close button
        actions_layout = QHBoxLayout()
        actions_layout.addStretch()
        
        close_btn = QPushButton("Close")
        close_btn.setStyleSheet(
            "QPushButton { color: white; background-color: #3182CE; border: none; "
            "border-radius: 8px; padding: 8px 20px; font-weight: bold; font-family: 'Segoe UI'; font-size: 13px; }"
            "QPushButton:hover { background-color: #2B6CB0; }"
        )
        close_btn.clicked.connect(self.accept)
        actions_layout.addWidget(close_btn)
        layout.addLayout(actions_layout)


class AttachmentItem(QFrame):
    """Badge widget for individual file attachments in the tray."""
    clicked_file = pyqtSignal(Path)
    removed = pyqtSignal(Path)
    
    def __init__(self, file_path: Path):
        super().__init__()
        self.file_path = file_path
        self.setStyleSheet(
            "QFrame { background-color: #2D3748; border: 1px solid #4A5568; "
            "border-radius: 12px; padding: 2px 8px; }"
        )
        layout = QHBoxLayout(self)
        layout.setContentsMargins(6, 2, 6, 2)
        layout.setSpacing(6)
        
        # Icon / Thumbnail
        suffix = file_path.suffix.lower()
        is_image = suffix in ['.png', '.jpg', '.jpeg', '.webp', '.bmp']
        
        icon_label = QLabel()
        icon_label.setFixedSize(16, 16)
        icon_label.setStyleSheet("border: none; background-color: transparent;")
        if is_image:
            pixmap = QPixmap(str(file_path))
            if not pixmap.isNull():
                scaled_pixmap = pixmap.scaled(16, 16, Qt.AspectRatioMode.KeepAspectRatioByExpanding, Qt.TransformationMode.SmoothTransformation)
                icon_label.setPixmap(scaled_pixmap)
            else:
                icon_label.setText("🖼️")
        else:
            icon_label.setText("📄")
        layout.addWidget(icon_label)
        
        # Clickable File Name Link
        name_btn = QPushButton(file_path.name)
        name_btn.setStyleSheet(
            "QPushButton { color: #63B3ED; border: none; background-color: transparent; "
            "text-align: left; font-family: 'Segoe UI'; font-size: 12px; padding: 0px; text-decoration: underline; }"
            "QPushButton:hover { color: #90CDF4; }"
        )
        name_btn.clicked.connect(lambda: self.clicked_file.emit(self.file_path))
        layout.addWidget(name_btn)
        
        # Remove button
        remove_btn = QPushButton("×")
        remove_btn.setFixedSize(16, 16)
        remove_btn.setStyleSheet(
            "QPushButton { color: #E53E3E; border: none; background-color: transparent; "
            "font-size: 14px; font-weight: bold; padding: 0px; }"
            "QPushButton:hover { color: #FC8181; }"
        )
        remove_btn.clicked.connect(lambda: self.removed.emit(self.file_path))
        layout.addWidget(remove_btn)


def parse_markdown_blocks(text: str) -> list[dict]:
    """
    Parses response text and splits it into a sequence of text and code blocks.
    """
    from file_handler import parse_markdown_blocks as parse
    return parse(text)


class CodeBlockWidget(QFrame):
    """Container for displaying parsed markdown code blocks with an option to save to file."""
    def __init__(self, language: str, code_content: str, parent=None):
        super().__init__(parent)
        self.language = language or "txt"
        self.code_content = code_content
        
        self.setStyleSheet(
            "CodeBlockWidget { background-color: #1E222A; border: 1px solid #2D3139; "
            "border-radius: 8px; }"
        )
        
        # Vertical layout
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        # Header bar
        header = QFrame()
        header.setFixedHeight(28)
        header.setStyleSheet(
            "background-color: #181A1F; border-top-left-radius: 8px; border-top-right-radius: 8px; "
            "border-bottom: 1px solid #2D3139;"
        )
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(10, 0, 10, 0)
        
        # Language Label
        lang_lbl = QLabel(self.language.upper())
        lang_lbl.setStyleSheet(
            "color: #ABB2BF; font-weight: bold; font-family: 'Segoe UI'; font-size: 11px; border: none; background: transparent;"
        )
        header_layout.addWidget(lang_lbl)
        header_layout.addStretch()
        
        # Save Button
        save_btn = QPushButton("💾 另存檔案")
        save_btn.setStyleSheet(
            "QPushButton { color: #61AFEF; border: none; background-color: transparent; "
            "font-family: 'Segoe UI'; font-weight: bold; font-size: 11px; padding: 0px; }"
            "QPushButton:hover { color: #56B6C2; text-decoration: underline; }"
        )
        save_btn.clicked.connect(self.save_to_file)
        header_layout.addWidget(save_btn)
        
        layout.addWidget(header)
        
        # Code body
        self.code_edit = QTextEdit()
        self.code_edit.setPlainText(self.code_content)
        self.code_edit.setReadOnly(True)
        # Monospace styling for code block
        self.code_edit.setStyleSheet(
            "QTextEdit { background-color: #1E222A; border: none; "
            "border-bottom-left-radius: 8px; border-bottom-right-radius: 8px; "
            "color: #ABB2BF; font-family: 'Consolas', 'Courier New', monospace; "
            "font-size: 13px; padding: 8px; }"
        )
        
        # Estimate height based on line count to avoid layout rendering latency issues
        lines_count = self.code_content.count('\n') + 1
        self.code_edit.setFixedHeight(min(max(lines_count * 18 + 20, 80), 300))
        
        layout.addWidget(self.code_edit)

    def save_to_file(self) -> None:
        # File type filter mapping based on code block language
        filters = {
            "py": "Python Files (*.py)",
            "python": "Python Files (*.py)",
            "c": "C Source Files (*.c *.h)",
            "cpp": "C++ Source Files (*.cpp *.h *.hpp)",
            "c++": "C++ Source Files (*.cpp *.h *.hpp)",
            "java": "Java Files (*.java)",
            "sh": "Shell Scripts (*.sh)",
            "bash": "Shell Scripts (*.sh)",
            "html": "HTML Files (*.html)",
            "htm": "HTML Files (*.html)",
            "xml": "XML Files (*.xml)",
            "css": "CSS Files (*.css)",
            "js": "JavaScript Files (*.js)",
            "javascript": "JavaScript Files (*.js)",
            "ts": "TypeScript Files (*.ts)",
            "typescript": "TypeScript Files (*.ts)",
            "sql": "SQL Scripts (*.sql)",
            "toml": "TOML Files (*.toml)",
            "json": "JSON Files (*.json)",
            "yaml": "YAML Files (*.yaml *.yml)",
            "yml": "YAML Files (*.yaml *.yml)",
            "md": "Markdown Documents (*.md)",
            "markdown": "Markdown Documents (*.md)",
            "ini": "Config Files (*.ini *.cfg *.conf)",
            "cfg": "Config Files (*.ini *.cfg *.conf)",
            "conf": "Config Files (*.ini *.cfg *.conf)",
            "env": "Environment Files (*.env)",
        }
        
        lang = self.language.lower()
        default_filter = filters.get(lang, "Text Files (*.txt);;All Files (*)")
        default_ext = "." + lang if lang in filters else ".txt"
        
        # Open save file dialog
        file_path_str, _ = QFileDialog.getSaveFileName(
            self,
            "另存新檔 (Save Code Block)",
            f"code{default_ext}",
            default_filter
        )
        
        if file_path_str:
            try:
                Path(file_path_str).write_text(self.code_content, encoding="utf-8")
                logging.info("Successfully saved code block to %s", file_path_str)
            except Exception as e:
                logging.error("Failed to save code block: %s", e)


class MessageBubble(QFrame):
    """Custom styled chat message bubble."""
    def __init__(self, text: str, is_user: bool, is_refusal: bool = False):
        super().__init__()
        layout = QHBoxLayout(self)
        layout.setContentsMargins(10, 5, 10, 5)

        # Style colors
        if is_refusal:
            bg_color = "#5C2525"
            text_color = "#FCA5A5"
            border_color = "#7F1D1D"
        elif is_user:
            bg_color = "#2B6CB0"  # Slate Blue
            text_color = "#E2E8F0"
            border_color = "#2B6CB0"
        else:
            bg_color = "#2D3748"  # Dark Gray
            text_color = "#E2E8F0"
            border_color = "#1A202C"

        bubble = QFrame()
        bubble.setStyleSheet(
            f"background-color: {bg_color}; border: 1px solid {border_color}; "
            f"border-radius: 12px; padding: 8px;"
        )
        bubble.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        bubble_layout = QVBoxLayout(bubble)
        bubble_layout.setContentsMargins(8, 8, 8, 8)
        bubble_layout.setSpacing(6)

        # Parse text and add labels or CodeBlockWidgets
        blocks = parse_markdown_blocks(text)
        for block in blocks:
            if block["type"] == "text":
                content = block["content"]
                # Only add if it has non-whitespace characters or is the only block
                if content.strip() or len(blocks) == 1:
                    label = QLabel(content)
                    label.setWordWrap(True)
                    label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
                    label.setStyleSheet(
                        f"color: {text_color}; font-size: 13px; font-family: 'Segoe UI', Arial; "
                        f"background-color: transparent; border: none; padding: 0px;"
                    )
                    bubble_layout.addWidget(label)
            elif block["type"] == "code":
                code_widget = CodeBlockWidget(block["language"], block["content"])
                code_widget.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
                bubble_layout.addWidget(code_widget)

        if is_user:
            layout.addStretch()
            layout.addWidget(bubble)
        else:
            layout.addWidget(bubble)
            layout.addStretch()


class ChatWindow(QWidget):
    """Main Chat Window (State 2 of Scheme B)."""
    closed_to_bubble = pyqtSignal(QPoint)

    def __init__(self, config: dict, evaluator: MoralEvaluator, bubble, alarm_manager, alarm_trigger, alarm_scheduler, intent_parser, new_tag: str = None):
        super().__init__()
        self.config = config
        self.evaluator = evaluator
        self.bubble = bubble
        self.alarm_manager = alarm_manager
        self.alarm_trigger = alarm_trigger
        self.alarm_scheduler = alarm_scheduler
        self.intent_parser = intent_parser
        self.conversation: list[dict] = []
        self.drag_position = QPoint()
        self.awaiting_update_confirm = False
        self.pending_version = None
        self.update_worker = None

        # Initialize OllamaClient
        from ollama_client import OllamaClient
        llm_base_url = self.config["llm"].get("base_url", "http://localhost:11434")
        self.ollama_client = OllamaClient(llm_base_url)

        # Initialize FileIntentParser
        from file_handler import FileIntentParser
        self.file_intent_parser = FileIntentParser(
            base_url=llm_base_url,
            model=self.config["llm"]["model"]
        )

        # Initialize NewsManager
        from news.news_manager import NewsManager
        self.news_manager = NewsManager(
            base_dir=BASE_DIR,
            base_url=llm_base_url,
            model=self.config["llm"]["model"]
        )

        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint | Qt.WindowType.Tool)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.resize(360, 500)

        # Main background card
        self.card = QFrame(self)
        self.card.setGeometry(0, 0, 360, 500)
        self.card.setStyleSheet(
            "QFrame { background-color: #1A1D24; border: 1px solid #2D3748; "
            "border-radius: 16px; }"
        )

        # Main Layout inside the card
        card_layout = QVBoxLayout(self.card)
        card_layout.setContentsMargins(10, 10, 10, 10)

        # --- Custom Title Bar ---
        title_layout = QHBoxLayout()
        
        self.title_label = QLabel("Ann")
        self.title_label.setStyleSheet(
            "color: #E2E8F0; font-size: 16px; font-weight: bold; font-family: 'Segoe UI', Arial;"
        )
        title_layout.addWidget(self.title_label)
        title_layout.addStretch()

        # Minimize/Shrink button
        self.shrink_btn = QPushButton("▼")
        self.shrink_btn.setFixedSize(28, 28)
        self.shrink_btn.setStyleSheet(
            "QPushButton { color: #A0AEC0; background-color: #2D3748; border: none; "
            "border-radius: 14px; font-size: 12px; }"
            "QPushButton:hover { background-color: #4A5568; color: white; }"
        )
        self.shrink_btn.clicked.connect(self.shrink_back)
        title_layout.addWidget(self.shrink_btn)

        card_layout.addLayout(title_layout)

        # --- Message Area (Scrollable) ---
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setStyleSheet(
            "QScrollArea { border: none; background-color: transparent; }"
            "QScrollBar:vertical { border: none; background: #1A1D24; width: 8px; }"
            "QScrollBar::handle:vertical { background: #4A5568; border-radius: 4px; }"
            "QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0px; }"
        )

        self.scroll_widget = QWidget()
        self.scroll_widget.setStyleSheet("background-color: transparent;")
        self.scroll_layout = QVBoxLayout(self.scroll_widget)
        self.scroll_layout.setContentsMargins(0, 0, 0, 0)
        self.scroll_layout.addStretch()
        self.scroll_area.setWidget(self.scroll_widget)

        card_layout.addWidget(self.scroll_area)

        # --- Dismiss Alarm Button ---
        self.dismiss_btn = QPushButton("🔔 關閉鬧鐘 🔔")
        self.dismiss_btn.setStyleSheet(
            "QPushButton { color: white; background-color: #E53E3E; border: none; "
            "border-radius: 12px; padding: 10px; font-size: 14px; font-weight: bold; margin-bottom: 5px; }"
            "QPushButton:hover { background-color: #C53030; }"
        )
        self.dismiss_btn.clicked.connect(self.dismiss_alarm)
        self.dismiss_btn.hide()
        card_layout.addWidget(self.dismiss_btn)

        # --- Bottom Input Area ---
        input_layout = QHBoxLayout()

        self.input_field = QLineEdit()
        self.input_field.setPlaceholderText("Type a message...")
        self.input_field.setStyleSheet(
            "QLineEdit { color: white; background-color: #2D3748; border: 1px solid #4A5568; "
            "border-radius: 16px; padding: 8px 12px; font-size: 13px; font-family: 'Segoe UI'; }"
            "QLineEdit:focus { border: 1px solid #3182CE; }"
        )
        self.input_field.returnPressed.connect(self.send_message)
        input_layout.addWidget(self.input_field)

        self.send_btn = QPushButton("Send")
        self.send_btn.setStyleSheet(
            "QPushButton { color: white; background-color: #3182CE; border: none; "
            "border-radius: 16px; padding: 8px 16px; font-size: 13px; font-weight: bold; }"
            "QPushButton:hover { background-color: #2B6CB0; }"
        )
        self.send_btn.clicked.connect(self.send_message)
        input_layout.addWidget(self.send_btn)

        # --- Attachment Tray ---
        self.attachments = []
        self.attachment_tray = QWidget()
        self.attachment_tray.setStyleSheet("background-color: transparent;")
        self.tray_layout = QHBoxLayout(self.attachment_tray)
        self.tray_layout.setContentsMargins(4, 2, 4, 2)
        self.tray_layout.setSpacing(6)
        self.tray_layout.addStretch()
        self.attachment_tray.hide()
        card_layout.addWidget(self.attachment_tray)

        card_layout.addLayout(input_layout)

        # Drag and Drop support
        self.setAcceptDrops(True)
        self.drag_overlay = DragDropOverlay(self)
        self.drag_overlay.setGeometry(self.rect())

        # Welcome message
        if new_tag:
            self.awaiting_update_confirm = True
            self.pending_version = new_tag
            self.add_message(f"Hello! I am Ann, your safety-conscious assistant. 偵測到新版本 {new_tag}。請問您現在需要更新嗎？[y/n]", is_user=False)
        else:
            self.add_message("Hello! I am Ann, your safety-conscious assistant. How can I help you today?", is_user=False)

    # Window Dragging
    def mousePressEvent(self, event) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            self.drag_position = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
            event.accept()

    def mouseMoveEvent(self, event) -> None:
        if event.buttons() == Qt.MouseButton.LeftButton:
            self.move(event.globalPosition().toPoint() - self.drag_position)
            event.accept()

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        if hasattr(self, 'drag_overlay') and self.drag_overlay:
            self.drag_overlay.setGeometry(self.rect())

    def dragEnterEvent(self, event) -> None:
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
            if hasattr(self, 'drag_overlay') and self.drag_overlay:
                self.drag_overlay.show()

    def dragLeaveEvent(self, event) -> None:
        if hasattr(self, 'drag_overlay') and self.drag_overlay:
            self.drag_overlay.hide()

    def dropEvent(self, event) -> None:
        if hasattr(self, 'drag_overlay') and self.drag_overlay:
            self.drag_overlay.hide()
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
            for url in event.mimeData().urls():
                file_path = Path(url.toLocalFile())
                if file_path.is_file():
                    suffix = file_path.suffix.lower()
                    allowed_text = ['.txt', '.md', '.py', '.js', '.json', '.csv', '.html', '.css', '.yaml', '.yml', '.ini', '.cfg', '.log', '.c', '.cpp', '.java', '.sh', '.ts', '.sql', '.toml', '.env', '.xml']
                    allowed_img = ['.png', '.jpg', '.jpeg', '.webp', '.bmp']
                    if suffix in allowed_text or suffix in allowed_img:
                        self.add_attachment(file_path)
                    else:
                        logging.info("Dropped unsupported file format: %s", suffix)

    def add_attachment(self, file_path: Path) -> None:
        if file_path in self.attachments:
            return
        try:
            if file_path.stat().st_size > 5 * 1024 * 1024:
                self.add_message(f"⚠️ 檔案過大: {file_path.name} 超過 5MB 限制。", is_user=False, is_refusal=True)
                return
        except Exception as e:
            logging.error("Error checking file size: %s", e)
            return

        self.attachments.append(file_path)
        item = AttachmentItem(file_path)
        item.clicked_file.connect(self.show_attachment_preview)
        item.removed.connect(self.remove_attachment)
        self.tray_layout.insertWidget(self.tray_layout.count() - 1, item)
        self.attachment_tray.show()

    def remove_attachment(self, file_path: Path) -> None:
        if file_path in self.attachments:
            self.attachments.remove(file_path)
            for i in range(self.tray_layout.count()):
                widget = self.tray_layout.itemAt(i).widget()
                if isinstance(widget, AttachmentItem) and widget.file_path == file_path:
                    widget.deleteLater()
                    break
            if not self.attachments:
                self.attachment_tray.hide()

    def clear_attachments(self) -> None:
        self.attachments.clear()
        for i in reversed(range(self.tray_layout.count())):
            item = self.tray_layout.itemAt(i)
            widget = item.widget()
            if isinstance(widget, AttachmentItem):
                widget.deleteLater()
        self.attachment_tray.hide()

    def show_attachment_preview(self, file_path: Path) -> None:
        dialog = AttachmentViewerDialog(file_path, self)
        dialog.exec()

    def shrink_back(self) -> None:
        """Collapse the chat window back into the floating bubble."""
        # If alarm is active, transfer visual target back to bubble
        if self.bubble.active_triggered_alarms:
            self.alarm_trigger.stop_visual_effects()
            self.alarm_trigger.start_visual_effects(self.bubble)
            
        self.closed_to_bubble.emit(self.pos() + self.rect().center())
        self.hide()

    def dismiss_alarm(self) -> None:
        self.bubble.dismiss_alarm()

    def add_message(self, text: str, is_user: bool, is_refusal: bool = False) -> None:
        """Add a bubble message to the chat view."""
        bubble = MessageBubble(text, is_user, is_refusal)
        self.scroll_layout.insertWidget(self.scroll_layout.count() - 1, bubble)
        
        # Force layout update to compute correct scroll maximum synchronously
        self.scroll_layout.activate()
        self.scroll_widget.adjustSize()
        
        QApplication.processEvents()
        
        # Scroll to bottom with a short delay to ensure layout has calculated new size
        scroll_bar = self.scroll_area.verticalScrollBar()
        QTimer.singleShot(50, lambda: scroll_bar.setValue(scroll_bar.maximum()))

    def send_message(self) -> None:
        user_text = self.input_field.text().strip()
        if not user_text:
            return

        if user_text.lower() == "exit":
            QApplication.quit()
            return

        # Intercept update confirmation replies
        if self.awaiting_update_confirm:
            self.input_field.clear()
            self.add_message(user_text, is_user=True)
            user_input_lower = user_text.lower()
            intent = detect_update_intent(user_input_lower)

            if intent == "yes":
                llm_message = (
                    f"[System Instruction: The user confirmed they want to install the available update (version {self.pending_version}). "
                    f"Reply with a warm goodbye and state that you are starting the update. "
                    f"You MUST append the marker '[UPDATE]' at the very end of your response so the system can run the updater.]\n\n"
                    f"User: {user_text}"
                )
                self.conversation.append({"role": "user", "content": llm_message})
                self.awaiting_update_confirm = False
                self.pending_version = None
                
                # Prepend system prompt
                messages_with_system = [
                    {"role": "system", "content": SYSTEM_PROMPT},
                    *self.conversation,
                ]
                
                # Call Ollama asynchronously via worker thread
                llm_base_url = self.config["llm"].get("base_url", "http://localhost:11434")
                self.send_btn.setEnabled(False)
                self.input_field.setEnabled(False)
                self.title_label.setText("Ann is typing...")
                
                self.worker = OllamaWorker(llm_base_url, self.config["llm"]["model"], messages_with_system, None)
                self.worker.finished.connect(self.handle_reply)
                self.worker.start()
                return
            elif intent == "no":
                self.awaiting_update_confirm = False
                self.pending_version = None
                self.add_message("好的，那我們先不更新。如果您想再次檢查，可以隨時對我說『更新』。", is_user=False)
                return
            else:
                self.add_message("我不太確定您的意思。請問您現在需要更新程式嗎？（您可以回答「好/要」來更新，或回答「不用/先不要」跳過）", is_user=False)
                return

        # Intercept update check requests
        user_input_lower = user_text.lower()
        if any(w in user_input_lower for w in ["update", "更新", "檢查更新", "升級", "check update"]):
            self.input_field.clear()
            self.add_message(user_text, is_user=True)
            self.add_message("正在檢查更新，請稍候...", is_user=False)

            self.send_btn.setEnabled(False)
            self.input_field.setEnabled(False)
            self.title_label.setText("Checking for updates...")

            self.update_worker = UpdateCheckWorker(self.config, BASE_DIR)
            self.update_worker.finished.connect(self.handle_update_check_finished)
            self.update_worker.start()
            return

        # Intercept file generation/export intents
        file_parsed = self.file_intent_parser.parse_intent(user_text)
        if file_parsed["intent"] != "none":
            self.input_field.clear()
            self.add_message(user_text, is_user=True)
            
            from file_handler import handle_file_intent
            file_reply = handle_file_intent(file_parsed, self.conversation, BASE_DIR)
            if file_reply:
                self.add_message(file_reply, is_user=False)
            return

        # Identify images in attachments first to check vision capability
        attached_images = []
        for file_path in self.attachments:
            suffix = file_path.suffix.lower()
            if suffix in ['.png', '.jpg', '.jpeg', '.webp', '.bmp']:
                attached_images.append(file_path)

        target_model = self.config["llm"]["model"]
        if attached_images:
            vision_model = self.ollama_client.find_first_vision_model()
            if vision_model:
                target_model = vision_model
                logging.info("Dynamic routing: routing to vision model %s", target_model)
            else:
                self.add_message(
                    "⚠️ 偵測到您上傳了圖片，但本地未安裝任何支援視覺的模型。\n"
                    "請先在終端機執行 `ollama run llava` 下載並安裝視覺模型以進行分析。",
                    is_user=False,
                    is_refusal=True
                )
                return

        # Capture text attachments and format preview logs
        attachment_text = ""
        attached_names = []
        for file_path in self.attachments:
            attached_names.append(file_path.name)
            suffix = file_path.suffix.lower()
            if suffix in ['.png', '.jpg', '.jpeg', '.webp', '.bmp']:
                attachment_text += f"\n\n[Attached Image: {file_path.name}]\n"
            else:
                try:
                    try:
                        content = file_path.read_text(encoding='utf-8')
                    except UnicodeDecodeError:
                        try:
                            content = file_path.read_text(encoding='utf-8-sig')
                        except UnicodeDecodeError:
                            content = file_path.read_text(encoding='latin-1')
                    lang = suffix[1:] if suffix.startswith('.') else ""
                    attachment_text += f"\n\n[Attached File: {file_path.name}]\n```{lang}\n{content}\n```\n"
                except Exception as e:
                    attachment_text += f"\n\n[Error reading attached file {file_path.name}: {str(e)}]\n"

        ui_display_text = user_text
        if attached_names:
            ui_display_text += "\n\n📎 " + ", ".join(attached_names)

        self.input_field.clear()
        self.add_message(ui_display_text, is_user=True)
        
        # Save image list to send via OllamaWorker, then clear the tray
        images_to_send = list(attached_images)
        self.clear_attachments()

        # --- Moral Evaluation ---
        result = self.evaluator.evaluate(user_text)
        
        if result.decision == Decision.REFUSE:
            self.add_message(f"I'm unable to help with that. ({result.rationale})", is_user=False, is_refusal=True)
            return

        if result.decision == Decision.ESCALATE_OR_PAUSE:
            self.add_message(f"⚠️ {result.rationale}", is_user=False, is_refusal=True)
            return

        # --- Alarm Intent Handling ---
        parsed = self.intent_parser.parse_intent(user_text)
        if parsed["intent"] != "none":
            def _gui_call_llm(prompt: str) -> str:
                return None

            _prompt_holder: list[str] = []

            def _capture_llm(prompt: str) -> str:
                _prompt_holder.append(prompt)
                return ""

            result_or_direct = handle_alarm_intent(parsed, self.alarm_manager, _capture_llm)

            if _prompt_holder:
                reply_prompt = _prompt_holder[0]
                self.send_btn.setEnabled(False)
                self.input_field.setEnabled(False)
                self.title_label.setText("Ann is typing...")
                messages = [
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": reply_prompt},
                ]
                self.worker = OllamaWorker(
                    self.config["llm"].get("base_url", "http://localhost:11434"),
                    self.config["llm"]["model"],
                    messages,
                )
                self.worker.finished.connect(self.handle_reply)
                self.worker.start()
            else:
                self.add_message(result_or_direct or "", is_user=False, is_refusal=True)
            return

        # Prepare message payload
        if result.decision == Decision.COMPLY_WITH_SAFEGUARDS:
            llm_message = (
                f"[Important: {result.rationale} Respond carefully and include "
                f"appropriate disclaimers.]\n\nUser: {user_text}{attachment_text}"
            )
        else:
            llm_message = user_text + attachment_text

        # --- News Intent Handling ---
        if self.news_manager.intent_parser.should_parse(user_text):
            self.send_btn.setEnabled(False)
            self.input_field.setEnabled(False)
            self.title_label.setText("Ann is fetching news...")

            self.news_worker = NewsWorker(self.news_manager, user_text)
            self.news_worker.finished.connect(
                lambda reply, err: self.handle_news_reply(reply, err, user_text, llm_message, target_model, images_to_send)
            )
            self.news_worker.start()
            return

        self.conversation.append({"role": "user", "content": llm_message})

        # Prepend system prompt
        messages_with_system = [
            {"role": "system", "content": SYSTEM_PROMPT},
            *self.conversation,
        ]

        # Call Ollama asynchronously via worker thread
        llm_base_url = self.config["llm"].get("base_url", "http://localhost:11434")

        self.send_btn.setEnabled(False)
        self.input_field.setEnabled(False)
        self.title_label.setText("Ann is typing...")

        self.worker = OllamaWorker(llm_base_url, target_model, messages_with_system, images_to_send)
        self.worker.finished.connect(self.handle_reply)
        self.worker.start()

    def handle_news_reply(self, reply: str, error: str, user_text: str, llm_message: str, target_model: str, images_to_send: list) -> None:
        if error == "not_news":
            # Fallback to standard Ollama flow
            self.conversation.append({"role": "user", "content": llm_message})
            messages_with_system = [
                {"role": "system", "content": SYSTEM_PROMPT},
                *self.conversation,
            ]
            llm_base_url = self.config["llm"].get("base_url", "http://localhost:11434")
            
            # Start normal Ollama worker
            self.worker = OllamaWorker(llm_base_url, target_model, messages_with_system, images_to_send)
            self.worker.finished.connect(self.handle_reply)
            self.worker.start()
        else:
            # Re-enable inputs
            self.send_btn.setEnabled(True)
            self.input_field.setEnabled(True)
            self.title_label.setText("Ann")

            if error:
                self.add_message(f"獲取新聞時發生錯誤：{error}", is_user=False, is_refusal=True)
            else:
                self.add_message(reply, is_user=False)
                # Save to conversation memory (use clean user_text and reply)
                self.conversation.append({"role": "user", "content": user_text})
                self.conversation.append({"role": "assistant", "content": reply})

    def handle_reply(self, reply: str, error: str) -> None:
        self.send_btn.setEnabled(True)
        self.input_field.setEnabled(True)
        self.title_label.setText("Ann")

        if error:
            self.add_message(f"(LLM error — is Ollama running? {error})", is_user=False, is_refusal=True)
            if self.conversation:
                self.conversation.pop()
            return

        if "[EXIT]" in reply:
            clean_reply = reply.replace("[EXIT]", "").strip()
            self.conversation.append({"role": "assistant", "content": clean_reply})
            self.add_message(clean_reply, is_user=False)
            
            # Disable GUI controls
            self.send_btn.setEnabled(False)
            self.input_field.setEnabled(False)
            self.title_label.setText("Goodbye...")
            
            # Exit program after 1.5 seconds delay so user can read goodbye
            QTimer.singleShot(1500, QApplication.quit)
        elif "[RESTART]" in reply:
            clean_reply = reply.replace("[RESTART]", "").strip()
            self.conversation.append({"role": "assistant", "content": clean_reply})
            self.add_message(clean_reply, is_user=False)
            
            # Disable GUI controls
            self.send_btn.setEnabled(False)
            self.input_field.setEnabled(False)
            self.title_label.setText("Restarting...")
            
            # Exit program with code 3 after 1.5 seconds delay
            QTimer.singleShot(1500, lambda: QApplication.exit(EXIT_RESTART))
        elif "[UPDATE]" in reply:
            clean_reply = reply.replace("[UPDATE]", "").strip()
            self.conversation.append({"role": "assistant", "content": clean_reply})
            self.add_message(clean_reply, is_user=False)
            
            # Disable GUI controls
            self.send_btn.setEnabled(False)
            self.input_field.setEnabled(False)
            self.title_label.setText("Updating...")
            
            # Exit program with code 42 after 1.5 seconds delay
            QTimer.singleShot(1500, lambda: QApplication.exit(EXIT_UPDATE))
        else:
            self.conversation.append({"role": "assistant", "content": reply})
            self.add_message(reply, is_user=False)
            self.input_field.setFocus()

    def handle_update_check_finished(self, new_version: str, error: str) -> None:
        self.send_btn.setEnabled(True)
        self.input_field.setEnabled(True)
        self.title_label.setText("Ann")

        if error:
            self.add_message(f"(檢查更新時發生錯誤：{error})", is_user=False, is_refusal=True)
            return

        if new_version:
            self.awaiting_update_confirm = True
            self.pending_version = new_version
            self.add_message(f"偵測到新版本 {new_version}。請問您現在要更新嗎？[y/n]", is_user=False)
        else:
            self.add_message("您目前已是最新版本，不需要更新。", is_user=False)
        self.input_field.setFocus()


class FloatingBubble(QWidget):
    """Draggable Floating Bubble (State 1 of Scheme B)."""
    def __init__(self, config: dict, evaluator: MoralEvaluator, alarm_manager, alarm_trigger, alarm_scheduler, intent_parser, new_tag: str = None):
        super().__init__()
        self.config = config
        self.evaluator = evaluator
        self.alarm_manager = alarm_manager
        self.alarm_trigger = alarm_trigger
        self.alarm_scheduler = alarm_scheduler
        self.intent_parser = intent_parser
        self.active_triggered_alarms = []
        self.drag_position = QPoint()
        self.click_start_pos = QPoint()
        self.drag_active = False
        self.setAcceptDrops(True)

        # Frameless, stays on top, tool window (no taskbar icon)
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint | Qt.WindowType.Tool)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.resize(70, 70)

        # Label inside bubble
        self.label = QLabel("Ann", self)
        self.label.setGeometry(0, 0, 70, 70)
        self.label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.label.setStyleSheet(
            "color: white; font-size: 14px; font-weight: bold; font-family: 'Segoe UI', Arial;"
        )

        # Initialize Chat Window
        self.chat_window = ChatWindow(self.config, self.evaluator, self, self.alarm_manager, self.alarm_trigger, self.alarm_scheduler, self.intent_parser, new_tag)
        self.chat_window.closed_to_bubble.connect(self.collapse_from_chat)

        # Position bubble in the bottom right corner initially
        screen = QApplication.primaryScreen().availableGeometry()
        self.move(screen.right() - 100, screen.bottom() - 100)

        # Start GUI Scheduler
        self.alarm_scheduler.start_gui_scheduler(self, self.on_alarm_triggered)

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        alarm_active = self.property("alarm_active")

        # Draw bubble circle gradient
        painter.setPen(Qt.PenStyle.NoPen)
        grad = QLinearGradient(0, 0, 0, self.height())
        if alarm_active:
            grad.setColorAt(0, QColor(63, 55, 14))  # Dark yellow
            grad.setColorAt(1, QColor(30, 25, 5))
        elif self.drag_active:
            grad.setColorAt(0, QColor(34, 84, 61))  # Dark green
            grad.setColorAt(1, QColor(20, 50, 35))
        else:
            grad.setColorAt(0, QColor(45, 55, 72))  # Slate Gray
            grad.setColorAt(1, QColor(26, 32, 44))
        painter.setBrush(QBrush(grad))
        
        pad = 2 if self.drag_active else 5
        painter.drawEllipse(pad, pad, self.width() - (pad * 2), self.height() - (pad * 2))

        # Glowing border
        if alarm_active:
            pen = QPen(QColor(246, 224, 94, 230), 3)  # Flashing yellow border
        elif self.drag_active:
            pen = QPen(QColor(72, 187, 120, 230), 3)  # Glowing green border for drop target
        else:
            pen = QPen(QColor(49, 130, 206, 200), 2)  # Blue glow border
        painter.setPen(pen)
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawEllipse(pad, pad, self.width() - (pad * 2), self.height() - (pad * 2))

    # Mouse Events
    def mousePressEvent(self, event) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            self.click_start_pos = event.globalPosition().toPoint()
            self.drag_position = self.click_start_pos - self.frameGeometry().topLeft()
            event.accept()

    def mouseMoveEvent(self, event) -> None:
        if event.buttons() == Qt.MouseButton.LeftButton:
            self.move(event.globalPosition().toPoint() - self.drag_position)
            event.accept()

    def mouseReleaseEvent(self, event) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            # Check if this was a click (no significant dragging)
            moved = (event.globalPosition().toPoint() - self.click_start_pos).manhattanLength()
            if moved < 5:
                if self.active_triggered_alarms:
                    self.dismiss_alarm()
                else:
                    self.expand_to_chat()
            event.accept()

    def expand_to_chat(self) -> None:
        """Morph/Expand from bubble to chat window."""
        if self.active_triggered_alarms:
            self.alarm_trigger.stop_visual_effects()
            self.alarm_trigger.start_visual_effects(self.chat_window)
            self.chat_window.dismiss_btn.show()

        bubble_center = self.pos() + self.rect().center()
        
        chat_width, chat_height = 360, 500
        chat_x = bubble_center.x() - chat_width // 2
        chat_y = bubble_center.y() - chat_height // 2

        # Stay within screen boundaries
        screen = QApplication.primaryScreen().availableGeometry()
        chat_x = max(screen.left(), min(chat_x, screen.right() - chat_width))
        chat_y = max(screen.top(), min(chat_y, screen.bottom() - chat_height))

        self.chat_window.setGeometry(chat_x, chat_y, chat_width, chat_height)
        self.hide()
        self.chat_window.show()
        self.chat_window.input_field.setFocus()

    def collapse_from_chat(self, chat_center: QPoint) -> None:
        """Morph/Collapse from chat window back to bubble."""
        bubble_x = chat_center.x() - self.width() // 2
        bubble_y = chat_center.y() - self.height() // 2

        # Stay within screen boundaries
        screen = QApplication.primaryScreen().availableGeometry()
        bubble_x = max(screen.left(), min(bubble_x, screen.right() - self.width()))
        bubble_y = max(screen.top(), min(bubble_y, screen.bottom() - self.height()))

        self.move(bubble_x, bubble_y)
        self.show()

    def on_alarm_triggered(self, alarm) -> None:
        logging.info("Alarm triggered in GUI: %s", alarm.label)
        self.active_triggered_alarms.append(alarm)
        
        target = self.chat_window if self.chat_window.isVisible() else self
        self.alarm_trigger.start_trigger(target)
        self.chat_window.dismiss_btn.show()
        self.chat_window.add_message(f"⏰ [鬧鐘提醒] {alarm.label or '無備註'} 時間到了！", is_user=False)

    def dismiss_alarm(self) -> None:
        self.alarm_trigger.stop_trigger()
        self.active_triggered_alarms.clear()
        self.chat_window.dismiss_btn.hide()

    def dragEnterEvent(self, event) -> None:
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
            self.drag_active = True
            self.update()
            
    def dragLeaveEvent(self, event) -> None:
        self.drag_active = False
        self.update()
        
    def dropEvent(self, event) -> None:
        self.drag_active = False
        self.update()
        
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
            self.expand_to_chat()
            
            for url in event.mimeData().urls():
                file_path = Path(url.toLocalFile())
                if file_path.is_file():
                    suffix = file_path.suffix.lower()
                    allowed_text = ['.txt', '.md', '.py', '.js', '.json', '.csv', '.html', '.css', '.yaml', '.yml', '.ini', '.cfg', '.log', '.c', '.cpp', '.java', '.sh', '.ts', '.sql', '.toml', '.env', '.xml']
                    allowed_img = ['.png', '.jpg', '.jpeg', '.webp', '.bmp']
                    if suffix in allowed_text or suffix in allowed_img:
                        self.chat_window.add_attachment(file_path)
                    else:
                        logging.info("Dropped unsupported file format in bubble: %s", suffix)


def start_gui(config: dict, evaluator: MoralEvaluator, alarm_manager, alarm_trigger, alarm_scheduler, intent_parser, new_tag: str = None) -> None:
    """Launch the PyQt6 application loop."""
    app = QApplication(sys.argv)
    bubble = FloatingBubble(config, evaluator, alarm_manager, alarm_trigger, alarm_scheduler, intent_parser, new_tag)
    bubble.show()
    sys.exit(app.exec())
