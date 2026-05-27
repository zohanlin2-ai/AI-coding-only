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
        QPushButton, QLabel, QScrollArea, QFrame, QSizePolicy
    )
    from PyQt6.QtCore import Qt, QPoint, QPropertyAnimation, QEasingCurve, pyqtSignal, QObject, QThread, QTimer
    from PyQt6.QtGui import QPainter, QColor, QLinearGradient, QPen, QBrush
except ImportError:
    from PySide6.QtWidgets import (
        QApplication, QWidget, QVBoxLayout, QHBoxLayout, QLineEdit,
        QPushButton, QLabel, QScrollArea, QFrame, QSizePolicy
    )
    from PySide6.QtCore import Qt, QPoint, QPropertyAnimation, QEasingCurve, Signal, QObject, QThread, QTimer
    from PySide6.QtGui import QPainter, QColor, QLinearGradient, QPen, QBrush
    # Map PySide6 Signal to pyqtSignal name
    pyqtSignal = Signal

# Import core elements from assistant.py and moral_evaluator.py
from assistant import load_config, call_ollama, SYSTEM_PROMPT, BASE_DIR, EXIT_UPDATE
from moral_evaluator import MoralEvaluator, Decision

# Set up logging for GUI
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] (GUI) %(message)s")


class OllamaWorker(QThread):
    """Worker thread to handle blocking Ollama requests without freezing the GUI."""
    finished = pyqtSignal(str, str)  # Emits (reply_text, error_message)

    def __init__(self, base_url: str, model: str, messages: list[dict]):
        super().__init__()
        self.base_url = base_url
        self.model = model
        self.messages = messages

    def run(self) -> None:
        try:
            reply = call_ollama(self.base_url, self.model, self.messages)
            self.finished.emit(reply, "")
        except Exception as e:
            self.finished.emit("", str(e))


class MessageBubble(QFrame):
    """Custom styled chat message bubble."""
    def __init__(self, text: str, is_user: bool, is_refusal: bool = False):
        super().__init__()
        layout = QHBoxLayout(self)
        layout.setContentsMargins(10, 5, 10, 5)

        self.label = QLabel(text)
        self.label.setWordWrap(True)
        self.label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)

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

        self.label.setStyleSheet(
            f"color: {text_color}; font-size: 13px; font-family: 'Segoe UI', Arial; "
            f"background-color: transparent; border: none; padding: 0px;"
        )

        bubble = QFrame()
        bubble.setStyleSheet(
            f"background-color: {bg_color}; border: 1px solid {border_color}; "
            f"border-radius: 12px; padding: 8px;"
        )
        bubble_layout = QVBoxLayout(bubble)
        bubble_layout.setContentsMargins(8, 8, 8, 8)
        bubble_layout.addWidget(self.label)

        if is_user:
            layout.addStretch()
            layout.addWidget(bubble)
        else:
            layout.addWidget(bubble)
            layout.addStretch()


