////////////////////////////////////////////////////////////////////////////////
//
//  OVERVIEW:
//  This code controls 3 GM3506 BLDC motors using an STM32G491RE Nucleo board.
//  The motors operate using open-loop velocity control through the SimpleFOC
//  library.
//
//  The system supports two operating modes:
//  - Guidewire mode: Motor 1 controls linear movement and Motor 2 controls rotation.
//  - Catheter mode: Motor 3 controls linear movement.
//
//  The motors can be controlled using either physical buttons or a UI connected
//  through the onboard USB virtual COM port (UART communication).
//
//  The physical controller includes movement buttons, speed adjustment buttons,
//  a mode selection switch, a start button and an emergency stop button.
//
//  UI commands are received through serial communication and stored in the
//  CommandData structure, which is also used for physical controller inputs.
//
//  PWM encoder feedback is used to monitor motor angular position and transmit
//  position information to the UI.
//
//
//  ENUMERATIONS AND STRUCTURES:
//
//  ControlSource
//  - Defines whether commands are received from the UI or physical controller.
//
//  OperatingMode
//  - Defines whether the guidewire or catheter mechanism is selected.
//
//  ControlCommand
//  - Defines the requested motor action, including movement, start, stop
//    and switching between control sources.
//
//  CommandData
//  - Stores the selected operating mode, control command and UI speed setting.
//  - Variables: mode, control, speed.
//
//
//  FUNCTIONS:
//
//  doPWM1(), doPWM2(), doPWM3()
//  - Interrupt service routines for processing PWM signals from the encoders.
//  - Each function calls handlePWM() for its corresponding encoder.
//  - Inputs: None.
//  - Updates: Internal encoder measurements.
//
//  parseMode()
//  - Converts a received mode string into the corresponding OperatingMode.
//  - Inputs: String containing the requested operating mode.
//  - Returns: OperatingMode::GUIDEWIRE or OperatingMode::CATHETER.
//
//  parseControl()
//  - Converts a received control string into the corresponding ControlCommand.
//  - Toggles UIController when the SWITCH command is received.
//  - Inputs: String containing the requested control action.
//  - Returns: Corresponding ControlCommand enumeration.
//  - Updates: UIController when switching control sources.
//
//  readUICommunication()
//  - Reads incoming serial data from the UI through the USB virtual COM port.
//  - Stores received characters until a newline character is detected.
//  - Separates the received command into source, mode, control and speed.
//  - Validates the speed value and converts received strings into enumerations.
//  - Inputs: Serial data from the UI.
//  - Updates: Data.mode, Data.control, Data.speed.
//
//  controlMethod()
//  - Selects whether the UI or physical controller is used for motor control.
//  - Processes the SWITCH command to update the active control source.
//  - Calls readButtonInput() when switching to physical control.
//  - Inputs: Data.control, UIController.
//  - Updates: source.
//
//  readButtonInput()
//  - Reads the physical controller buttons and mode selection switch.
//  - Checks the emergency stop and start buttons before movement inputs.
//  - Converts physical button presses into ControlCommand values.
//  - Intended to select guidewire or catheter mode using the mode switch.
//  - Inputs: Physical button and switch states.
//  - Updates: Data.control.
//  - Note: The current mode switch code does not update Data.mode.
//
//  checkEmergencyStop()
//  - Checks whether a STOP command has been received.
//  - Disables all three motor drivers when the motors are enabled.
//  - Updates the motor enable state and clears the command string.
//  - Inputs: Data.control, motorsEnabled.
//  - Updates: motorsEnabled, command.
//
//  checkStart()
//  - Checks whether a START command has been received.
//  - Enables all three motor drivers if they are currently disabled.
//  - Inputs: Data.control, motorsEnabled.
//  - Updates: motorsEnabled.
//
//  readSpeed()
//  - Updates motor velocity using UI or physical controller inputs.
//  - For UI control, calculates the change in speed from the previous UI value.
//  - For physical control, detects speed button presses using debounce logic.
//  - Increases or decreases velocity in increments of SPEED_INCREMENT.
//  - Limits commanded velocity between 0 and MAX_VELOCITY.
//  - Inputs: Data.speed, source, UP_SPEED, DOWN_SPEED.
//  - Updates: CONTROL_VELOCITY, previousUISpeed.
//
//  readControls()
//  - Determines the target velocities of the motors based on the selected
//    operating mode and requested control command.
//  - In guidewire mode, Motor 1 controls linear movement and Motor 2 rotation.
//  - Motor 2 movements restricted based on cw and acw rotation flags.
//  - In catheter mode, Motor 3 controls linear movement.
//  - Positive and negative velocities determine the movement direction.
//  - Inputs: Data.mode, Data.control, CONTROL_VELOCITY, motorsEnabled.
//  - Updates: target_velocity1, target_velocity2, target_velocity3.
//  - Note: Target velocities are not currently reset on RELEASE.
//
//  currentAngleUpdate()
//  - Updates the angular position measurements from all three encoders.
//  - Selects the angle of the motor currently commanded to move.
//  - IF angle of guidewire rotation exceeds +/- 180 degrees from start flags to controller and UI.
//  - Converts the selected motor angle from radians to degrees.
//  - Constrain the displayed angle between 0 and 360 degrees.
//  - The degree angle transmitted to the UI or current angle used to calculate displacement.
//  - Inputs: Encoder measurements, target motor velocities.
//  - Updates: current_angle1, current_angle2, current_angle3,
//             current_moving_angle, degree_moving_angle, cwFlag, acwFlag.
//
//  setup()
//  - Initialises serial communication and configures physical controller inputs.
//  - Initialises the three PWM encoders and enables their interrupts.
//  - Configures the motor drivers with supply voltage and voltage limits.
//  - Links each motor to its corresponding driver.
//  - Configures all motors for open-loop velocity control.
//  - Initialises the motors and disables the drivers until a start command.
//  - Read startup angle of encoder for rotation and calculates limits from this.
//  - Inputs: None.
//  - Updates: Hardware configuration, motorsEnabled.
//
//  loop()
//  - Continuously processes UI commands and control source selection.
//  - Checks emergency stop and start commands.
//  - Updates motor speed and target velocities.
//  - Reads encoder measurements and updates the current moving angle.
//  - Executes SimpleFOC motor control functions.
//  - Applies the target velocities to all three motors.
//  - Transmits the current moving angle to the UI every 100 ms.
//  - Inputs: UI commands, physical controller inputs, encoder measurements.
//  - Updates: Motor outputs, control variables, serial output.
//
////////////////////////////////////////////////////////////////////////////////


