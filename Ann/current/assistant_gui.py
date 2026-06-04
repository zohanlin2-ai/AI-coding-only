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
    from PyQt6.QtCore import Qt, QPoint, QPropertyAnimation, QEasingCurve, pyqtSignal, QObject, QThread, QTimer, QRectF
    from PyQt6.QtGui import QPainter, QColor, QLinearGradient, QPen, QBrush, QPixmap, QPainterPath
except ImportError:
    from PySide6.QtWidgets import (
        QApplication, QWidget, QVBoxLayout, QHBoxLayout, QLineEdit,
        QPushButton, QLabel, QScrollArea, QFrame, QSizePolicy, QDialog, QTextEdit, QFileDialog
    )
    from PySide6.QtCore import Qt, QPoint, QPropertyAnimation, QEasingCurve, Signal, QObject, QThread, QTimer, QRectF
    from PySide6.QtGui import QPainter, QColor, QLinearGradient, QPen, QBrush, QPixmap, QPainterPath
    # Map PySide6 Signal to pyqtSignal name
    pyqtSignal = Signal

# Imports from core modules
from alarm_handler import (
    detect_update_intent, UPDATE_CHECK_WORDS, parse_reply_marker,
    build_update_confirm_llm_message, UPDATE_CONFIRM_NO_REPLY, UPDATE_CONFIRM_UNCLEAR_REPLY,
)
from assistant import load_config, BASE_DIR, EXIT_UPDATE, EXIT_RESTART
from core_controller import CoreController, ControllerResult, handle_memory_command, SYSTEM_PROMPT
from file_handler import parse_markdown_blocks

# Set up logging for GUI
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] (GUI) %(message)s")

# Allowed file extensions for drag-and-drop (single source of truth for ChatWindow + FloatingBubble).
ALLOWED_TEXT_EXTENSIONS = [
    '.txt', '.md', '.py', '.js', '.json', '.csv', '.html', '.css',
    '.yaml', '.yml', '.ini', '.cfg', '.log', '.c', '.cpp', '.java',
    '.sh', '.ts', '.sql', '.toml', '.env', '.xml',
]
ALLOWED_IMAGE_EXTENSIONS = ['.png', '.jpg', '.jpeg', '.webp', '.bmp']


class ControllerWorker(QThread):
    """
    Worker thread that runs CoreController.post_message() without blocking the GUI.

    Emits:
        status_update(str) — fired before the blocking call starts so the GUI
            can show a context-specific status label (e.g. 'Ann is fetching news...').
        finished(ControllerResult) — fired when post_message() returns.
    """
    status_update = pyqtSignal(str)   # status key: 'typing' | 'fetching_news'
    finished = pyqtSignal(object)     # ControllerResult

    def __init__(
        self,
        controller: CoreController,
        user_text: str,
        attachment_text: str = "",
        images: list | None = None,
    ):
        super().__init__()
        self.controller = controller
        self.user_text = user_text
        self.attachment_text = attachment_text
        self.images = images or []

    def run(self) -> None:
        # Emit fine-grained status before blocking on Ollama
        if (
            self.controller.news_manager
            and self.controller.news_manager.intent_parser.should_parse(self.user_text)
        ):
            self.status_update.emit("fetching_news")
        else:
            self.status_update.emit("typing")

        result = self.controller.post_message(
            self.user_text, self.attachment_text, self.images
        )
        self.finished.emit(result)


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


import webbrowser

def elide_text(text: str, max_weight: int = 76) -> str:
    """Helper to truncate a title to a maximum weighted length (Chinese=2, English=1) with trailing ellipsis."""
    weight = 0
    elided = []
    for char in text:
        if ord(char) > 127:
            weight += 2
        else:
            weight += 1
            
        if weight > max_weight:
            return "".join(elided) + "..."
        elided.append(char)
    return text

