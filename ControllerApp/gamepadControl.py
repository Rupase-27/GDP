import os
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")

import pygame
from PyQt5.QtCore import QObject, pyqtSignal, QTimer
import sys
from PyQt5.QtWidgets import QApplication

class GamepadControl(QObject):
    drive = pyqtSignal(str, float)
    
    def __init__(self):
        super().__init__()
        pygame.init()
        pygame.joystick.init()
        self.joystick = None
        self.previous = "stop"
        
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.callGamepad)
        self.timer.start(50)
        
    def callGamepad(self):
        for event in pygame.event.get():
            if event.type == pygame.JOYDEVICEADDED and self.joystick is None:
                self.joystick = pygame.joystick.Joystick(event.device_index)
                # Send some sort of acknowledgement
                print(f"Gamepad connected: {self.joystick.get_name()}")
            elif event.type == pygame.JOYDEVICEREMOVED and self.joystick is not None:
                print(f"Gamepad disconnected: {self.joystick.get_name()}")
                self.joystick = None
                # self.drive.emit("stop", 0.0) probably here
            elif event.type == pygame.JOYBUTTONDOWN:
                print("Stop this!")
                # self.drive.emit("stop", 0.0) something like that
                
        if self.joystick is None:
            return

        ly = -self.joystick.get_axis(1) # Left stick vertical axis
        lx = self.joystick.get_axis(0) # Left stick horizontal axis
        ry = self.joystick.get_axis(4) # Right stick for speed control
        
        action, value = "stop", 0.0
        if (abs(ly) > 0.1 or abs(lx) > 0.1) and abs(ry) > 0.1:
            pass # Ignore if both sticks are moved at the same time
        elif abs(ly) > 0.1:
            print("Move forward if positive, backward if negative " + str(ly))
            action, value = ("forward" if ly > 0 else "back"), abs(ly)
        elif abs(lx) > 0.1:
            print("Rotate clockwise if positive, counterclockwise if negative " + str(lx))
            action, value = ("cw" if lx > 0 else "anti-cw"), abs(lx)
        elif abs(ry) > 0.1:
            print("Speed increase if positive, decrease if negative " + str(ry))
            action, value = "speed", ry
            
        if action != self.previous or action == "speed":
            self.drive.emit(action, value)
        self.previous = action
            
if __name__ == "__main__":
    app = QApplication(sys.argv)
    gamepad_control = GamepadControl()
    sys.exit(app.exec_())