#include <Arduino.h>
#include <SimpleFOC.h>
#include <string>
using namespace std;

#define ENCODER1_PWM PC10
#define ENCODER2_PWM PC11
#define ENCODER3_PWM PC12

#define IN1_1 PA10
#define IN2_1 PA9
#define IN3_1 PA8
#define DRIVER1_EN PB10

#define IN1_2 PB2
#define IN2_2 PC2
#define IN3_2 PC8
#define DRIVER2_EN PC5

#define IN1_3 PC6
#define IN2_3 PC7
#define IN3_3 PC9
#define DRIVER3_EN PB5

#define BTN_STOP PC4
#define MODE_SWITCH PB13
#define BTN_START PB14

#define UP_SPEED PB15
#define DOWN_SPEED PB1

#define BTN_FORWARD PA12
#define BTN_BACK PA11
#define BTN_CW PB12
#define BTN_CCW PB11

const unsigned long PRINT_INTERVAL = 10000;
const unsigned long DEBOUNCE_TIME = 50;
const float MAX_VELOCITY = 0.2f;
const float SPEED_INCREMENT = 0.01f;

unsigned long previous_print_time = 0;

float CONTROL_VELOCITY = 0.0f;

float target_velocity1 = 0.0f;
float target_velocity2 = 0.0f;
float target_velocity3 = 0.0f;

int previousUISpeed = 0;

float current_angle1 = 0.0f;
float current_angle2 = 0.0f;
float current_angle3 = 0.0f;

float startup_rotation = 0.0f;

float min_rotation_limit = 0.0f;
float max_rotation_limit = 0.0f;

float current_moving_angle = 0.0f;
float degree_moving_angle = 0.0f;

bool guidewireMode = true;
bool motorsEnabled = false;
bool UIController = false;
bool cwFlag = false;
bool acwFlag = false;

enum class ControlSource {
    UI,
    BUTTON
};

enum class OperatingMode {
    GUIDEWIRE,
    CATHETER
};

enum class ControlCommand {
    RELEASE,
    START,
    STOP,
    PUSH,
    PULL,
    ROTATE_CW,
    ROTATE_ACW,
    SWITCH
};

