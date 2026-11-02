#include <Arduino.h>
#include <SimpleFOC.h>
#include <SPI.h>

// Motor driver pins
#define IN11 25
#define IN21 26
#define IN31 27
#define EN1 14

// AS5048A encoder
MagneticSensorSPI sensor = MagneticSensorSPI(AS5048_SPI, SS);

// 3-PWM driver
BLDCDriver3PWM driver = BLDCDriver3PWM(IN11, IN21, IN31, EN1);

// Motor (change pole pairs to your motor)
BLDCMotor motor = BLDCMotor(11);

void setup() {
  Serial.begin(115200);
  delay(1000);

  Serial.println("Starting");

  // Encoder
  sensor.init();

  // Link sensor to motor
  motor.linkSensor(&sensor);

  // Driver setup
  driver.voltage_power_supply = 10.0;    // Set to your supply voltage
  driver.init();

  // Link driver
  motor.linkDriver(&driver);

  // Open loop velocity mode
  motor.controller = MotionControlType::velocity_openloop;

  motor.voltage_limit = 10.0;

  motor.init();
  Serial.println("Motor initialised");
}

void loop() {

  // Spin continuously at 5 rad/s
  motor.move(5.0);

  // Update sensor reading
  sensor.update();

  Serial.print("Angle rad: ");
  Serial.print(sensor.getAngle(), 4);

  Serial.print("   Deg: ");
  Serial.println(sensor.getAngle() * 180.0f / PI, 1);

  delay(100);
}