class ChatWindow(QWidget):
    """Main Chat Window (State 2 of Scheme B)."""
    closed_to_bubble = pyqtSignal(QPoint)

    def __init__(self, config: dict, evaluator: MoralEvaluator, bubble, alarm_manager, alarm_trigger, alarm_scheduler, intent_parser):
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

        card_layout.addLayout(input_layout)

        # Welcome message
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

        if user_text.lower() == "update":
            QApplication.exit(EXIT_UPDATE)
            return

        self.input_field.clear()
        self.add_message(user_text, is_user=True)

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
            intent = parsed["intent"]
            reply_prompt = ""
            if intent == "set_alarm":
                time_str = parsed["time"]
                label = parsed["label"]
                repeat_pattern = parsed.get("repeat")
                if not time_str:
                    reply_prompt = "請告訴我您想設定鬧鐘的具體時間。"
                else:
                    try:
                        from datetime import datetime
                        dt = datetime.fromisoformat(time_str)
                        success, msg_or_list, _ = self.alarm_manager.add_alarm(dt, label, repeat_pattern)
                        if success:
                            repeat_msg = f" repeating '{repeat_pattern}'" if repeat_pattern else ""
                            reply_prompt = f"System instruction: The alarm was successfully set for {dt.strftime('%Y-%m-%d %H:%M')}{repeat_msg} with label '{label or '無'}'. Confirm this to the user in a friendly way."
                        else:
                            reply_prompt = (
                                f"System instruction: The user wants to set an alarm but the limit of 10 active alarms has been reached.\n"
                                f"Here is the list of active alarms:\n{msg_or_list}\n"
                                f"Please inform the user about the limit and present this list of current alarms with their IDs, asking which one they would like to delete to make room."
                            )
                    except Exception as ex:
                        self.add_message(f"設定鬧鐘時發生錯誤：{ex}", is_user=False, is_refusal=True)
                        return
            elif intent == "list_alarms":
                alarms = self.alarm_manager.get_alarms()
                if not alarms:
                    reply_prompt = "System instruction: Tell the user in a friendly way that they have no active alarms."
                else:
                    alarms_list = "\n".join(
                        f"- [ID: {a.id}] {a.datetime.strftime('%Y-%m-%d %H:%M:%S')} — {a.label or '無備註'}" +
                        (f" (重複: {a.repeat_pattern})" if a.repeat_pattern else "")
                        for a in alarms
                    )
                    reply_prompt = f"System instruction: Present the following active alarms list to the user in a friendly way:\n{alarms_list}"
            elif intent == "delete_alarm":
                alarm_id = parsed["alarm_id"]
                label = parsed["label"]
                target_alarm = parsed["target_alarm"]
                deleted = False
                if alarm_id:
                    deleted = self.alarm_manager.delete_alarm(alarm_id)
                elif target_alarm:
                    deleted = self.alarm_manager.delete_alarm_by_target(target_alarm)
                elif label:
                    deleted = self.alarm_manager.delete_alarm_by_label(label)
                
                if deleted:
                    reply_prompt = f"System instruction: The alarm (ID/label/target: {alarm_id or target_alarm or label}) has been successfully deleted. Confirm this to the user in a friendly way."
                else:
                    self.add_message(f"找不到符合條件的鬧鐘（ID: {alarm_id or '無'}, 標籤/時間: {target_alarm or label or '無'}），請確認後再試。", is_user=False, is_refusal=True)
                    return
            elif intent == "update_alarm":
                alarm_id = parsed["alarm_id"]
                target_alarm = parsed["target_alarm"]
                time_str = parsed["time"]
                if not time_str:
                    self.add_message("請告訴我您想將鬧鐘修改成什麼時間。", is_user=False, is_refusal=True)
                    return
                else:
                    try:
                        from datetime import datetime
                        dt = datetime.fromisoformat(time_str)
                        success, msg = self.alarm_manager.update_alarm(
                            alarm_id=alarm_id, 
                            target_alarm=target_alarm, 
                            new_datetime=dt
                        )
                        if success:
                            reply_prompt = f"System instruction: {msg} Confirm this successful update to the user in a friendly way."
                        else:
                            self.add_message(msg, is_user=False, is_refusal=True)
                            return
                    except Exception as ex:
                        self.add_message(f"修改鬧鐘時發生錯誤：{ex}", is_user=False, is_refusal=True)
                        return

            # Call Ollama Worker asynchronously for response generation
            self.send_btn.setEnabled(False)
            self.input_field.setEnabled(False)
            self.title_label.setText("Ann is typing...")
            
            messages = [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": reply_prompt}
            ]
            
            self.worker = OllamaWorker(
                self.config["llm"].get("base_url", "http://localhost:11434"),
                self.config["llm"]["model"],
                messages
            )
            self.worker.finished.connect(self.handle_reply)
            self.worker.start()
            return

        # Prepare message payload
        if result.decision == Decision.COMPLY_WITH_SAFEGUARDS:
            llm_message = (
                f"[Important: {result.rationale} Respond carefully and include "
                f"appropriate disclaimers.]\n\nUser: {user_text}"
            )
        else:
            llm_message = user_text

        self.conversation.append({"role": "user", "content": llm_message})

        # Prepend system prompt
        messages_with_system = [
            {"role": "system", "content": SYSTEM_PROMPT},
            *self.conversation,
        ]

        # Call Ollama asynchronously via worker thread
        llm_model = self.config["llm"]["model"]
        llm_base_url = self.config["llm"].get("base_url", "http://localhost:11434")

        self.send_btn.setEnabled(False)
        self.input_field.setEnabled(False)
        self.title_label.setText("Ann is typing...")

        self.worker = OllamaWorker(llm_base_url, llm_model, messages_with_system)
        self.worker.finished.connect(self.handle_reply)
        self.worker.start()

    def handle_reply(self, reply: str, error: str) -> None:
        self.send_btn.setEnabled(True)
        self.input_field.setEnabled(True)
        self.title_label.setText("Ann")

        if error:
            self.add_message(f"(LLM error — is Ollama running? {error})", is_user=False, is_refusal=True)
            if self.conversation:
                self.conversation.pop()
            return

        self.conversation.append({"role": "assistant", "content": reply})
        self.add_message(reply, is_user=False)
        self.input_field.setFocus()


class FloatingBubble(QWidget):
    """Draggable Floating Bubble (State 1 of Scheme B)."""
    def __init__(self, config: dict, evaluator: MoralEvaluator, alarm_manager, alarm_trigger, alarm_scheduler, intent_parser):
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
        self.chat_window = ChatWindow(self.config, self.evaluator, self, self.alarm_manager, self.alarm_trigger, self.alarm_scheduler, self.intent_parser)
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
        else:
            grad.setColorAt(0, QColor(45, 55, 72))  # Slate Gray
            grad.setColorAt(1, QColor(26, 32, 44))
        painter.setBrush(QBrush(grad))
        painter.drawEllipse(5, 5, self.width() - 10, self.height() - 10)

        # Glowing border
        if alarm_active:
            pen = QPen(QColor(246, 224, 94, 230), 3)  # Flashing yellow border
        else:
            pen = QPen(QColor(49, 130, 206, 200), 2)  # Blue glow border
        painter.setPen(pen)
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawEllipse(5, 5, self.width() - 10, self.height() - 10)

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


def start_gui(config: dict, evaluator: MoralEvaluator, alarm_manager, alarm_trigger, alarm_scheduler, intent_parser) -> None:
    """Launch the PyQt6 application loop."""
    app = QApplication(sys.argv)
    bubble = FloatingBubble(config, evaluator, alarm_manager, alarm_trigger, alarm_scheduler, intent_parser)
    bubble.show()
    sys.exit(app.exec())
