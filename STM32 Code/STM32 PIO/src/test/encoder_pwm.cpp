#include <Arduino.h>
#include <SimpleFOC.h>

#define ENCODER_CS  PB6
#define ENCODER_PWM PB7

#define IN1       PB2
#define IN2       PC2
#define IN3       PC8
#define DRIVER_EN PC5

MagneticSensorPWM sensor(
    ENCODER_PWM,
    4,
    1000
);

BLDCMotor motor = BLDCMotor(11);

BLDCDriver3PWM driver = BLDCDriver3PWM(
    IN1,
    IN2,
    IN3,
    DRIVER_EN
);

void doPWM() {
    sensor.handlePWM();
}

unsigned long previousPrintTime = 0;
const unsigned long printInterval = 100;

void setup() {
    Serial.begin(115200);
    delay(1000);

    driver.voltage_power_supply = 12; // V
    driver.init();
    motor.linkDriver(&driver);

    sensor.init();
    sensor.enableInterrupt(doPWM);
    motor.linkSensor(&sensor);

    motor.init();
    motor.initFOC();

    Serial.println("Motor ready");
    _delay(1000);
}

void loop() {
    motor.loopFOC();
    motor.move(2.0f);

    if (millis() - previousPrintTime >= printInterval) {
        previousPrintTime = millis();

        Serial.print("Angle: ");
        Serial.print(sensor.getAngle(), 4);
    }
}