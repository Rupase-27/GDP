# This connects the GUI, (potential) gamepad, and serial link together

import sys
import time
from pathlib import Path

from PyQt5.QtCore import QObject
from PyQt5.QtWidgets import QApplication

from controllerGUI import ControlMode, MainWindow
from gamepadControl import GamepadControl # Once we're sure we want this
from robotConnection import RobotConnection

ROTATE_ACTIONS = {"cw", "anti-cw"}

class MainApp(QObject):
    SPEED_STEP_INTERVAL = 0.01 # Interval for speed increase/decrease when using gamepad
    
    def __init__(self):
        super().__init__()
        self.ui = MainWindow()
        self.controls = self.ui.controls
        self.connection = RobotConnection(self)
        self.gamepad = GamepadControl()
        
        self.currentAction = None
        self.prevSpeed = 0.0
        
        # From UI to robot
        self.controls.driveCommand.connect(self.sendGo)
        self.controls.stopCommand.connect(self.sendStop)
        self.controls.modeChanged.connect(lambda mode:self.setMode())
        # self.controls.speedChanged.connect(self.speedChange)
        self.controls.startCommand.connect(self.startButton)
        
        # From gamepad to robot
        self.gamepad.drive.connect(self.handleGamepad)
        
        # From robot to UI
        self.connection.status.connect(self.ui.add_log)
        self.connection.messageReceived.connect(lambda msg:self.ui.add_log(f"Received: {msg}"))
        
        self.mode = self.controls.controlling.value
        
    # shutdown is not called yet
    def start(self):
        self.ui.show()
        self.connection.connect()
    
    def shutdown(self):
        self.sendStop()
        self.connection.disconnect()
    
    # Commands
    def sendGo(self, command):
        if command == "release":
            self.sendReturn()
            return
        # mode = self.controls.controlling.value
        if self.mode == ControlMode.CATHETER and command in ROTATE_ACTIONS:
            return # Stops catheter from rotating
        
        self.currentAction = command
        self.connection.move(self.mode, command, self.controls.speed)
        
    def sendStop(self):
        self.currentAction = None
        self.connection.stop()
            
    def sendReturn(self):
        self.connection.release()
        
    def speedChange(self, value):
        # if self.currentAction is not None:
        #     self.sendGo(self.currentAction)
        
        # self.connection.move(self.controls.controlling.value, "speed", value)
        self.connection.speedChange(value)
        
    def startButton(self):
        # self.connection.sendStart()
        self.connection.move(self.mode, "start", self.controls.speed)
        
    # Mode tracked in a variable now so not constantly calling thingy
    def setMode(self, mode):
        if mode == ControlMode.CATHETER or mode == ControlMode.GUIDEWIRE:
            self.mode = mode
        self.connection.sendModeChange(mode)
            
    # NOT SURE IF WORK YET dont bother testing either
    def handleGamepad(self, command, value):
        if command == "stop":
            self.sendStop()
        elif command == "speed":
            t = time.monotonic()
            if t - self.prevSpeed >= self.SPEED_STEP_INTERVAL:
                self.prevSpeed = t
                if value > 0:
                    newSpeed = min(self.controls.speed + 1, 20.0)
                else:
                    newSpeed = max(self.controls.speed - 1, 0.0)
                self.controls.slider.setValue(int(newSpeed))
        else:
            self.sendGo(command)
    
        
def main():
    app = QApplication(sys.argv)
    style = Path(__file__).parent / "style.qss"
    app.setStyleSheet(style.read_text())
    
    mainApp = MainApp()
    mainApp.start()
    sys.exit(app.exec_())
    
if __name__ == "__main__":
    main()