ControlSource source= ControlSource::BUTTON;

struct CommandData {
    OperatingMode mode;
    ControlCommand control;
    int speed;
};

CommandData Data = {
    OperatingMode::GUIDEWIRE,
    ControlCommand::RELEASE,
    0
};

string command;
string receivedMessage;
string sendMessage;

MagneticSensorPWM sensor1(ENCODER1_PWM, 4, 1000);
MagneticSensorPWM sensor2(ENCODER2_PWM, 4, 1000);
MagneticSensorPWM sensor3(ENCODER3_PWM, 4, 1000);

BLDCMotor motor1 = BLDCMotor(11);
BLDCMotor motor2 = BLDCMotor(11);
BLDCMotor motor3 = BLDCMotor(11);

BLDCDriver3PWM driver1(IN1_1, IN2_1, IN3_1,DRIVER1_EN);
BLDCDriver3PWM driver2(IN1_2, IN2_2, IN3_2, DRIVER2_EN);
BLDCDriver3PWM driver3(IN1_3, IN2_3, IN3_3, DRIVER3_EN);

void doPWM1() {
    sensor1.handlePWM();
}

void doPWM2() {
    sensor2.handlePWM();
}

void doPWM3() {
    sensor3.handlePWM();
}

OperatingMode parseMode(const string& value) {
    if (value == "catheter") {
        return OperatingMode::CATHETER;
    }

    return OperatingMode::GUIDEWIRE;
}

ControlCommand parseControl(const string& value) {
    if (value == "START") {
        return ControlCommand::START;
    }
    else if (value == "STOP") {
        return ControlCommand::STOP;
    }
    else if (value == "PUSH") {
        return ControlCommand::PUSH;
    }
    else if (value == "PULL") {
        return ControlCommand::PULL;
    }
    else if (value == "ROTATE_CW") {
        return ControlCommand::ROTATE_CW;
    }
    else if (value == "ROTATE_ACW") {
        return ControlCommand::ROTATE_ACW;
    }
    else if (value == "SWITCH"){
        // switching between control and ui
        UIController = !UIController;
        return ControlCommand::SWITCH;
    }

    return ControlCommand::RELEASE;
}

void readUICommunication() {
    while (Serial.available() > 0) {
        char receivedChar = Serial.read();

        if (receivedChar == '\r') {
            continue;
        }

        if (receivedChar == '\n') {
            command = receivedMessage;
            receivedMessage.clear();

            size_t pos1 = command.find(' ');
            size_t pos2 = command.find(' ', pos1 + 1);

            if (pos1 != string::npos &&
                pos2 != string::npos) {

                string modeString = command.substr(0, pos1);
                string controlString = command.substr(pos1 + 1, pos2 - pos1 - 1);
                string speedString = command.substr(pos2 + 1);

                if (speedString.length() == 1 &&
                    speedString[0] >= '0' &&
                    speedString[0] <= '9') {
                    
                    Data.mode = parseMode(modeString);
                    Data.control = parseControl(controlString); 
                    Data.speed = speedString[0] - '0';
                }
                else {
                    Serial.println("Invalid speed");
                }
            }
            else {
                Serial.println("Invalid command");
            }

            command.clear();
        }
        else {
            receivedMessage += receivedChar;
        }
    }
}

void controlMethod() {
    if (Data.control == ControlCommand::SWITCH) {
        if (UIController){
            source = ControlSource::UI;
        }
        else {
            source = ControlSource::BUTTON;
        }
    }
}

void readButtonInput() {

    if (!digitalRead(BTN_STOP) == HIGH) {
            Data.control = ControlCommand::STOP;
            return;
        }

    if (source == ControlSource::BUTTON) {

        if (!motorsEnabled && !digitalRead(BTN_START) == HIGH) {
            Data.control = ControlCommand::START;
            return;
        }

        // only going to be used when controller inputs read from i.e control method BUTTONS
        if (digitalRead(MODE_SWITCH) == HIGH){
            Data.mode = OperatingMode::CATHETER;
        }   
        else {
            Data.mode = OperatingMode::GUIDEWIRE;
        }

        if (!digitalRead(BTN_FORWARD) && digitalRead(BTN_BACK)) {
            Data.control = ControlCommand::PUSH;
        }
        else if (!digitalRead(BTN_BACK) && digitalRead(BTN_FORWARD)) {
            Data.control = ControlCommand::PULL;
        }
        else if (!digitalRead(BTN_CW) && digitalRead(BTN_CCW)) {
            Data.control = ControlCommand::ROTATE_CW;
        }
        else if (!digitalRead(BTN_CCW) && digitalRead(BTN_CW)) {
            Data.control = ControlCommand::ROTATE_ACW;
        }
        else {
            Data.control = ControlCommand::RELEASE;
        }
        
    }
    
}

