import sys
import os
import traceback
from pathlib import Path
from PySide6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout,
                               QHBoxLayout, QTextEdit, QPushButton, QLabel,
                               QStatusBar, QFrame, QCheckBox, QComboBox)
from PySide6.QtCore import Qt, QThread, Signal, QSize
from PySide6.QtGui import QPixmap, QFont, QCursor
from ai_engine import AIEngine, MODELS_CONFIG


class GenerationWorker(QThread):
    finished = Signal(str, str)
    error = Signal(str)
    progress = Signal(str)

    def __init__(self, engine: AIEngine, prompt: str, model_key: str, enable_safety: bool):
        super().__init__()
        self.engine = engine
        self.prompt = prompt
        self.model_key = model_key
        self.enable_safety = enable_safety

    def run(self):
        try:
            self.progress.emit(f"正在載入 {self.model_key} 並生成圖片...")
            filepath, translated = self.engine.generate(
                self.prompt,
                model_key=self.model_key,
                enable_safety_check=self.enable_safety
            )
            self.finished.emit(filepath, translated)
        except Exception as e:
            # Print full traceback to console for debugging
            traceback.print_exc()
            # Emit only the core human-readable message to UI
            self.error.emit(str(e).split("\n")[0])


class ClickableLabel(QLabel):
    """A QLabel that emits a clicked signal when pressed."""
    clicked = Signal()

    def mousePressEvent(self, event):
        if self.pixmap() and not self.pixmap().isNull():
            self.clicked.emit()
        super().mousePressEvent(event)


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Local AI Image Generator")
        self.resize(1000, 820)
        self.setMinimumSize(800, 700)

        self.engine = AIEngine()
        self._is_generating = False
        self._last_filepath: str | None = None

        self.init_ui()
        self.load_stylesheet()

    def init_ui(self):
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)
        layout.setContentsMargins(40, 40, 40, 40)
        layout.setSpacing(20)

        # ── Header ──────────────────────────────────────────────────
        self.title_label = QLabel("Local AI Image Generator")
        self.title_label.setObjectName("TitleLabel")
        layout.addWidget(self.title_label)

        self.subtitle_label = QLabel("描述您的想像，讓本地 AI 為您具現化。")
        self.subtitle_label.setObjectName("SubtitleLabel")
        layout.addWidget(self.subtitle_label)

        # ── Prompt Input ────────────────────────────────────────────
        self.prompt_input = QTextEdit()
        self.prompt_input.setPlaceholderText(
            "描述圖片風格、大小、儲存格式 "
            "(例如：森林中的紅頭髮小精靈, 寫實風格, 1024x1024, png)"
        )
        self.prompt_input.setFixedHeight(120)
        layout.addWidget(self.prompt_input)

        # ── Options Row (Model Selector + Safety Toggle) ─────────────
        options_layout = QHBoxLayout()
        options_layout.setSpacing(15)

        model_label = QLabel("AI 畫家模型：")
        model_label.setStyleSheet("color: #CCCCCC; font-weight: bold; font-size: 15px;")
        self.model_selector = QComboBox()
        self.model_selector.setCursor(Qt.PointingHandCursor)
        self.model_selector.addItems(list(MODELS_CONFIG.keys()))
        options_layout.addWidget(model_label)
        options_layout.addWidget(self.model_selector)

        options_layout.addSpacing(30)

        self.safety_checkbox = QCheckBox("啟用 NSFW 安全過濾機制")
        self.safety_checkbox.setCursor(Qt.PointingHandCursor)
        self.safety_checkbox.setChecked(False)
        options_layout.addWidget(self.safety_checkbox)
        options_layout.addStretch()
        layout.addLayout(options_layout)

        # ── Action Buttons Row ───────────────────────────────────────
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(12)

        self.gen_button = QPushButton("開始生成")
        self.gen_button.setObjectName("GenButton")
        self.gen_button.setCursor(Qt.PointingHandCursor)
        self.gen_button.clicked.connect(self.start_generation)
        btn_layout.addWidget(self.gen_button, stretch=1)

        self.open_folder_button = QPushButton("📂 開啟輸出資料夾")
        self.open_folder_button.setObjectName("OpenFolderButton")
        self.open_folder_button.setCursor(Qt.PointingHandCursor)
        self.open_folder_button.clicked.connect(self.open_output_folder)
        btn_layout.addWidget(self.open_folder_button, stretch=0)

        layout.addLayout(btn_layout)

        # ── Image Display Area ────────────────────────────────────────
        self.image_display = ClickableLabel()
        self.image_display.setObjectName("ImageDisplay")
        self.image_display.setAlignment(Qt.AlignCenter)
        self.image_display.setText("產出的圖片將顯示於此\n點擊圖片可在系統預覽中開啟原始解析度")
        self.image_display.setMinimumHeight(400)
        self.image_display.setCursor(Qt.ArrowCursor)
        self.image_display.clicked.connect(self.open_image_in_system_viewer)
        layout.addWidget(self.image_display, 1)

        # ── Status Bar ───────────────────────────────────────────────
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        device_info = self.engine.get_device_info()
        self.status_bar.showMessage(f"準備就緒 | {device_info}")

    def load_stylesheet(self):
        qss_path = Path(__file__).parent / "style.qss"
        try:
            self.setStyleSheet(qss_path.read_text(encoding="utf-8"))
        except Exception as e:
            print(f"Could not load stylesheet: {e}")

    # ── Generation ──────────────────────────────────────────────────

    def start_generation(self):
        if self._is_generating:
            return

        prompt = self.prompt_input.toPlainText().strip()
        if not prompt:
            self.status_bar.showMessage("請輸入描述內容！")
            return

        self._is_generating = True
        self._set_controls_enabled(False)
        self.gen_button.setText("生成中...")
        self.image_display.setText("正在構思中，請稍候...")

        model_key = self.model_selector.currentText()
        enable_safety = self.safety_checkbox.isChecked()

        # Release any previous worker before creating a new one
        if hasattr(self, "worker") and self.worker is not None:
            self.worker.deleteLater()
            self.worker = None

        self.worker = GenerationWorker(self.engine, prompt, model_key, enable_safety)
        self.worker.finished.connect(self.on_generation_finished)
        self.worker.error.connect(self.on_generation_error)
        self.worker.progress.connect(self.status_bar.showMessage)
        self.worker.start()

    def on_generation_finished(self, filepath: str, translated_prompt: str):
        self._is_generating = False
        self._last_filepath = filepath
        self._set_controls_enabled(True)
        self.gen_button.setText("開始生成")

        # Display generated image
        pixmap = QPixmap(filepath)
        scaled_pixmap = pixmap.scaled(
            self.image_display.size(),
            Qt.KeepAspectRatio,
            Qt.SmoothTransformation
        )
        self.image_display.setPixmap(scaled_pixmap)
        self.image_display.setCursor(Qt.PointingHandCursor)

        self.status_bar.showMessage(
            f"✅ 生成成功 | AI 提示詞: {translated_prompt} | 點擊圖片可放大預覽"
        )

    def on_generation_error(self, error_msg: str):
        self._is_generating = False
        self._set_controls_enabled(True)
        self.gen_button.setText("開始生成")

        # Keep the previous image — do NOT clear it on error
        # Only update the status bar with a concise, user-friendly message
        self.status_bar.showMessage(f"❌ 生成失敗：{error_msg}")

    # ── Helper Actions ───────────────────────────────────────────────

    def open_output_folder(self):
        """Opens the outputs directory in the system file explorer."""
        output_dir = Path(__file__).parent / "outputs"
        output_dir.mkdir(parents=True, exist_ok=True)
        os.startfile(str(output_dir))

    def open_image_in_system_viewer(self):
        """Opens the last generated image with the system default viewer."""
        if self._last_filepath and Path(self._last_filepath).exists():
            os.startfile(self._last_filepath)

    def _set_controls_enabled(self, enabled: bool):
        """Toggles interactive controls during generation."""
        self.gen_button.setEnabled(enabled)
        self.safety_checkbox.setEnabled(enabled)
        self.model_selector.setEnabled(enabled)
        self.open_folder_button.setEnabled(enabled)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    font = QFont("Segoe UI", 10)
    app.setFont(font)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())
