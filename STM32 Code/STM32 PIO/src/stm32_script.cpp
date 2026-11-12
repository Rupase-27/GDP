//
//  MOTOR CONNECTIONS
//
//  Initalises FOC controller and links motors to AS5048A encoders.
//  
//  OVERVIEW
//
//  User will input velocity of movement and direction using external 'game'
//  controller and the motors will move accordingly. Encoders are used to 
//  track the position and angle of the motor.
//
//  checkStop() - Checks the external emergency stop button
//
//  triggerEmergencyStop() - Disables all motors during an issue
//
//  setup() - Initalisation and linking
//
//  loop() - FOC feedback for smooth and highly efficient motor movement
//
//////////////////////////////////////////////////////////////////////////

#include <Arduino.h>
#include <SPI.h>
#include <SimpleFOC.h>

MagneticSensorSPI encoder1(AS5048_SPI, PB6);
MagneticSensorSPI encoder2(AS5048_SPI, PB12);
MagneticSensorSPI encoder3(AS5048_SPI, PB11);

BLDCDriver3PWM driver1(PA10, PA9, PA8, PB1);
BLDCDriver3PWM driver2(PC6, PC7, PC9, PB5);
BLDCDriver3PWM driver3(PB2, PC2, PC8, PC5);

BLDCMotor motor1(11);
BLDCMotor motor2(11);
BLDCMotor motor3(11);

const int ESTOP_PIN = PC3;

float target_velocity1 = 0.0f;
float target_velocity2 = 0.0f;
float target_velocity3 = 0.0f;

const float MAX_ERROR = 3.0f;
const float MAX_VELOCITY = 5.0f;

unsigned long controlStartTime = 0;

void triggerEmergencyStop();
void checkStop();
void errorCheck();

void triggerEmergencyStop()
{
    target_velocity1 = 0.0f;
    target_velocity2 = 0.0f;
    target_velocity3 = 0.0f;

    motor1.disable();
    motor2.disable();
    motor3.disable();

    Serial.println("EMERGENCY STOP: Halting all motor drivers.");

    while (true)
    {
        delay(100);
    }
}

void checkStop()
{
    if (digitalRead(ESTOP_PIN) == LOW)
    {
        triggerEmergencyStop();
    }
}

void errorCheck()
{
    if (millis() - controlStartTime < 1000)
    {
        return;
    }

    float error1 = abs(target_velocity1 - motor1.shaft_velocity);
    float error2 = abs(target_velocity2 - motor2.shaft_velocity);
    float error3 = abs(target_velocity3 - motor3.shaft_velocity);

    if (error1 > MAX_ERROR)
    {
        Serial.println(
            "MOTOR 1 SPEED ERROR -> TRIGGERED EMERGENCY STOP"
        );

        triggerEmergencyStop();
    }

    if (error2 > MAX_ERROR)
    {
        Serial.println(
            "MOTOR 2 SPEED ERROR -> TRIGGERED EMERGENCY STOP"
        );

        triggerEmergencyStop();
    }

    if (error3 > MAX_ERROR)
    {
        Serial.println(
            "MOTOR 3 SPEED ERROR -> TRIGGERED EMERGENCY STOP"
        );

        triggerEmergencyStop();
    }
}

void setup()
{
    Serial.begin(115200);
    delay(2000);

    SimpleFOCDebug::enable(&Serial);

    pinMode(ESTOP_PIN, INPUT_PULLUP);

    pinMode(PB6, OUTPUT);
    pinMode(PB12, OUTPUT);
    pinMode(PB11, OUTPUT);

    digitalWrite(PB6, HIGH);
    digitalWrite(PB12, HIGH);
    digitalWrite(PB11, HIGH);

    SPI.begin();

    encoder1.init();
    encoder2.init();
    encoder3.init();

    driver1.voltage_power_supply = 12;
    driver2.voltage_power_supply = 12;
    driver3.voltage_power_supply = 12;

    driver1.voltage_limit = 3.0f;
    driver2.voltage_limit = 3.0f;
    driver3.voltage_limit = 3.0f;

    int driverStatus1 = driver1.init();
    int driverStatus2 = driver2.init();
    int driverStatus3 = driver3.init();

    if (!driverStatus1 || !driverStatus2 || !driverStatus3)
    {
        Serial.println("MOTOR DRIVER INITIALISATION FAILED");
        triggerEmergencyStop();
    }

    motor1.linkDriver(&driver1);
    motor1.linkSensor(&encoder1);

    motor2.linkDriver(&driver2);
    motor2.linkSensor(&encoder2);

    motor3.linkDriver(&driver3);
    motor3.linkSensor(&encoder3);

    motor1.controller = MotionControlType::velocity;
    motor2.controller = MotionControlType::velocity;
    motor3.controller = MotionControlType::velocity;

    motor1.torque_controller = TorqueControlType::voltage;
    motor2.torque_controller = TorqueControlType::voltage;
    motor3.torque_controller = TorqueControlType::voltage;

    motor1.voltage_limit = 3.0f;
    motor2.voltage_limit = 3.0f;
    motor3.voltage_limit = 3.0f;

    motor1.voltage_sensor_align = 2.0f;
    motor2.voltage_sensor_align = 2.0f;
    motor3.voltage_sensor_align = 2.0f;

    motor1.velocity_limit = MAX_VELOCITY;
    motor2.velocity_limit = MAX_VELOCITY;
    motor3.velocity_limit = MAX_VELOCITY;

    motor1.PID_velocity.P = 0.2f;
    motor1.PID_velocity.I = 2.0f;
    motor1.PID_velocity.D = 0.0f;

    motor2.PID_velocity.P = 0.2f;
    motor2.PID_velocity.I = 2.0f;
    motor2.PID_velocity.D = 0.0f;

    motor3.PID_velocity.P = 0.2f;
    motor3.PID_velocity.I = 2.0f;
    motor3.PID_velocity.D = 0.0f;

    motor1.LPF_velocity.Tf = 0.02f;
    motor2.LPF_velocity.Tf = 0.02f;
    motor3.LPF_velocity.Tf = 0.02f;

    int motorStatus1 = motor1.init();
    int motorStatus2 = motor2.init();
    int motorStatus3 = motor3.init();

    if (!motorStatus1 || !motorStatus2 || !motorStatus3)
    {
        Serial.println("MOTOR INITIALISATION FAILED");
        triggerEmergencyStop();
    }

    int focStatus1 = motor1.initFOC();

    if (!focStatus1)
    {
        Serial.println("MOTOR 1 FOC INITIALISATION FAILED");
        triggerEmergencyStop();
    }

    int focStatus2 = motor2.initFOC();

    if (!focStatus2)
    {
        Serial.println("MOTOR 2 FOC INITIALISATION FAILED");
        triggerEmergencyStop();
    }

    int focStatus3 = motor3.initFOC();

    if (!focStatus3)
    {
        Serial.println("MOTOR 3 FOC INITIALISATION FAILED");
        triggerEmergencyStop();
    }

    controlStartTime = millis();

    Serial.println("All motors ready.");
}

void loop()
{
    checkStop();

    motor1.loopFOC();
    motor2.loopFOC();
    motor3.loopFOC();

    motor1.move(target_velocity1);
    motor2.move(target_velocity2);
    motor3.move(target_velocity3);

    errorCheck();
}