void checkEmergencyStop() {
    if (Data.control == ControlCommand::STOP) {
        target_velocity1 = 0.0f;
        target_velocity2 = 0.0f;
        target_velocity3 = 0.0f;

        if (motorsEnabled) {
            driver1.disable();
            driver2.disable();
            driver3.disable();

            motorsEnabled = false;
        }

        command.clear();
    }
}

void checkStart() {
    if (!motorsEnabled && (Data.control == ControlCommand::START)){
        driver1.enable();
        driver2.enable();
        driver3.enable();

        motorsEnabled = true;
    }
}

void readSpeed() {
    static bool lastUpReading = HIGH;
    static bool lastDownReading = HIGH;

    static bool stableUpState = HIGH;
    static bool stableDownState = HIGH;

    static unsigned long upChangeTime = 0;
    static unsigned long downChangeTime = 0;

    unsigned long currentTime = millis();

    bool upRead = digitalRead(UP_SPEED);
    bool downRead = digitalRead(DOWN_SPEED);

    if (source == ControlSource::UI ){
        int speedChange = Data.speed - previousUISpeed;

        CONTROL_VELOCITY += speedChange * SPEED_INCREMENT;

        if (CONTROL_VELOCITY > MAX_VELOCITY) {
            CONTROL_VELOCITY = MAX_VELOCITY;
        }

        if (CONTROL_VELOCITY < 0.0f) {
            CONTROL_VELOCITY = 0.0f;
        }

        previousUISpeed = Data.speed;
    }
    else {
        if (upRead != lastUpReading) {
            upChangeTime = currentTime;
            lastUpReading = upRead;
        }

        if ((currentTime - upChangeTime) >= DEBOUNCE_TIME) {
            if (upRead != stableUpState) {
                stableUpState = upRead;

                if (stableUpState == LOW) {
                    CONTROL_VELOCITY += SPEED_INCREMENT;

                    if (CONTROL_VELOCITY > MAX_VELOCITY) {
                        CONTROL_VELOCITY = MAX_VELOCITY;
                    }

                    Serial.print("Velocity increased to: ");
                    Serial.println(CONTROL_VELOCITY, 2);
                }
            }
        }
        if (downRead != lastDownReading) {
            downChangeTime = currentTime;
            lastDownReading = downRead;
        }

        if ((currentTime - downChangeTime) >= DEBOUNCE_TIME) {
            if (downRead != stableDownState) {
                stableDownState = downRead;

                if (stableDownState == LOW) {
                    CONTROL_VELOCITY -= SPEED_INCREMENT;

                    if (CONTROL_VELOCITY < 0.0f) {
                        CONTROL_VELOCITY = 0.0f;
                    }

                    Serial.print("Velocity decreased to: ");
                    Serial.println(CONTROL_VELOCITY, 2);
                }
            }
        }
    }
}

void readControls() {

    if (!motorsEnabled) {
        return;
    }

    if (Data.mode == OperatingMode::GUIDEWIRE) {
        switch (Data.control) {
            case ControlCommand::PUSH:
                target_velocity1 = CONTROL_VELOCITY;
                break;

            case ControlCommand::PULL:
                target_velocity1 = -CONTROL_VELOCITY;
                break;

            case ControlCommand::ROTATE_CW:
                if (cwFlag) {
                    target_velocity2 = 0.0f;
                }
                else {
                    target_velocity2 = CONTROL_VELOCITY;
                }
                break;

            case ControlCommand::ROTATE_ACW:
                if(acwFlag) {
                    target_velocity2 = 0.0f;
                }
                else {
                    target_velocity2 = -CONTROL_VELOCITY;
                }
                break;

            default:
                break;
        }
    }
    else {
        switch (Data.control) {
            case ControlCommand::PUSH:
                target_velocity3 = CONTROL_VELOCITY;
                break;

            case ControlCommand::PULL:
                target_velocity3 = -CONTROL_VELOCITY;
                break;

            default:
                break;
        }
    }

    if (Data.control == ControlCommand::RELEASE) {
        target_velocity1 = 0.0f;
        target_velocity2 = 0.0f;
        target_velocity3 = 0.0f;
    }
}