class NewsCardWidget(QFrame):
    """
    Custom QFrame representing a single news article as an overlay card.
    Displays a background image (or gradient fallback), a bottom semi-transparent
    black gradient overlay, title, source, and publish time.
    Clicking the widget opens the article link in a web browser.
    """
    def __init__(self, article: dict, parent=None):
        super().__init__(parent)
        self.article = article
        self.link = article.get("link", "")
        self.title = article.get("title", "")
        self.source = article.get("source", "")
        self.published = article.get("published", "")
        self.local_image_path = article.get("local_image_path")

        # Set widget height and size policy
        self.setFixedHeight(120)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setMouseTracking(True)
        self.is_hovered = False

        # Set tooltip showing the full title
        self.setToolTip(self.title)

        # Load pixmap if local image path exists
        self.pixmap = None
        if self.local_image_path and Path(self.local_image_path).exists():
            self.pixmap = QPixmap(self.local_image_path)
            if self.pixmap.isNull():
                self.pixmap = None

        # Custom inner layout to position the text at the bottom
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 8, 12, 8)
        layout.setSpacing(2)
        layout.addStretch()

        # Title label: bold white text
        display_title = elide_text(self.title, 76)
        title_lbl = QLabel(display_title)
        title_lbl.setWordWrap(True)
        title_lbl.setStyleSheet(
            "QLabel { color: #FFFFFF; font-weight: bold; font-family: 'Segoe UI', Arial; "
            "font-size: 13px; background-color: transparent; border: none; padding: 0; }"
        )
        title_lbl.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
        layout.addWidget(title_lbl)

        # Source & Time row
        meta_text = f"{self.source} • {self.published}"
        meta_lbl = QLabel(meta_text)
        meta_lbl.setWordWrap(True)
        meta_lbl.setStyleSheet(
            "QLabel { color: #CBD5E0; font-family: 'Segoe UI', Arial; "
            "font-size: 10px; background-color: transparent; border: none; padding: 0; }"
        )
        meta_lbl.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
        layout.addWidget(meta_lbl)

    def enterEvent(self, event) -> None:
        self.is_hovered = True
        self.update()
        super().enterEvent(event)

    def leaveEvent(self, event) -> None:
        self.is_hovered = False
        self.update()
        super().leaveEvent(event)

    def mousePressEvent(self, event) -> None:
        if event.button() == Qt.MouseButton.LeftButton and self.link:
            webbrowser.open(self.link)
            event.accept()
        else:
            super().mousePressEvent(event)

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        rect = self.rect()
        radius = 12

        # 1. Draw background image or gradient fallback
        path = QPainterPath()
        path.addRoundedRect(QRectF(rect), radius, radius)
        painter.setClipPath(path)

        if self.pixmap:
            # Scale pixmap to cover the rect aspect-ratio correctly
            scaled_pixmap = self.pixmap.scaled(
                rect.size(),
                Qt.AspectRatioMode.KeepAspectRatioByExpanding,
                Qt.TransformationMode.SmoothTransformation
            )
            # Center the pixmap
            x = (rect.width() - scaled_pixmap.width()) // 2
            y = (rect.height() - scaled_pixmap.height()) // 2
            painter.drawPixmap(x, y, scaled_pixmap)
        else:
            # Solid dark gradient fallback (deep blue/grey gradient)
            grad = QLinearGradient(0, 0, 0, rect.height())
            grad.setColorAt(0, QColor(45, 55, 72))  # Slate Gray
            grad.setColorAt(1, QColor(26, 32, 44))
            painter.fillPath(path, QBrush(grad))

        # 2. Draw bottom semi-transparent overlay gradient for text readability
        overlay_grad = QLinearGradient(0, 0, 0, rect.height())
        overlay_grad.setColorAt(0, QColor(0, 0, 0, 0))          # transparent at top
        overlay_grad.setColorAt(0.5, QColor(0, 0, 0, 100))      # fade to dark
        overlay_grad.setColorAt(1, QColor(0, 0, 0, 220))        # almost solid black at bottom
        painter.fillPath(path, QBrush(overlay_grad))

        # 3. Draw hover outline / border
        painter.setClipping(False) # Disable clipping so border renders fully
        if self.is_hovered:
            border_pen = QPen(QColor(66, 153, 225, 230), 2)  # Glowing blue border
        else:
            border_pen = QPen(QColor(74, 85, 104, 150), 1)   # Subtle gray border
        painter.setPen(border_pen)
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawRoundedRect(QRectF(rect).adjusted(0.5, 0.5, -0.5, -0.5), radius, radius)


class MessageBubble(QFrame):
    """Custom styled chat message bubble."""
    def __init__(self, text: str, is_user: bool, is_refusal: bool = False, articles: list = None):
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
        if articles:
            import re
            lines = text.split("\n")
            cleaned_lines = []
            for line in lines:
                stripped = line.strip()
                if re.match(r"^\d+\.\s+\[", stripped) or stripped.startswith("來源：") or stripped.startswith("來源:"):
                    continue
                cleaned_lines.append(line)
            text = "\n".join(cleaned_lines)
            text = re.sub(r"\n\s*\n+", "\n\n", text).strip()

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

        # Render news card widgets if present
        if articles:
            cards_container = QWidget()
            cards_container.setStyleSheet("background-color: transparent; border: none;")
            cards_layout = QVBoxLayout(cards_container)
            cards_layout.setContentsMargins(0, 8, 0, 0)
            cards_layout.setSpacing(8)
            for art in articles:
                card = NewsCardWidget(art)
                cards_layout.addWidget(card)
            bubble_layout.addWidget(cards_container)

        if is_user:
            layout.addStretch()
            layout.addWidget(bubble)
        else:
            layout.addWidget(bubble)
            layout.addStretch()


