#
#
#
#
# This code acts as a bridge between the camera and the GUI, capturing frames from the camera, processing them to detect the guidewire and catheter, 
# and emitting signals to update the GUI with the annotated frames and tracking information.
# It open the camera, captures the frames, sensds the frames to the GuidewireCatheterTracker, 
# receives guidewire/catheter tip locations, sends the processed image to the GUI, and runs independently so the GUI doesnt freeze while the camera is running.
#
#
###########################################################################################################################################################################

import cv2
from PyQt5.QtCore import QThread, pyqtSignal
from PyQt5.QtGui import QImage
from device_tracker import GuidewireCatheterTracker

# Opens camera, has background worker thread and a communication with GUI
class CameraThread(QThread):
    frameReady = pyqtSignal(QImage)
    trackingUpdated = pyqtSignal(dict)
    cameraError = pyqtSignal(str)

    # Constructor for the CameraThread class, initializes camera parameters and the GuidewireCatheterTracker
    def __init__(self, camera_index=1, width=640, height=480, fps=100, parent=None):
        super().__init__(parent)
        self.camera_index = camera_index
        self.width = width
        self.height = height
        self.fps = fps
        # Each camera thread has its own instance of the GuidewireCatheterTracker to process frames independently
        self.tracker = GuidewireCatheterTracker(diff_thresh=35, catheter_kernel_size=9, entry_side="left")
        self._running = False
        self._calibrate_requested = False

    # Background recalibration called by GUI button
    def request_bg_calibration(self):
        self._calibrate_requested = True

    # Main loop of the thread, captures frames from the camera, processes them, and emits signals to update the GUI
    def run(self):
        cap = cv2.VideoCapture(self.camera_index, cv2.CAP_DSHOW)
        if not cap.isOpened():
            # Fallback to index 0 if external camera is the only camera
            cap = cv2.VideoCapture(0, cv2.CAP_DSHOW)
        if not cap.isOpened():
            self.cameraError.emit("Could not open Camera.")
            return

        # Sends MJEPG stream as it is much faster than raw images, and sets the camera properties for width, height, and FPS
        cap.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc(*"MJPG"))
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, self.width)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self.height)
        cap.set(cv2.CAP_PROP_FPS, self.fps)
        cap.set(cv2.CAP_PROP_AUTO_EXPOSURE, 0.25)
        cap.set(cv2.CAP_PROP_EXPOSURE, -6)

        # Main processing loop
        self._running = True
        while self._running:
            ret, frame = cap.read()
            if not ret:
                continue

            if self._calibrate_requested:
                self.tracker.capture_background(frame)
                self._calibrate_requested = False

            annotated, tips = self.tracker.process(frame)
            self.trackingUpdated.emit(tips)
            # Convert the annotated frame to QImage format for display in the GUI
            rgb = cv2.cvtColor(annotated, cv2.COLOR_BGR2RGB)
            h, w, ch = rgb.shape
            qt_img = QImage(rgb.data, w, h, ch * w, QImage.Format_RGB888).copy()
            # Sends the QImage to the GUI for display
            self.frameReady.emit(qt_img)

        cap.release()

    def stop(self):
        self._running = False
        self.wait()