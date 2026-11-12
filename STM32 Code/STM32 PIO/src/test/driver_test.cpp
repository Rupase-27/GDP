#include <Arduino.h>
#include <SPI.h>
#include <SimpleFOC.h>

#define ENCODER_CS PB6

#define PWM_A      PA10    // D2
#define PWM_B      PA9     // D8
#define PWM_C      PA8     // D7
#define DRIVER_EN  PB1


MagneticSensorSPI encoder(
    AS5048_SPI,
    ENCODER_CS
);

BLDCDriver3PWM driver(
    PWM_A,
    PWM_B,
    PWM_C,
    DRIVER_EN
);

BLDCMotor motor(11);

float target_velocity = 2;

Commander command = Commander(Serial);

void onTarget(char* cmd){ command.scalar(&target_velocity, cmd); }

void setup() {
    Serial.begin(115200);
    delay(2000);

    SimpleFOCDebug::enable(&Serial);

    command.add('T', onTarget, "target velocity");
  // initialize magnetic sensor hardware
  encoder.init();
  // link the motor to the sensor
  motor.linkSensor(&encoder);

  // driver config
  driver.voltage_power_supply = 12; // V
  driver.init();
  motor.linkDriver(&driver);

  motor.controller = MotionControlType::velocity;
  motor.torque_controller = TorqueControlType::voltage; 

  motor.updateVoltageLimit(3.0);

  motor.PID_velocity.P = 0.2;
  motor.PID_velocity.I = 20;
  motor.PID_velocity.D = 0;
  
  motor.PID_velocity.output_ramp = 1000.0f;
  motor.LPF_velocity.Tf = 0.02;

  motor.voltage_sensor_align = 3.0f;

  motor.init();

  Serial.println("Rotate motor by hand now...");

for (int i = 0; i < 100; i++)
{
    encoder.update();

    Serial.print("angle = ");
    Serial.print(encoder.getAngle(), 4);

    Serial.print(" | mech angle = ");
    Serial.println(encoder.getMechanicalAngle(), 4);

    delay(100);
}
  motor.initFOC();

  Serial.println("Motor ready.");
  _delay(1000);
}

void loop() {
  motor.loopFOC();

  motor.move(target_velocity);

  command.run();
}