void currentAngleUpdate() {
    sensor1.update();
    sensor2.update();
    sensor3.update();

    current_angle1 = sensor1.getAngle();
    current_angle2 = sensor2.getAngle();
    current_angle3 = sensor3.getAngle();

    // may have to swap depending on +/- direction

    cwFlag = current_angle2 <= min_rotation_limit;
    acwFlag = current_angle2 >= max_rotation_limit;

    // current_moving_angle kept as un constrained variable in case we want to use it for distance later

    if (target_velocity1 != 0) {
        current_moving_angle = current_angle1 * 180 / PI;
    }
    else if (target_velocity2 != 0) {
        current_moving_angle = current_angle2 * 180 / PI;
    }
    else if (target_velocity3 != 0) {
        current_moving_angle = current_angle3 * 180 / PI;
    }

    // degree_moving_angle used to send back to user as easier to read
    // fmod() returns remainder 

    if (current_moving_angle < 0) {
        degree_moving_angle = fmod(current_moving_angle, -360);
    }
    else {
        degree_moving_angle = fmod(current_moving_angle, 360);
    }
}

void setup() {
    Serial.begin(115200);
    delay(1000);

    pinMode(BTN_STOP, INPUT_PULLUP);
    pinMode(MODE_SWITCH, INPUT_PULLUP);
    pinMode(BTN_START, INPUT_PULLUP);

    pinMode(UP_SPEED, INPUT_PULLUP);
    pinMode(DOWN_SPEED, INPUT_PULLUP);

    pinMode(BTN_FORWARD, INPUT_PULLUP);
    pinMode(BTN_BACK, INPUT_PULLUP);
    pinMode(BTN_CW, INPUT_PULLUP);
    pinMode(BTN_CCW, INPUT_PULLUP);

    sensor1.init();
    sensor1.enableInterrupt(doPWM1);

    sensor2.init();
    sensor2.enableInterrupt(doPWM2);

    sensor3.init();
    sensor3.enableInterrupt(doPWM3);

    driver1.voltage_power_supply = 12.0f;
    driver1.voltage_limit = 2.0f;

    driver2.voltage_power_supply = 12.0f;
    driver2.voltage_limit = 2.0f;

    driver3.voltage_power_supply = 12.0f;
    driver3.voltage_limit = 2.0f;

    driver1.init();
    driver2.init();
    driver3.init();

    motor1.linkDriver(&driver1);
    motor2.linkDriver(&driver2);
    motor3.linkDriver(&driver3);

    motor1.voltage_limit = 2.0f;
    motor2.voltage_limit = 2.0f;
    motor3.voltage_limit = 2.0f;

    motor1.velocity_limit = MAX_VELOCITY;
    motor2.velocity_limit = MAX_VELOCITY;
    motor3.velocity_limit = MAX_VELOCITY;

    motor1.controller = MotionControlType::velocity_openloop;
    motor2.controller = MotionControlType::velocity_openloop;
    motor3.controller = MotionControlType::velocity_openloop;

    motor1.init();
    motor2.init();
    motor3.init();

    motor1.initFOC();
    motor2.initFOC();
    motor3.initFOC();

    driver1.disable();
    driver2.disable();
    driver3.disable();

    motorsEnabled = false;

    startup_rotation = sensor2.getAngle();

    // 30-1 cycloidal drive - this corresponds to resricting guidewire rotation to 360 degrees rotation
    // +- 180 degrees from startup
    max_rotation_limit = startup_rotation + (30*PI);
    min_rotation_limit = startup_rotation - (30*PI);

}

void loop() {
    
    readUICommunication();

    controlMethod();

    readButtonInput();

    checkEmergencyStop();

    checkStart();

    readSpeed();

    currentAngleUpdate();

    readControls();

    motor1.loopFOC();
    motor2.loopFOC();
    motor3.loopFOC();

    motor1.move(-target_velocity1);
    motor2.move(-target_velocity2);
    motor3.move(target_velocity3);

    if (millis() - previous_print_time >= PRINT_INTERVAL) {
        previous_print_time = millis();

        Serial.print("ANGLE ");
        Serial.println(degree_moving_angle, 2);
    }
}