class ChatWindow(QWidget):
    """Main Chat Window (State 2 of Scheme B)."""
    closed_to_bubble = pyqtSignal(QPoint)

    def __init__(self, config: dict, controller, bubble, alarm_manager, alarm_trigger, alarm_scheduler, new_tag: str = None):
        super().__init__()
        self.config = config
        self.controller = controller
        self.bubble = bubble
        self.alarm_manager = alarm_manager
        self.alarm_trigger = alarm_trigger
        self.alarm_scheduler = alarm_scheduler
        self.drag_position = QPoint()
        self.awaiting_update_confirm = False
        self.pending_version = None
        self.update_worker = None

        # 閒置自動縮回計時器（3 分鐘）
        self.inactivity_timer = QTimer(self)
        self.inactivity_timer.setSingleShot(True)
        self.inactivity_timer.setInterval(3 * 60 * 1000)  # 180,000 ms
        self.inactivity_timer.timeout.connect(self._on_inactivity_timeout)

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
        self.scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
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
                    if suffix in ALLOWED_TEXT_EXTENSIONS or suffix in ALLOWED_IMAGE_EXTENSIONS:
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

    def start_inactivity_timer(self) -> None:
        """啟動（或重置）3 分鐘閒置倒數計時器。"""
        self.inactivity_timer.start()

    def stop_inactivity_timer(self) -> None:
        """停止閒置計時器。"""
        self.inactivity_timer.stop()

    def _on_inactivity_timeout(self) -> None:
        """閒置計時器到期，自動切回 bubble 模式。"""
        logging.info("Inactivity timeout: auto-collapsing to bubble.")
        self.shrink_back()

    def extend_inactivity_if_alarm(self) -> None:
        """鬧鐘觸發時，若計時器剩餘時間不足 10 秒，補到 10 秒。"""
        if self.inactivity_timer.isActive():
            remaining = self.inactivity_timer.remainingTime()
            if remaining < 10_000:
                self.inactivity_timer.start(10_000)

    def shrink_back(self) -> None:
        """Collapse the chat window back into the floating bubble."""
        self.stop_inactivity_timer()
        # If alarm is active, transfer visual target back to bubble
        if self.bubble.active_triggered_alarms:
            self.alarm_trigger.stop_visual_effects()
            self.alarm_trigger.start_visual_effects(self.bubble)
            
        self.closed_to_bubble.emit(self.pos() + self.rect().center())
        self.hide()

    def dismiss_alarm(self) -> None:
        self.bubble.dismiss_alarm()
        self.start_inactivity_timer()

    def add_message(self, text: str, is_user: bool, is_refusal: bool = False, articles: list = None) -> None:
        """Add a bubble message to the chat view."""
        bubble = MessageBubble(text, is_user, is_refusal, articles)
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

        self.start_inactivity_timer()  # 對話更新，重置 3 分鐘倒數

        user_input_lower = user_text.lower().strip()

        # ---- /memory slash commands (fast, synchronous) -----------------
        if user_input_lower.startswith("/memory"):
            self.input_field.clear()
            self.add_message(user_text, is_user=True)
            reply = handle_memory_command(user_text, self.controller.memory_manager)
            self.add_message(reply, is_user=False)
            return

        # ---- System commands (fast, synchronous) ------------------------
        exit_cmds = {"exit", "close", "terminate", "close the window", "shut down", "再見", "關閉程式", "關閉"}
        if user_input_lower in exit_cmds:
            self.input_field.clear()
            self.add_message(user_text, is_user=True)
            self.send_btn.setEnabled(False)
            self.input_field.setEnabled(False)
            self.title_label.setText("Goodbye...")
            self.add_message("再見！有需要隨時找我。", is_user=False)
            QTimer.singleShot(1500, QApplication.quit)
            return

        restart_cmds = {"restart", "reboot", "重啟", "重新啟動"}
        if user_input_lower in restart_cmds:
            self.input_field.clear()
            self.add_message(user_text, is_user=True)
            self.send_btn.setEnabled(False)
            self.input_field.setEnabled(False)
            self.title_label.setText("Restarting...")
            self.add_message("好的，我現在重新啟動，稍後見！", is_user=False)
            QTimer.singleShot(1500, lambda: QApplication.exit(EXIT_RESTART))
            return

        # ---- Update confirmation flow ------------------------------------
        if self.awaiting_update_confirm:
            self.input_field.clear()
            self.add_message(user_text, is_user=True)
            intent = detect_update_intent(user_input_lower)
            if intent == "yes":
                llm_message = build_update_confirm_llm_message(self.pending_version, user_text)
                self.controller.conversation.append({"role": "user", "content": llm_message})
                self.awaiting_update_confirm = False
                self.pending_version = None
                messages_with_system = [
                    {"role": "system", "content": SYSTEM_PROMPT},
                    *self.controller.conversation,
                ]
                self.send_btn.setEnabled(False)
                self.input_field.setEnabled(False)
                self.title_label.setText("Ann is typing...")
                # Use ControllerWorker but intercept via a quick direct LLM call
                # (no routing needed for this confirmation message)
                try:
                    reply = self.controller.ollama_client.chat(
                        self.controller.llm_model, messages_with_system
                    )
                    clean = parse_reply_marker(reply)[0]
                    self.controller.conversation.append({"role": "assistant", "content": clean})
                    self.send_btn.setEnabled(True)
                    self.input_field.setEnabled(True)
                    self.title_label.setText("Ann")
                    self.add_message(clean, is_user=False)
                except Exception:
                    self.send_btn.setEnabled(True)
                    self.input_field.setEnabled(True)
                    self.title_label.setText("Ann")
                    self.add_message("好的，即將進行更新並重新啟動應用程式...", is_user=False)
                QTimer.singleShot(1500, lambda: QApplication.exit(EXIT_UPDATE))
                return
            elif intent == "no":
                self.awaiting_update_confirm = False
                self.pending_version = None
                self.add_message(UPDATE_CONFIRM_NO_REPLY, is_user=False)
            else:
                self.add_message(UPDATE_CONFIRM_UNCLEAR_REPLY, is_user=False)
            return

        # ---- On-demand update check -------------------------------------
        if any(w in user_input_lower for w in UPDATE_CHECK_WORDS):
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

        # ---- Collect attachments ----------------------------------------
        attached_images = [f for f in self.attachments if f.suffix.lower() in ALLOWED_IMAGE_EXTENSIONS]
        attachment_text = ""
        attached_names = []
        for file_path in self.attachments:
            attached_names.append(file_path.name)
            suffix = file_path.suffix.lower()
            if suffix in ALLOWED_IMAGE_EXTENSIONS:
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

        images_to_send = list(attached_images)
        self.clear_attachments()

        # ---- Dispatch to ControllerWorker (background thread) -----------
        self.send_btn.setEnabled(False)
        self.input_field.setEnabled(False)
        self.title_label.setText("Ann is typing...")

        self.worker = ControllerWorker(
            self.controller, user_text, attachment_text, images_to_send
        )
        self.worker.status_update.connect(self.on_status_update)
        self.worker.finished.connect(self.handle_controller_result)
        self.worker.start()

    def on_status_update(self, status: str) -> None:
        """Update title label based on status key emitted by ControllerWorker."""
        if status == "fetching_news":
            self.title_label.setText("Ann is fetching news...")
        else:
            self.title_label.setText("Ann is typing...")

    def handle_controller_result(self, result) -> None:
        """Handle the ControllerResult returned by ControllerWorker."""
        self.send_btn.setEnabled(True)
        self.input_field.setEnabled(True)
        self.title_label.setText("Ann")

        if result.error:
            self.add_message(f"(LLM error — is Ollama running? {result.error})", is_user=False, is_refusal=True)
        elif result.is_refusal:
            self.add_message(result.reply, is_user=False, is_refusal=True)
        else:
            if result.marker == "[EXIT]":
                self.add_message(result.reply, is_user=False)
                self.send_btn.setEnabled(False)
                self.input_field.setEnabled(False)
                self.title_label.setText("Goodbye...")
                QTimer.singleShot(1500, QApplication.quit)
                return
            elif result.marker == "[RESTART]":
                self.add_message(result.reply, is_user=False)
                self.send_btn.setEnabled(False)
                self.input_field.setEnabled(False)
                self.title_label.setText("Restarting...")
                QTimer.singleShot(1500, lambda: QApplication.exit(EXIT_RESTART))
                return
            elif result.marker == "[UPDATE]":
                self.add_message(result.reply, is_user=False)
                self.send_btn.setEnabled(False)
                self.input_field.setEnabled(False)
                self.title_label.setText("Updating...")
                QTimer.singleShot(1500, lambda: QApplication.exit(EXIT_UPDATE))
                return
            else:
                self.add_message(result.reply, is_user=False, articles=result.articles)

        if self.isVisible():
            self.input_field.setFocus()
            self.start_inactivity_timer()
        else:
            if not self.bubble.active_triggered_alarms:
                self.bubble.set_new_reply_pending(True)


    def handle_update_check_finished(self, new_version: str, error: str) -> None:
        self.send_btn.setEnabled(True)
        self.input_field.setEnabled(True)
        self.title_label.setText("Ann")

        if error:
            self.add_message(f"(檢查更新時發生錯誤：{error})", is_user=False, is_refusal=True)
        else:
            if new_version:
                self.awaiting_update_confirm = True
                self.pending_version = new_version
                self.add_message(f"偵測到新版本 {new_version}。請問您現在要更新嗎？[y/n]", is_user=False)
            else:
                self.add_message("您目前已是最新版本，不需要更新。", is_user=False)

        if self.isVisible():
            self.start_inactivity_timer()
            self.input_field.setFocus()
        else:
            if not self.bubble.active_triggered_alarms:
                self.bubble.set_new_reply_pending(True)


