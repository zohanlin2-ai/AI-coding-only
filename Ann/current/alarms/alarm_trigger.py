import logging
import threading
import time
from pathlib import Path

logger = logging.getLogger(__name__)

# Try to import pygame, but fail gracefully if not available
PYGAME_AVAILABLE = False
try:
    import pygame
    pygame.mixer.init()
    PYGAME_AVAILABLE = True
except Exception as e:
    logger.warning("pygame.mixer is not available or failed to initialize: %s. Sound will be disabled.", e)

# Import PyQt6 or PySide6 for GUI animations
GUI_AVAILABLE = False
try:
    from PyQt6.QtCore import QPoint, QPropertyAnimation, QSequentialAnimationGroup, QTimer, QParallelAnimationGroup
    GUI_AVAILABLE = True
except ImportError:
    try:
        from PySide6.QtCore import QPoint, QPropertyAnimation, QSequentialAnimationGroup, QTimer, QParallelAnimationGroup
        GUI_AVAILABLE = True
    except ImportError:
        GUI_AVAILABLE = False


class AlarmTrigger:
    def __init__(self, sound_path: str = None, volume: float = 0.8):
        self.sound_path = sound_path
        self.volume = volume
        self.sound_thread = None
        self.sound_stop_event = threading.Event()
        
        # GUI Animation objects
        self.shake_group = None
        self.flash_timer = None
        self.target_widget = None
        self.original_pos = None
        self.original_style = None
        self.flash_state = False

    def start_trigger(self, widget=None):
        """Starts both audio and visual alarm triggers."""
        logger.info("Triggering alarm...")
        self.play_sound()
        if widget and GUI_AVAILABLE:
            self.start_visual_effects(widget)

    def stop_trigger(self):
        """Stops all audio and visual triggers."""
        logger.info("Stopping alarm trigger.")
        self.stop_sound()
        self.stop_visual_effects()

    def play_sound(self):
        """Plays the alarm sound in a background loop with a 60-second timeout."""
        if not PYGAME_AVAILABLE:
            logger.warning("Sound skipped: pygame is not available.")
            return

        if not self.sound_path:
            logger.warning("Sound skipped: no sound path specified.")
            return

        sound_file = Path(self.sound_path)
        if not sound_file.exists():
            logger.error("Sound file not found: %s. Continuing with visual effect only.", sound_file)
            return

        self.sound_stop_event.clear()
        self.sound_thread = threading.Thread(target=self._run_sound_loop, args=(sound_file,), daemon=True)
        self.sound_thread.start()

    def _run_sound_loop(self, sound_file: Path):
        try:
            pygame.mixer.music.load(str(sound_file))
            pygame.mixer.music.set_volume(self.volume)
            pygame.mixer.music.play(-1) # Loop indefinitely
            
            # Wait for stop signal or 60 seconds timeout
            start_time = time.time()
            while not self.sound_stop_event.is_set():
                elapsed = time.time() - start_time
                if elapsed >= 60.0:
                    logger.info("Alarm sound timed out after 60 seconds.")
                    break
                time.sleep(0.1)
                
            pygame.mixer.music.stop()
        except Exception as e:
            logger.error("Error playing alarm sound: %s", e)

    def stop_sound(self):
        self.sound_stop_event.set()
        if self.sound_thread:
            self.sound_thread.join(timeout=1.0)
            self.sound_thread = None

    def start_visual_effects(self, widget):
        """Starts shake and flash animations on the target PyQt/PySide widget."""
        if not GUI_AVAILABLE or not widget:
            return

        self.target_widget = widget
        self.original_pos = widget.pos()
        self.original_style = widget.styleSheet()
        self.flash_state = False

        # 1. Create repeating Shake Animation
        self._setup_shake_animation(widget)
        self.shake_group.start()

        # 2. Setup background color flashing timer (every 300ms)
        self.flash_timer = QTimer(widget)
        self.flash_timer.timeout.connect(self._toggle_flash)
        self.flash_timer.start(300)

    def _setup_shake_animation(self, widget):
        # We build a sequential animation for one full shake cycle
        self.shake_group = QSequentialAnimationGroup(widget)
        
        # Shake offsets: left/right/decay (gentler shake)
        offsets = [6, -6, 4, -4, 2, -2, 1, -1, 0]
        
        for offset in offsets:
            anim = QPropertyAnimation(widget, b"pos")
            anim.setDuration(60) # 60ms per step (slower/gentler)
            anim.setStartValue(widget.pos())
            anim.setEndValue(self.original_pos + QPoint(offset, 0))
            self.shake_group.addAnimation(anim)
            
        # Connect finished signal to loop the shake animation if widget is still active
        self.shake_group.finished.connect(self._loop_shake)

    def _loop_shake(self):
        if self.target_widget and self.shake_group:
            # Re-read original pos in case widget was moved by user dragging
            # but keep it stable during active shake cycles
            self.shake_group.start()

    def _toggle_flash(self):
        if not self.target_widget:
            return
            
        self.flash_state = not self.flash_state
        
        # Let's inspect the type of widget to apply appropriate styling
        class_name = self.target_widget.__class__.__name__
        
        if class_name == "FloatingBubble":
            # For the bubble, we toggle a border glow property or repaint.
            # We can update a custom property or toggle a stylesheet.
            if self.flash_state:
                # Orange flashing glow style
                self.target_widget.setStyleSheet(
                    "QLabel { color: white; font-size: 14px; font-weight: bold; }"
                )
                # Let's set a flag on the bubble for paintEvent to draw orange glow
                self.target_widget.setProperty("alarm_active", True)
            else:
                self.target_widget.setStyleSheet(self.original_style)
                self.target_widget.setProperty("alarm_active", False)
            self.target_widget.style().unpolish(self.target_widget)
            self.target_widget.style().polish(self.target_widget)
            self.target_widget.update()
        else:
            # For ChatWindow or its card, we flash the background color of the card Frame
            # Find the card widget if target is ChatWindow
            card = getattr(self.target_widget, "card", self.target_widget)
            if self.flash_state:
                card.setStyleSheet(
                    "QFrame { background-color: #5F370E; border: 2px solid #ED8936; border-radius: 16px; }"
                )
            else:
                card.setStyleSheet(
                    "QFrame { background-color: #1A1D24; border: 1px solid #2D3748; border-radius: 16px; }"
                )

    def stop_visual_effects(self):
        if self.shake_group:
            self.shake_group.stop()
            self.shake_group = None
            
        if self.flash_timer:
            self.flash_timer.stop()
            self.flash_timer = None
            
        if self.target_widget:
            # Restore original state
            self.target_widget.setStyleSheet(self.original_style)
            self.target_widget.setProperty("alarm_active", False)
            if hasattr(self.target_widget, "card"):
                self.target_widget.card.setStyleSheet(
                    "QFrame { background-color: #1A1D24; border: 1px solid #2D3748; border-radius: 16px; }"
                )
            self.target_widget.move(self.original_pos)
            self.target_widget.style().unpolish(self.target_widget)
            self.target_widget.style().polish(self.target_widget)
            self.target_widget.update()
            
            self.target_widget = None
