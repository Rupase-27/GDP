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
    
from guidewirePanel import GuidewirePanel # Make this happen somewhere else later

from datetime import datetime # Same here for logging

# Used in left half of controller window
class ControlPanel(QWidget):
    # Commands that will be sent by the UI to be received in main 
    driveCommand = pyqtSignal(str)
    stopCommand = pyqtSignal()
    startCommand = pyqtSignal()
    modeChanged = pyqtSignal(object)
    speedChanged = pyqtSignal(int)
    
    controlling = ControlMode.GUIDEWIRE
    log_message = pyqtSignal(str) # Current message being sent to logs

    SPEED_PRESETS = {"0.005m/s": 5, "0.010m/s": 10, "0.019m/s": 19}

    def __init__(self, parent=None):
        super().__init__(parent)
        self.speed = 0  # Default speed

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

        self.toggle_button = QPushButton("Controlling: Guidewire")
        self.toggle_button.setCheckable(True)
        self.toggle_button.setMinimumSize(110, 70)
        self.toggle_button.clicked.connect(self.toggle)
        self.toggle_button.setEnabled(False)
        layout.addWidget(self.toggle_button)

        return box
    
    # Sets control mode and disables/enables rotation buttons
    def toggle(self):
        if self.toggle_button.isChecked():
            self.toggle_button.setText("Controlling: Catheter")
            self.controlling = ControlMode.CATHETER

            self.findChild(QPushButton, "anti-cw").setEnabled(False)
            self.findChild(QPushButton, "cw").setEnabled(False)
        else:
            self.toggle_button.setText("Controlling: Guidewire")
            self.controlling = ControlMode.GUIDEWIRE

            self.findChild(QPushButton, "anti-cw").setEnabled(True)
            self.findChild(QPushButton, "cw").setEnabled(True)
        self.modeChanged.emit(self.controlling)

    # Defines the control panel with buttons to control push pull and rotation
    def controlPanel(self):
        box = QGroupBox("Movement")
        self.grid = QGridLayout(box)

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
            
            btn.pressed.connect(lambda name=cmd: self.go(name))
            btn.released.connect(self.release)
            self.grid.addWidget(btn, row, col)
            btn.setEnabled(False) # Disabled until start button is pressed

        # Emergency stop button
        self.estop = QPushButton("STOP")
        self.estop.setMinimumSize(110, 70)
        self.estop.setStyleSheet("background:#c0392b; color:white; font-weight:bold;")
        self.estop.clicked.connect(self.stop)
        
        # Start button goes in place of estop before its pressed and then estop replaces it after pressed
        self.startbutton = QPushButton("START")
        self.startbutton.setMinimumSize(110, 70)
        self.startbutton.setStyleSheet("background:#27ae60; color:white; font-weight:bold;")
        self.startbutton.clicked.connect(self.startButton)
        self.grid.addWidget(self.startbutton, 1, 1) # Start put on ui not stop yet (pyqt5 is weird so this might not have done anything)
        return box
    
    def startButton(self):
        log_msg = f"Start button pressed"
        self.log_message.emit(log_msg) # Hacky solution for now but should work
        
        # Call robot stuff here
        self.startCommand.emit()
                
        # Make all buttons available to be pressed and then replace start button with estop
        self.findChild(QPushButton, "forward").setEnabled(True)
        self.findChild(QPushButton, "back").setEnabled(True)
        self.findChild(QPushButton, "cw").setEnabled(not self.toggle_button.isChecked())
        self.findChild(QPushButton, "anti-cw").setEnabled(not self.toggle_button.isChecked())
        self.toggle_button.setEnabled(True)
        # Replace start button with estop
        self.grid.removeWidget(self.startbutton)
        self.startbutton.hide()
        self.grid.addWidget(self.estop, 1, 1)
        self.estop.show()
        
        self.slider.setValue(0) # Oh yeah and speed will start at 0 of course
        # self.startCommand.emit() # DONT FORGET THIS AGAIN # I Also changed is and moved it somewhere else

    def go(self, name):
        print(f"Button pressed: {name}")
        log_msg = f"Starting movement: {name}, current speed {self.speed/1000:.3f}m/s" # CHANGE TO RADIANS??????
        self.log_message.emit(log_msg)
        
        # Call robot stuff here
        self.driveCommand.emit(name)

    def stop(self):
        # print("stop button pressed")
        log_msg = f"Stopping movement"
        self.log_message.emit(log_msg) # Hacky solution for now but should work
        
        # Call robot stuff here
        self.stopCommand.emit()
        
        # Disable all buttons and put the start button back in place of estop
        self.findChild(QPushButton, "forward").setEnabled(False)
        self.findChild(QPushButton, "back").setEnabled(False)
        self.findChild(QPushButton, "cw").setEnabled(False)
        self.findChild(QPushButton, "anti-cw").setEnabled(False)
        self.toggle_button.setEnabled(False)
        # Replace estop with start button
        self.grid.removeWidget(self.estop)
        self.estop.hide()
        self.grid.addWidget(self.startbutton, 1, 1)
        self.startbutton.show()
        
        self.slider.setValue(0) # Not needed but like...

    def release(self):
        log_msg = f"Releasing movement"
        self.log_message.emit(log_msg)
        
        # Call robot stuff here
        self.driveCommand.emit("release")

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
        # self.slider.sliderReleased.connect(lambda: self.speedChanged.emit(self.speed))
        self.presets.buttonClicked[int].connect(self.slider.setValue)
        self.slider.setValue(self.speed)
        self.set_speed(self.speed)
        return box

    # Sets the speed given value on the slider
    def set_speed(self, speed):
        self.speed = speed
        self.speed_label.setText(f"Speed: {(speed/1000):.3f}m/s / 0.020m/s")
        
        log_msg = f"Speed set to: {self.speed/1000:.3f}m/s"
        self.log_message.emit(log_msg) # Etc and stuff yeah
        
        self.speedChanged.emit(self.speed)
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
        self.resize(1650, 1050)

        central = QWidget()
        self.setCentralWidget(central)
        root = QHBoxLayout(central)

        # Left half
        left = QVBoxLayout()
        self.controls = ControlPanel()
        left.addWidget(self.controls, 1)

        # Right half panels
        right = QVBoxLayout()
        self.camera_panel = PlaceholderPanel("Camera")
        self.guidewire_state = PlaceholderPanel("Guidewire Shape")
        self.logs = QGroupBox("Log")
        log_lay = QVBoxLayout(self.logs)
        self.log = QTextEdit(readOnly=True)
        log_lay.addWidget(self.log)
        self.controls.log_message.connect(self.add_log)
        
        self.guidewire_state = GuidewirePanel() # This will also be somewhere else later

        right.addWidget(self.camera_panel, 2)
        right.addWidget(self.guidewire_state, 3)
        # right.addWidget(self.logs, 1)
        left.addWidget(self.logs, 1)
        
        root.addLayout(left, 1)
        root.addLayout(right, 1)
        
        
    def add_log(self, message: str):
        # stamp = datetime.now().strftime("%H:%M:%S")
        # self.log.append(f"[{stamp}] {message}") # With timestamp if wanted
        self.log.append(message)
        self.log.verticalScrollBar().setValue(self.log.verticalScrollBar().maximum())

# Now for just running on its own for testing
# Do not care if it's removed, shouldn't impact anything
if __name__ == "__main__":
    app = QApplication(sys.argv)
    stylePath = Path(__file__).parent / "style.qss"
    app.setStyleSheet(stylePath.read_text())
    win = MainWindow()
    win.show()
    sys.exit(app.exec_())