# Feel free to modify/tear up this code. Just wanted to put out a starting point.
# Code based on the PySerial library's getting started documentation - https://www.pyserial.com/docs/getting-started
import serial

# Can either write code for finding port (https://www.pyserial.com/docs/debugging-guide) or just check Device Manager -> Ports (COM & LPT)
def serial_send(portName, command, baudRate=115200, timeout=0):
    try:
        serialPort = serial.Serial(portName, baudRate, timeout=timeout)
        serialPort.write(command.encode())
    except serial.SerialException as e:
        print(f"Serial error: {e}")
        if "FileNotFoundError" in str(e):
            print("Specified port cannot be found. Check connection and port name.")
        if "PermissionError" in str(e):
            print("Permission denied. User lacks required permissions, or port already in use.")
    finally:
        if 'serialPort' in locals() and serialPort.is_open:
             serialPort.close()