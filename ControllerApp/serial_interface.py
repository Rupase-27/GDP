# Code relies on the PySerial library - https://pypi.org/project/pyserial/
# Feel free to message me about/modify this code
# Tested all functions with a pi pico I have at home
#
# check_ports() - Lists all connected serial devices by vendor
#
# auto_locate() - Attempts to locate a connected STM or ESP device and returns its port - I can improve this if needed
#
# initialise_port(portName, baudRate=115200, timeout=0) - Initialises a serial port, returns the serial object
# portName - The name of the port to initialise (e.g. COM3) (the thing returned by auto_locate())
# baudRate - Has to match STM (which uses 115200 at time of writing)
# timeout - Blocking time to wait for communication (seconds), 0 for non-blocking
#
# serial_receive(serialPort) - Checks if there is a message in the receive buffer, returns it if so
# serialPort - The object returned by initialise_port()
#
# serial_send(serialPort, command) - Encodes string and attempts to send over serialPort (e.g. object instantiated with initialise_port())
# command - The string you want to send
# 
# serialPort.close() - Closes the serial port
#
# General process: deviceLocation = auto_locate(); serialPort = initialise_port(deviceLocation); serial_send/receive(...); serialPort.close() when done
#
# ------------------------------------------------------------------

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

# Attempt to locate an STM or ESP device and return its port - Can improve if needed
def auto_locate():
    ports = serial.tools.list_ports.comports()
    if not ports:
        print(" > Automatic location failed: No devices detected.")
    else:
        for port in ports:
            if port.vid in [1155, 12346]:
                print(f"Device located at port: {port.device}")
                return port.device
        print (" > Automatic location failed: Detected devices not recognised.")

def initialise_port(portName, baudRate=115200, timeout=0):
    try:
        serialPort = serial.Serial(portName, baudRate, timeout=timeout)
        return serialPort
    except serial.SerialException as error:
        if "FileNotFoundError" in str(error):
            print(" > Initialisation Error: Specified port cannot be found. Check connection and port name.")
        elif "PermissionError" in str(error):
            print(" > Initialisation Error: Permission denied. User lacks required permissions, or port already in use.")
        else:
            print(f"Initialisation error: {error}")

def serial_receive(serialPort):
    if serialPort.in_waiting:
        message = serialPort.readall().decode()
        return message
    print("No message in buffer.")

def serial_send(serialPort, command):
    try:
        serialPort.write((str(command)+"\n").encode())
    except serial.SerialException as error:
        print(f"Write error: {error}")
