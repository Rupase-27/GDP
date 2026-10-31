#include <SimpleFOC.h>

// Encoders
MagneticSensorSPI encoder1 = MagneticSensorSPI(AS5048_SPI, PB6);
MagneticSensorSPI encoder2 = MagneticSensorSPI(AS5048_SPI, PB12);
MagneticSensorSPI encoder3 = MagneticSensorSPI(AS5048_SPI, PB11);

// Drivers
BLDCDriver3PWM driver1 = BLDCDriver3PWM(PA10, PA9, PA8, PB1);
BLDCDriver3PWM driver2 = BLDCDriver3PWM(PC6, PC7, PC9, PB5);
BLDCDriver3PWM driver3 = BLDCDriver3PWM(PB2, PC2, PC8, PC5);

// Motors
BLDCMotor motor1 = BLDCMotor(11); // Guidewire Translation
BLDCMotor motor2 = BLDCMotor(11); // Guidewire Rotation
BLDCMotor motor3 = BLDCMotor(11); // Catheter Translation

// Pins
#define ESTOP_PIN    PC3
#define MODE_SWITCH  PC14
#define BTN_FORWARD  PC10
#define BTN_BACK     PC11
#define BTN_CW       PC12
#define BTN_CCW      PA15

float target_velocity1 = 0.0f;
float target_velocity2 = 0.0f;
float target_velocity3 = 0.0f;

const float MAX_VELOCITY = 5.0f;
const float CONTROL_SPEED = 2.0f;

bool guidewireMode = true;

// =======================

void triggerEmergencyStop()
{
    Serial.println("EMERGENCY STOP");
    motor1.disable();
    motor2.disable();
    motor3.disable();
    while (true)
    {
    }
}

void checkStop()
{
    if (digitalRead(ESTOP_PIN) == LOW)
    {
        triggerEmergencyStop();
    }
}

void updateMode()
{
    guidewireMode = digitalRead(MODE_SWITCH);
}

void readControls()
{
    target_velocity1 = 0;
    target_velocity2 = 0;
    target_velocity3 = 0;

    if (guidewireMode)
    {
        // GUIDEWIRE MODE

        // Translation
        if (!digitalRead(BTN_FORWARD))
            target_velocity1 = CONTROL_SPEED;

        if (!digitalRead(BTN_BACK))
            target_velocity1 = -CONTROL_SPEED;

        // Rotation
        if (!digitalRead(BTN_CW))
            target_velocity2 = CONTROL_SPEED;

        if (!digitalRead(BTN_CCW))
            target_velocity2 = -CONTROL_SPEED;
    }
    else
    {
        // CATHETER MODE

        if (!digitalRead(BTN_FORWARD))
            target_velocity3 = CONTROL_SPEED;

        if (!digitalRead(BTN_BACK))
            target_velocity3 = -CONTROL_SPEED;
    }
}

void setup()
{
    Serial.begin(115200);
    delay(1000);

    pinMode(ESTOP_PIN, INPUT_PULLUP);
    pinMode(MODE_SWITCH, INPUT_PULLUP);
    pinMode(BTN_FORWARD, INPUT_PULLUP);
    pinMode(BTN_BACK, INPUT_PULLUP);
    pinMode(BTN_CW, INPUT_PULLUP);
    pinMode(BTN_CCW, INPUT_PULLUP);

    encoder1.init();
    encoder2.init();
    encoder3.init();

    driver1.voltage_power_supply = 8;
    driver2.voltage_power_supply = 8;
    driver3.voltage_power_supply = 8;

    driver1.init();
    driver2.init();
    driver3.init();

    motor1.linkDriver(&driver1);
    motor1.linkSensor(&encoder1);

    motor2.linkDriver(&driver2);
    motor2.linkSensor(&encoder2);

    motor3.linkDriver(&driver3);
    motor3.linkSensor(&encoder3);

    motor1.controller = MotionControlType::velocity;
    motor2.controller = MotionControlType::velocity;
    motor3.controller = MotionControlType::velocity;

    motor1.voltage_limit = 3;
    motor2.voltage_limit = 3;
    motor3.voltage_limit = 3;

    motor1.velocity_limit = MAX_VELOCITY;
    motor2.velocity_limit = MAX_VELOCITY;
    motor3.velocity_limit = MAX_VELOCITY;

    motor1.init();
    motor2.init();
    motor3.init();

    motor1.initFOC();
    motor2.initFOC();
    motor3.initFOC();

    Serial.println("System Ready");
}

void loop()
{
    checkStop();

    updateMode();

    motor1.loopFOC();
    motor2.loopFOC();
    motor3.loopFOC();

    readControls();

    motor1.move(target_velocity1);
    motor2.move(target_velocity2);
    motor3.move(target_velocity3);

    static unsigned long lastPrint = 0;

    if (millis() - lastPrint > 1000)
    {
        lastPrint = millis();

        if (guidewireMode)
            Serial.println("MODE: GUIDEWIRE");
        else
            Serial.println("MODE: CATHETER");
    }
}
