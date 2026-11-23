import serial
from PyQt5.QtCore import QObject, QTimer, pyqtSignal

import serial_interface as si
from controllerGUI import ControlMode

class RobotConnection(QObject):
    status = pyqtSignal(str)
    messageReceived = pyqtSignal(str)
    
    DEVICE_CODES = {ControlMode.GUIDEWIRE: "guidewire", ControlMode.CATHETER: "catheter", "speed": b'speed'}
    COMMANDS = { "forward": "PUSH", "back": "PULL", "cw": "ROTATE-CW", "anti-cw": "ROTATE-ACW", "stop": "STOP", "release": "RELEASE", "start": "START" }
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.port = None
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.poll)
        self.buffer = ""
        
    @property
    def connected(self):
        return self.port is not None and self.port.is_open
    
    # Connection to the robot via serial port
    def connect(self, portName = None):
        portName = portName or si.auto_locate()
        if portName is None:
            self.status.emit("No device found.")
            return False
        self.port = si.initialise_port(portName)
        if self.port is None:
            self.status.emit("Failed to connect to device.")
            return False
        self.timer.start(20)
        self.status.emit(f"Connected to device at {portName}.")
        return True

    def disconnect(self):
        if self.connected:
            self.timer.stop()
            self.port.close()
            self.stop()
            self.status.emit("Disconnected from device.")
        self.port = None
        
    # Handle commands from the GUI
    def move(self, mode, command, speed_mm_s):
        mode = ControlMode(mode)
        line = f"{self.DEVICE_CODES[mode]} {self.COMMANDS[command]} {int(speed_mm_s)}"
        self.send(line)
        
    def stop(self):
        self.send("STOP")
        
    def release(self):
        self.send("release")
        
    def speedChange(self, value):
        self.send(f"Speed: {value}")
        
    def sendModeChange(self, mode):
        self.send(self.DEVICE_CODES[mode])
        
    # def sendStart(self):
        # self.send("START")
        # self.move()
    
    # Send a command to the robot
    def send(self, line):
        if self.connected:
            si.serial_send(self.port, line)
            self.status.emit(f"Sent: {line}") # REMOVE ONE KNOW IT WORKS :)
        else:
            self.status.emit("Failed to send message")
    
    # Poll the serial port for incoming messages
    def poll(self):
        try:
            if not self.connected or not self.port.in_waiting:
                return
            chunk = si.serial_receive(self.port)
        except (serial.SerialException, OSError) as e:
            self.status.emit(f"Serial error: {e}")
            self.timer.stop()
            self.port = None
            return
        if not chunk:
            return
        # Reads may end mid-line, so buffer...
        self.buffer += chunk
        *lines, self.buffer = self.buffer.split("\n")
        for line in lines:
            if line:
                self.messageReceived.emit(line)