class FloatingBubble(QWidget):
    """Draggable Floating Bubble (State 1 of Scheme B)."""
    def __init__(self, config: dict, controller, alarm_manager, alarm_trigger, alarm_scheduler, new_tag: str = None):
        super().__init__()
        self.config = config
        self.controller = controller
        self.alarm_manager = alarm_manager
        self.alarm_trigger = alarm_trigger
        self.alarm_scheduler = alarm_scheduler
        self.active_triggered_alarms = []
        self.drag_position = QPoint()
        self.click_start_pos = QPoint()
        self.drag_active = False
        self.setAcceptDrops(True)

        # 粉紅燈狀態（有未讀 Ann 回覆）
        self.new_reply_pending = False
        self._pulse_alpha = 80          # 當前透明度（80~230 之間震盪）
        self._pulse_direction = 1       # 1=加深, -1=變淡

        self._pulse_timer = QTimer(self)
        self._pulse_timer.setInterval(30)          # ~33fps
        self._pulse_timer.timeout.connect(self._update_pulse)

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
        self.chat_window = ChatWindow(self.config, self.controller, self, self.alarm_manager, self.alarm_trigger, self.alarm_scheduler, new_tag)
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
        elif self.new_reply_pending:
            pen = QPen(QColor(236, 72, 153, self._pulse_alpha), 3)  # Pulsing pink border
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

    def set_new_reply_pending(self, state: bool) -> None:
        """設定粉紅燈狀態，並啟動/停止脈衝動畫。"""
        self.new_reply_pending = state
        if state:
            self._pulse_alpha = 80
            self._pulse_direction = 1
            self._pulse_timer.start()
        else:
            self._pulse_timer.stop()
        self.update()

    def _update_pulse(self) -> None:
        """更新粉紅燈的脈衝透明度。"""
        self._pulse_alpha += self._pulse_direction * 6
        if self._pulse_alpha >= 230:
            self._pulse_alpha = 230
            self._pulse_direction = -1
        elif self._pulse_alpha <= 80:
            self._pulse_alpha = 80
            self._pulse_direction = 1
        self.update()

    def expand_to_chat(self) -> None:
        """Morph/Expand from bubble to chat window."""
        self.set_new_reply_pending(False)
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
        self.chat_window.start_inactivity_timer()

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
        self.chat_window.extend_inactivity_if_alarm()
        
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
                    if suffix in ALLOWED_TEXT_EXTENSIONS or suffix in ALLOWED_IMAGE_EXTENSIONS:
                        self.chat_window.add_attachment(file_path)
                    else:
                        logging.info("Dropped unsupported file format in bubble: %s", suffix)


def start_gui(
    config: dict,
    controller,
    alarm_manager,
    alarm_trigger,
    alarm_scheduler,
    new_tag: str = None,
) -> None:
    """Launch the PyQt6 application loop."""
    app = QApplication(sys.argv)

    # Premium ToolTip styling matching dark mode
    app.setStyleSheet(
        "QToolTip { color: #ffffff; background-color: #2D3748; border: 1px solid #4A5568; "
        "border-radius: 6px; padding: 6px; font-family: 'Segoe UI', Arial; font-size: 12px; }"
    )

    bubble = FloatingBubble(config, controller, alarm_manager, alarm_trigger, alarm_scheduler, new_tag)
    bubble.show()
    sys.exit(app.exec())
