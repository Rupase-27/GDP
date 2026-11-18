//
//  OVERVIEW:
//  This code is designed to control 3 GM3506 motors using a STM32G491RE Nucleo board. 
//  The motors are controlled using open-loop velocity control in SimpleFOC library
//
//  The code allows for two modes of operation: guidewire and catheter mode, which can be 
//  toggled using a switch. The motors can be enabled or disabled using a start button, 
//  and an emergency stop button is provided for safety. The speed of the motors can be 
//  adjusted using up and down buttons.
//
//  doPWM1(), doPWM2(), doPWM3()
//  - Interrupt service routines for handling PWM signals from the encoders
//
//  start() 
//  - Enables the motors when the start button is pressed
//  - Inputs: None
//  - Updates: motorsEnabled
//
//  triggerEmergencyStop() 
//  - Disables all motors and prints "EMERGENCY STOP"
//  - Inputs: None
//  - Updates: motorsEnabled
//
//  checkStop() 
//  - Checks if the emergency stop button is pressed and triggers emergency stop
//  - Inputs: None
//
//  updateMode() 
//  - Reads the mode toggleswitch and updates the guidewireMode variable
//  - Inputs: None
//  - Updates: guidewireMode
//
//  readControls()
//  - Reads the state of control buttons and updates target velocities for each motor
//  - Rotation disabled for catheter mode
//  - Velocity set to 0 when fwd/back or cw/ccw buttons are pressed together
//  - Inputs: None
//  - Updates: Target velocities
//
//  readSpeedButtons()
//  - Reads the state of speed control buttons and updates CONTROL_SPEED
//  - Includes debounce logic with edge detection and time constraints to prevent multiple 
//    increments/decrements from a single press
//  - Inputs: None
//  - Updates: CONTROL_SPEED
//
//  currentAngleUpdate()
//  - Updates the global angle variable of working motor based on encoder readings
//  - Can be used in UI to show angle or later diatnce moved
//  - Inputs: None
//  - Updates: current_moving_angle
//
////////////////////////////////////////////////////////////////////////////////



#include <Arduino.h>
#include <SimpleFOC.h>

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

#define ESTOP PC4
#define MODE_SWITCH PB13
#define START PB14

#define UP_SPEED PB15
#define DOWN_SPEED PB1

#define BTN_FORWARD PA12
#define BTN_BACK PA11
#define BTN_CW PB12
#define BTN_CCW PB11

unsigned long previousPrintTime = 0;
const unsigned long printInterval = 100;

float CONTROL_VELOCITY = 2.0f;
const float MAX_VELOCITY = 5.0f;
const unsigned long DEBOUNCE_TIME = 50;

float target_velocity1 = 0.0f;
float target_velocity2 = 0.0f;
float target_velocity3 = 0.0f;

float current_angle1 = 0.0f;
float current_angle2 = 0.0f;
float current_angle3 = 0.0f;

float previous_angle1 = 0.0f;
float previous_angle2 = 0.0f;
float previous_angle3 = 0.0f;

float current_moving_angle = 0.0f;

bool guidewireMode = true;
bool motorsEnabled = false;

MagneticSensorPWM sensor1(ENCODER1_PWM, 4, 1000);
MagneticSensorPWM sensor2(ENCODER2_PWM, 4, 1000);
MagneticSensorPWM sensor3(ENCODER3_PWM, 4, 1000);

BLDCMotor motor1 = BLDCMotor(11);
BLDCMotor motor2 = BLDCMotor(11);
BLDCMotor motor3 = BLDCMotor(11);

BLDCDriver3PWM driver1 = BLDCDriver3PWM(
    IN1_1,
    IN2_1,
    IN3_1,
    DRIVER1_EN
);

BLDCDriver3PWM driver2 = BLDCDriver3PWM(
    IN1_2,
    IN2_2,
    IN3_2,
    DRIVER2_EN
);

BLDCDriver3PWM driver3 = BLDCDriver3PWM(
    IN1_3,
    IN2_3,
    IN3_3,
    DRIVER3_EN
);

void doPWM1() {
    sensor1.handlePWM();
}

void doPWM2() {
    sensor2.handlePWM();
}

void doPWM3() {
    sensor3.handlePWM();
}

