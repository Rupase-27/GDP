import sys
from pathlib import Path
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QHBoxLayout, QVBoxLayout, QGridLayout,
    QPushButton, QSlider, QLabel, QGroupBox, QButtonGroup, QTextEdit,
)
from enum import Enum
class ControlMode(Enum):
    GUIDEWIRE = "guidewire"
    CATHETER = "catheter"

# Used in left half of controller window
class ControlPanel(QWidget):
    controlling = ControlMode.GUIDEWIRE

    SPEED_PRESETS = {"0.005m/s": 5, "0.010m/s": 10, "0.019m/s": 19}

    def __init__(self, parent=None):
        super().__init__(parent)
        self.speed = 10  # Default speed

        layout = QVBoxLayout(self)
        # Layout going top to bottom
        layout.addWidget(self.speedControl())
        layout.addWidget(self.controlPanel())
        layout.addWidget(self.controlToggle())
        self.controlling = ControlMode.GUIDEWIRE
        layout.addStretch()
        
    # Button that toggles between guidewire and catheter
    def controlToggle(self):
        box = QGroupBox("Control Mode")
        layout = QVBoxLayout(box)

        self.toggle_button = QPushButton("Guidewire")
        self.toggle_button.setCheckable(True)
        self.toggle_button.setMinimumSize(110, 70)
        self.toggle_button.clicked.connect(self.toggle)
        layout.addWidget(self.toggle_button)

        return box
    
    # Sets control mode and disables/enables rotation buttons
    def toggle(self):
        if self.toggle_button.isChecked():
            self.toggle_button.setText("Catheter")
            self.controlling = ControlMode.CATHETER

            self.findChild(QPushButton, "anti-cw").setEnabled(False)
            self.findChild(QPushButton, "cw").setEnabled(False)
        else:
            self.toggle_button.setText("Guidewire")
            self.controlling = ControlMode.GUIDEWIRE

            self.findChild(QPushButton, "anti-cw").setEnabled(True)
            self.findChild(QPushButton, "cw").setEnabled(True)

    # Defines the control panel with buttons to control push pull and rotation
    def controlPanel(self):
        box = QGroupBox("Movement")
        grid = QGridLayout(box)

        # Define buttons to control movement
        buttons = {
            "forward":  ("Push ▲", 0, 1),
            "anti-cw":      ("⟲ Rotate Left", 1, 0),
            "cw":       ("Rotate Right ⟳", 1, 2),
            "back":     ("Pull ▼", 2, 1),
        }
        # Adds buttons to grid Layout
        for cmd, (text, row, col) in buttons.items():
            btn = QPushButton(text)
            btn.setMinimumSize(110, 70)
            btn.setObjectName(cmd)
            
            btn.pressed.connect(lambda name=cmd: self.start(name))
            btn.released.connect(self.stop)
            grid.addWidget(btn, row, col)

        # Emergency stop button
        estop = QPushButton("STOP")
        estop.setMinimumSize(110, 70)
        estop.setStyleSheet("background:#c0392b; color:white; font-weight:bold;")
        estop.clicked.connect(self.stop)
        grid.addWidget(estop, 1, 1)
        return box

    def start(self, name):
        print(f"start button pressed: {name}")
        if self.controlling == ControlMode.GUIDEWIRE:
            #print("guidewire go")
            print("")
        else:
            #print("catheter go")
            print("")
        # Call robot stuff here

    def stop(self):
        print("stop button pressed")
        if self.controlling == ControlMode.GUIDEWIRE:
            #print("guidewire stop")
            print("")
        else:
            #print("catheter stop")
            print("")
        # Call robot stuff here

    # Speed slider with buttons for presets
    def speedControl(self):
        box = QGroupBox("Speed")
        layout = QVBoxLayout(box)

        self.speed_label = QLabel()
        self.speed_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.speed_label)

        # Defining slider with range and interval given speeds from Paper
        self.slider = QSlider(Qt.Horizontal)
        self.slider.setRange(0, 20)
        self.slider.setTickPosition(QSlider.TicksBelow)
        self.slider.setTickInterval(1)
        self.slider.setPageStep(1)
        layout.addWidget(self.slider)

        # Adds buttons for each "preset" option, for convenience
        row = QHBoxLayout()
        self.presets = QButtonGroup(self)
        self.presets.setExclusive(True)
        for name, value in self.SPEED_PRESETS.items():
            b = QPushButton(name)
            b.setCheckable(True)
            self.presets.addButton(b, value)
            row.addWidget(b)
        layout.addLayout(row)

        # When slider is changed, updates speed and labels
        self.slider.valueChanged.connect(self.set_speed)
        self.presets.buttonClicked[int].connect(self.slider.setValue)
        self.slider.setValue(self.speed)
        self.set_speed(self.speed)
        return box

    # Sets the speed given value on the slider
    def set_speed(self, speed):
        self.speed = speed
        self.speed_label.setText(f"Speed: {(speed/1000):.3f}m/s / 0.020m/s")
        # Press the button if speed matches preset option
        btn = self.presets.button(speed)
        if btn:
            btn.setChecked(True)
        else:
            checked = self.presets.checkedButton()
            if checked:
                self.presets.setExclusive(False)
                checked.setChecked(False)
                self.presets.setExclusive(True)

# Placeholder for camera display, guidewire diagram, and logs / other info
class PlaceholderPanel(QGroupBox):
    def __init__(self, title, parent=None):
        super().__init__(title, parent)
        lay = QVBoxLayout(self)
        self.body = QLabel(f"{title} goes here")
        self.body.setAlignment(Qt.AlignCenter)
        self.body.setStyleSheet("color:gray;")
        lay.addWidget(self.body)

# The actual window that shows up when launched
class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Controller")
        self.resize(1100, 700)

        central = QWidget()
        self.setCentralWidget(central)
        root = QHBoxLayout(central)

        # Left half
        self.controls = ControlPanel()
        root.addWidget(self.controls, 1)

        # Right half panels
        right = QVBoxLayout()
        self.camera_panel = PlaceholderPanel("Camera")
        self.guidewire_state = PlaceholderPanel("Guidewire Shape")
        self.logs = QGroupBox("Log")
        log_lay = QVBoxLayout(self.logs)
        self.log = QTextEdit(readOnly=True)
        log_lay.addWidget(self.log)

        right.addWidget(self.camera_panel, 2)
        right.addWidget(self.guidewire_state, 1)
        right.addWidget(self.logs, 1)
        root.addLayout(right, 1)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    stylePath = Path(__file__).parent / "style.qss"
    app.setStyleSheet(stylePath.read_text())
    win = MainWindow()
    win.show()
    sys.exit(app.exec_())