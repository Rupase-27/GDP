# Feel free to modify/tear up this code. Just wanted to put out a starting point.
# Code based on the PySerial library's getting started documentation - https://www.pyserial.com/docs/getting-started
import serial
import serial.tools.list_ports

# Can either write code for finding port (https://www.pyserial.com/docs/debugging-guide) or just check Device Manager -> Ports (COM & LPT)
def serial_send(portName, command, baudRate=115200, timeout=0):
    try:
        serialPort = serial.Serial(portName, baudRate, timeout=timeout)
        serialPort.write(command.encode())
    except serial.SerialException as error:
        print(f"Serial error: {error}")
        if "FileNotFoundError" in str(error):
            print("Specified port cannot be found. Check connection and port name.")
        if "PermissionError" in str(error):
            print("Permission denied. User lacks required permissions, or port already in use.")
    finally:
        if 'serialPort' in locals() and serialPort.is_open:
             serialPort.close()

# Only identifies the vendor
# Tested with a pi pico I have at home
def check_ports():
    # Vendors list - https://www.usb.org/developers -> Valid Vendor IDs
    vendors = {
        11914: "Raspberry Pi",
        1155: "STMicroelectronics (STM)",
        12346: "Espressif Incorporated (ESP)"
    }

    ports = serial.tools.list_ports.comports()
    if not ports:
        print("No devices detected.")
    else:
        for port in ports:
            vendor = vendors.get(port.vid, "Unknown device")  
            print(f"{port.device}: {vendor}")