void start()
{
    if (!motorsEnabled && digitalRead(START) == LOW)
    {
        digitalWrite(DRIVER1_EN, HIGH);
        digitalWrite(DRIVER2_EN, HIGH);
        digitalWrite(DRIVER3_EN, HIGH);

        motorsEnabled = true;

        Serial.println("Motors enabled");
    }
}

void triggerEmergencyStop()
{
    driver1.disable();
    driver2.disable();
    driver3.disable();

    motorsEnabled = false;

    Serial.println("EMERGENCY STOP");

    start();

}

void checkStop()
{
    if (digitalRead(ESTOP) == LOW)
    {
        triggerEmergencyStop();
    }
}

void updateMode()
{
    guidewireMode =
        digitalRead(MODE_SWITCH);
}

void readSpeedButtons() {
    const float SPEED_INCREMENT = 0.2f;

    static bool lastUpReading = HIGH;
    static bool lastDownReading = HIGH;

    static bool stableUpState = HIGH;
    static bool stableDownState = HIGH;

    static unsigned long upChangeTime = 0;
    static unsigned long downChangeTime = 0;

    unsigned long currentTime = millis();

    bool upRead = digitalRead(UP_SPEED);
    bool downRead = digitalRead(DOWN_SPEED);

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

void readControls()
{
    target_velocity1 = 0.0f;
    target_velocity2 = 0.0f;
    target_velocity3 = 0.0f;

    if (guidewireMode)
    {
        if (!digitalRead(BTN_FORWARD) && !digitalRead(BTN_BACK))
        {
            target_velocity1 = 0.0f;
        }
        else if (!digitalRead(BTN_FORWARD))
        {
            target_velocity1 = CONTROL_VELOCITY;
        }
        else if (!digitalRead(BTN_BACK))
        {
            target_velocity1 = -CONTROL_VELOCITY;
        }

        if (!digitalRead(BTN_CW) && !digitalRead(BTN_CCW))
        {
            target_velocity2 = 0.0f;
        }
        else if (!digitalRead(BTN_CW))
        {
            target_velocity2 = CONTROL_VELOCITY;
        }
        else if (!digitalRead(BTN_CCW))
        {
            target_velocity2 = -CONTROL_VELOCITY;
        }
    }
    else
    {
        if (!digitalRead(BTN_FORWARD) && !digitalRead(BTN_BACK))
        {
            target_velocity3 = 0.0f;
        }
        else if (!digitalRead(BTN_FORWARD))
        {
            target_velocity3 = CONTROL_VELOCITY;
        }
        else if (!digitalRead(BTN_BACK))
        {
            target_velocity3 = -CONTROL_VELOCITY;
        }
    }
}

void currentAngleUpdate() {
    current_angle1 = sensor1.getAngle();
    current_angle2 = sensor2.getAngle();
    current_angle3 = sensor3.getAngle();

    // may need to change to small interval depending on accuracy

    if (target_velocity1 != 0) {
        current_moving_angle = current_angle1;
    }
    else if (target_velocity2 != 0) {
        current_moving_angle = current_angle2;
    }
    else if (target_velocity3 != 0) {
        current_moving_angle = current_angle3;
    }
}

void setup() {
    Serial.begin(115200);
    delay(1000);

    pinMode(ESTOP, INPUT_PULLUP);
    pinMode(MODE_SWITCH, INPUT_PULLUP);
    pinMode(START, INPUT_PULLUP);

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

    previous_angle1 = sensor1.getAngle();
    previous_angle2 = sensor2.getAngle();
    previous_angle3 = sensor3.getAngle();

    motorsEnabled = false;

    Serial.println("Motors disabled - press START");

}

void loop() {
    start();
    readSpeedButtons();
    checkStop();
    updateMode();
    readControls();
    currentAngleUpdate();

    motor1.loopFOC();
    motor2.loopFOC();
    motor3.loopFOC();

    motor1.move(-target_velocity1);
    motor2.move(-target_velocity2);
    motor3.move(target_velocity3);

    if (millis() - previousPrintTime >= printInterval) {
        previousPrintTime = millis();

        Serial.print("Mode: ");
        Serial.print(guidewireMode ? "Guidewire" : "Catheter");

        Serial.print("Angle of Moving motor: ");
        Serial.print(current_moving_angle, 4);
    }
}