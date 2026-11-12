#include <Arduino.h>
#include <SimpleFOC.h>
#include <math.h>

BLDCDriver3PWM driver1(PA10, PA9, PA8, PB1);
BLDCDriver3PWM driver2(PC6, PC7, PC9, PB5);
BLDCDriver3PWM driver3(PB2, PC2, PC8, PC5);

const int pole_pairs = 11;

float electrical_angle = 0.0f;

float target_velocity = 0.05f;
float current_velocity = 0.0f;

float voltage_amplitude = 1.0f;
float supply_voltage = 12.0f;

uint32_t previous_time = 0;
uint32_t previous_print = 0;

void setMotorVoltages(
    BLDCDriver3PWM &driver,
    float angle,
    float direction
)
{
    angle *= direction;

    float centre_voltage = supply_voltage * 0.5f;

    float phaseA =
        centre_voltage +
        voltage_amplitude * sinf(angle);

    float phaseB =
        centre_voltage +
        voltage_amplitude *
        sinf(angle - 2.0f * PI / 3.0f);

    float phaseC =
        centre_voltage +
        voltage_amplitude *
        sinf(angle + 2.0f * PI / 3.0f);

    driver.setPwm(phaseA, phaseB, phaseC);
}

void disableAllMotors()
{
    driver1.disable();
    driver2.disable();
    driver3.disable();
}

void setup()
{
    Serial.begin(115200);
    delay(1000);

    driver1.voltage_power_supply = supply_voltage;
    driver1.voltage_limit = supply_voltage;

    driver2.voltage_power_supply = supply_voltage;
    driver2.voltage_limit = supply_voltage;

    driver3.voltage_power_supply = supply_voltage;
    driver3.voltage_limit = supply_voltage;

    if (!driver1.init())
    {
        Serial.println("Driver 1 failed");
        while (1);
    }

    if (!driver2.init())
    {
        Serial.println("Driver 2 failed");
        while (1);
    }

    if (!driver3.init())
    {
        Serial.println("Driver 3 failed");
        while (1);
    }

    driver1.enable();
    driver2.enable();
    driver3.enable();

    setMotorVoltages(driver1, 0.0f, 1.0f);
    setMotorVoltages(driver2, 0.0f, 1.0f);
    setMotorVoltages(driver3, 0.0f, 1.0f);

    delay(500);

    previous_time = micros();

    Serial.println("Enter velocity in rad/s");
}

void loop()
{
    uint32_t current_time = micros();

    float dt =
        (current_time - previous_time) * 1e-6f;

    previous_time = current_time;

    if (dt > 0.01f)
    {
        dt = 0.01f;
    }

    float acceleration = 0.2f;

    if (current_velocity < target_velocity)
    {
        current_velocity += acceleration * dt;

        if (current_velocity > target_velocity)
        {
            current_velocity = target_velocity;
        }
    }
    else if (current_velocity > target_velocity)
    {
        current_velocity -= acceleration * dt;

        if (current_velocity < target_velocity)
        {
            current_velocity = target_velocity;
        }
    }

    electrical_angle +=
        current_velocity *
        pole_pairs *
        dt;

    while (electrical_angle >= TWO_PI)
    {
        electrical_angle -= TWO_PI;
    }

    while (electrical_angle < 0.0f)
    {
        electrical_angle += TWO_PI;
    }

    setMotorVoltages(driver1, electrical_angle, 1.0f);
    setMotorVoltages(driver2, electrical_angle, 1.0f);
    setMotorVoltages(driver3, electrical_angle, 1.0f);

    if (Serial.available())
    {
        float requested_velocity =
            Serial.parseFloat();

        while (Serial.available())
        {
            Serial.read();
        }

        target_velocity = requested_velocity;

        Serial.print("Target velocity: ");
        Serial.println(target_velocity, 4);
    }
}