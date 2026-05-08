import sys
import cv2
import os
import numpy as np
from PySide6.QtWidgets import (QApplication, QMainWindow, QPushButton, QVBoxLayout, 
                             QHBoxLayout, QLabel, QWidget, QFrame)
from PySide6.QtCore import Qt, QThread, Signal
from PySide6.QtGui import QImage, QPixmap

class VideoThread(QThread):
    change_pixmap_signal = Signal(np.ndarray)

    def __init__(self):
        super().__init__()
        self._run_flag = True
        self.cap = None

    def run(self):
        # Initialize camera
        self.cap = cv2.VideoCapture(0)
        while self._run_flag:
            ret, cv_img = self.cap.read()
            if ret:
                # Flip image horizontally for mirror effect
                cv_img = cv2.flip(cv_img, 1)
                self.change_pixmap_signal.emit(cv_img)
        
        if self.cap:
            self.cap.release()

    def stop(self):
        self._run_flag = False
        self.wait()

class FaceDetectionUI(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Real-time DNN Face & Eye Detection")
        self.setFixedSize(900, 750)

        # State control
        self.is_camera_on = False
        self.is_detection_on = False
        
        # Load DNN Face Model
        model_path = "models/res10_300x300_ssd_iter_140000.caffemodel"
        proto_path = "models/deploy.prototxt"
        
        self.net = None
        if os.path.exists(model_path) and os.path.exists(proto_path):
            self.net = cv2.dnn.readNetFromCaffe(proto_path, model_path)
        
        # Load Eye Cascade (Haar Cascade is still okay for eyes within the DNN face ROI)
        self.eye_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_eye.xml')
        
        self.init_ui()

    def init_ui(self):
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)

        # Title
        title = QLabel("Robust DNN Face Detection Management")
        title.setAlignment(Qt.AlignCenter)
        title.setStyleSheet("font-size: 22px; font-weight: bold; margin: 10px;")
        main_layout.addWidget(title)

        # Video Display Area (800x600)
        self.video_container = QFrame()
        self.video_container.setFixedSize(800, 600)
        self.video_container.setStyleSheet("background-color: #1a1a1a; border: 2px solid #333; border-radius: 5px;")
        
        self.video_label = QLabel(self.video_container)
        self.video_label.setFixedSize(800, 600)
        self.video_label.setAlignment(Qt.AlignCenter)
        self.video_label.setText("Camera is OFF")
        self.video_label.setStyleSheet("color: #777; font-size: 16px;")
        
        video_inner_layout = QVBoxLayout(self.video_container)
        video_inner_layout.addWidget(self.video_label)
        main_layout.addWidget(self.video_container, alignment=Qt.AlignCenter)

        # Button Layout
        btn_layout = QHBoxLayout()
        
        self.btn_camera = QPushButton("Start Camera Stream")
        self.btn_camera.setFixedHeight(50)
        self.btn_camera.setStyleSheet("background-color: #2196F3; color: white; border-radius: 4px; font-weight: bold;")
        self.btn_camera.clicked.connect(self.toggle_camera)
        
        self.btn_detect = QPushButton("Enable Detection")
        self.btn_detect.setFixedHeight(50)
        self.btn_detect.setEnabled(False)
        self.btn_detect.setStyleSheet("background-color: #e0e0e0; color: #888; border-radius: 4px; font-weight: bold;")
        self.btn_detect.clicked.connect(self.toggle_detection)
        
        btn_layout.addWidget(self.btn_camera)
        btn_layout.addWidget(self.btn_detect)
        main_layout.addLayout(btn_layout)

        # Status Bar
        self.status_label = QLabel("Status: Ready")
        self.status_label.setStyleSheet("padding: 5px; color: #555;")
        main_layout.addWidget(self.status_label)

    def toggle_camera(self):
        if not self.is_camera_on:
            self.thread = VideoThread()
            self.thread.change_pixmap_signal.connect(self.update_frame)
            self.thread.start()
            
            self.btn_camera.setText("Stop Camera Stream")
            self.btn_camera.setStyleSheet("background-color: #f44336; color: white; border-radius: 4px; font-weight: bold;")
            self.btn_detect.setEnabled(True)
            self.btn_detect.setStyleSheet("background-color: #4CAF50; color: white; border-radius: 4px; font-weight: bold;")
            self.is_camera_on = True
            self.status_label.setText("Status: Streaming...")
        else:
            self.thread.stop()
            self.is_camera_on = False
            self.is_detection_on = False
            self.video_label.clear()
            self.video_label.setText("Camera is OFF")
            self.btn_camera.setText("Start Camera Stream")
            self.btn_camera.setStyleSheet("background-color: #2196F3; color: white; border-radius: 4px; font-weight: bold;")
            self.btn_detect.setText("Enable Detection")
            self.btn_detect.setEnabled(False)
            self.btn_detect.setStyleSheet("background-color: #e0e0e0; color: #888; border-radius: 4px; font-weight: bold;")
            self.status_label.setText("Status: Camera Closed")

    def toggle_detection(self):
        if self.net is None:
            self.status_label.setText("Error: Model files missing in 'models/' folder.")
            return

        if not self.is_detection_on:
            self.is_detection_on = True
            self.btn_detect.setText("Disable Detection")
            self.btn_detect.setStyleSheet("background-color: #FF9800; color: white; border-radius: 4px; font-weight: bold;")
            self.status_label.setText("Status: DNN Detection Active")
        else:
            self.is_detection_on = False
            self.btn_detect.setText("Enable Detection")
            self.btn_detect.setStyleSheet("background-color: #4CAF50; color: white; border-radius: 4px; font-weight: bold;")
            self.status_label.setText("Status: Detection Disabled")

    def update_frame(self, cv_img):
        if self.is_detection_on and self.net is not None:
            (h, w) = cv_img.shape[:2]
            # Construct a blob from the image
            blob = cv2.dnn.blobFromImage(cv2.resize(cv_img, (300, 300)), 1.0, (300, 300), (104.0, 177.0, 123.0))
            
            self.net.setInput(blob)
            detections = self.net.forward()

            # Loop over the detections
            for i in range(0, detections.shape[2]):
                confidence = detections[0, 0, i, 2]

                # Filter out weak detections
                if confidence > 0.5:
                    # Compute coordinates
                    box = detections[0, 0, i, 3:7] * np.array([w, h, w, h])
                    (startX, startY, endX, endY) = box.astype("int")

                    # Draw Face box
                    cv2.rectangle(cv_img, (startX, startY), (endX, endY), (0, 255, 0), 2)
                    text = f"Face: {confidence * 100:.2f}%"
                    cv2.putText(cv_img, text, (startX, startY - 10),
                                cv2.FONT_HERSHEY_SIMPLEX, 0.45, (0, 255, 0), 2)

                    # Eye detection within Face ROI (Upper 60%)
                    face_h = endY - startY
                    face_w = endX - startX
                    if face_h > 0 and face_w > 0:
                        eye_search_h = int(face_h * 0.6)
                        roi_gray = cv2.cvtColor(cv_img[startY:startY+eye_search_h, startX:endX], cv2.COLOR_BGR2GRAY)
                        eyes = self.eye_cascade.detectMultiScale(roi_gray, 1.1, 15)
                        
                        for (ex, ey, ew, eh) in eyes:
                            cv2.rectangle(cv_img[startY:startY+eye_search_h, startX:endX], 
                                         (ex, ey), (ex+ew, ey+eh), (255, 0, 0), 2)

        # Convert to Qt format and scale
        qt_img = self.cv_to_qt(cv_img)
        self.video_label.setPixmap(qt_img)

    def cv_to_qt(self, cv_img):
        rgb_image = cv2.cvtColor(cv_img, cv2.COLOR_BGR2RGB)
        h, w, ch = rgb_image.shape
        bytes_per_line = ch * w
        q_img = QImage(rgb_image.data, w, h, bytes_per_line, QImage.Format_RGB888)
        return QPixmap.fromImage(q_img).scaled(800, 600, Qt.KeepAspectRatio)

    def closeEvent(self, event):
        if self.is_camera_on:
            self.thread.stop()
        event.accept()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    ui = FaceDetectionUI()
    ui.show()
    sys.exit(app.exec())
