#include <Arduino.h>
#include <HardwareTimer.h>

#define PWM1_A PA10
#define PWM1_B PA9
#define PWM1_C PA8
#define DRIVER1_EN PB10

#define PWM2_A PC6
#define PWM2_B PC7
#define PWM2_C PC9
#define DRIVER2_EN PB5

#define PWM3_A PB2
#define PWM3_B PC2_ALT1
#define PWM3_C PC8_ALT2
#define DRIVER3_EN PC5

#define PWM1_A_CHANNEL 3
#define PWM1_B_CHANNEL 2
#define PWM1_C_CHANNEL 1

#define PWM2_A_CHANNEL 1
#define PWM2_B_CHANNEL 2
#define PWM2_C_CHANNEL 4

#define PWM3_A_CHANNEL 1
#define PWM3_B_CHANNEL 2
#define PWM3_C_CHANNEL 3

#define ESTOP_PIN PC3
#define MODE_SWITCH PC14
#define BTN_FORWARD PC10
#define BTN_BACK PC11
#define BTN_CW PC12
#define BTN_CCW PD2

#define PWM_FREQUENCY 25000

HardwareTimer pwmTimer1(TIM1);
HardwareTimer pwmTimer2(TIM8);
HardwareTimer pwmTimer3(TIM20);

const int pole_pairs = 11;

float electrical_angle1 = 0.0f;
float electrical_angle2 = 0.0f;
float electrical_angle3 = 0.0f;

float target_velocity1 = 0.0f;
float target_velocity2 = 0.0f;
float target_velocity3 = 0.0f;

float current_velocity1 = 0.0f;
float current_velocity2 = 0.0f;
float current_velocity3 = 0.0f;

const float CONTROL_SPEED = 0.05f;
const float MAX_VELOCITY = 5.0f;
const float acceleration = 0.2f;

float amplitude = 1.0f;
float supply_voltage = 12.0f;

bool guidewireMode = true;

uint32_t timer_period1;
uint32_t timer_period2;
uint32_t timer_period3;

uint32_t previous_time;
uint32_t previous_print;

void setPhaseVoltages(
    HardwareTimer &timer,
    uint32_t timer_period,
    uint32_t channelA,
    uint32_t channelB,
    uint32_t channelC,
    float angle
)
{
    float modulation = amplitude / supply_voltage;

    float dutyA =
        0.5f + modulation * sinf(angle);

    float dutyB =
        0.5f +
        modulation * sinf(angle - 2.0f * PI / 3.0f);

    float dutyC =
        0.5f +
        modulation * sinf(angle + 2.0f * PI / 3.0f);

    dutyA = constrain(dutyA, 0.0f, 1.0f);
    dutyB = constrain(dutyB, 0.0f, 1.0f);
    dutyC = constrain(dutyC, 0.0f, 1.0f);

    timer.setCaptureCompare(
        channelA,
        (uint32_t)(dutyA * timer_period),
        TICK_COMPARE_FORMAT
    );

    timer.setCaptureCompare(
        channelB,
        (uint32_t)(dutyB * timer_period),
        TICK_COMPARE_FORMAT
    );

    timer.setCaptureCompare(
        channelC,
        (uint32_t)(dutyC * timer_period),
        TICK_COMPARE_FORMAT
    );
}

void initialiseMotorTimer(
    HardwareTimer &timer,
    uint32_t pinA,
    uint32_t pinB,
    uint32_t pinC,
    uint32_t channelA,
    uint32_t channelB,
    uint32_t channelC,
    uint32_t &timer_period
)
{
    PinName pinNameA = digitalPinToPinName(pinA);
    PinName pinNameB = digitalPinToPinName(pinB);
    PinName pinNameC = digitalPinToPinName(pinC);

    timer.pause();

    timer.setMode(
        channelA,
        TIMER_OUTPUT_COMPARE_PWM1,
        pinNameA
    );

    timer.setMode(
        channelB,
        TIMER_OUTPUT_COMPARE_PWM1,
        pinNameB
    );

    timer.setMode(
        channelC,
        TIMER_OUTPUT_COMPARE_PWM1,
        pinNameC
    );

    timer.setOverflow(
        PWM_FREQUENCY,
        HERTZ_FORMAT
    );

    timer_period = timer.getOverflow(TICK_FORMAT);

    timer.setCaptureCompare(
        channelA,
        timer_period / 2,
        TICK_COMPARE_FORMAT
    );

    timer.setCaptureCompare(
        channelB,
        timer_period / 2,
        TICK_COMPARE_FORMAT
    );

    timer.setCaptureCompare(
        channelC,
        timer_period / 2,
        TICK_COMPARE_FORMAT
    );

    timer.refresh();
    timer.resume();
}

void disableAllMotors()
{
    digitalWrite(DRIVER1_EN, LOW);
    digitalWrite(DRIVER2_EN, LOW);
    digitalWrite(DRIVER3_EN, LOW);
}

void triggerEmergencyStop()
{
    disableAllMotors();

    Serial.println("EMERGENCY STOP");

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
    guidewireMode =
        digitalRead(MODE_SWITCH);
}

void readControls()
{
    target_velocity1 = 0.0f;
    target_velocity2 = 0.0f;
    target_velocity3 = 0.0f;

    if (guidewireMode)
    {
        if (!digitalRead(BTN_FORWARD))
        {
            target_velocity1 = CONTROL_SPEED;
        }

        if (!digitalRead(BTN_BACK))
        {
            target_velocity1 = -CONTROL_SPEED;
        }

        if (!digitalRead(BTN_CW))
        {
            target_velocity2 = CONTROL_SPEED;
        }

        if (!digitalRead(BTN_CCW))
        {
            target_velocity2 = -CONTROL_SPEED;
        }
    }
    else
    {
        if (!digitalRead(BTN_FORWARD))
        {
            target_velocity3 = CONTROL_SPEED;
        }

        if (!digitalRead(BTN_BACK))
        {
            target_velocity3 = -CONTROL_SPEED;
        }
    }

    target_velocity1 =
        constrain(
            target_velocity1,
            -MAX_VELOCITY,
            MAX_VELOCITY
        );

    target_velocity2 =
        constrain(
            target_velocity2,
            -MAX_VELOCITY,
            MAX_VELOCITY
        );

    target_velocity3 =
        constrain(
            target_velocity3,
            -MAX_VELOCITY,
            MAX_VELOCITY
        );
}

float updateVelocity(
    float current_velocity,
    float target_velocity,
    float dt
)
{
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

    return current_velocity;
}

float updateElectricalAngle(
    float electrical_angle,
    float velocity,
    float dt
)
{
    electrical_angle +=
        velocity *
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

    return electrical_angle;
}

void setup()
{
    Serial.begin(115200);
    delay(1000);

    pinMode(DRIVER1_EN, OUTPUT);
    pinMode(DRIVER2_EN, OUTPUT);
    pinMode(DRIVER3_EN, OUTPUT);

    digitalWrite(DRIVER1_EN, LOW);
    digitalWrite(DRIVER2_EN, LOW);
    digitalWrite(DRIVER3_EN, LOW);

    pinMode(ESTOP_PIN, INPUT_PULLUP);
    pinMode(MODE_SWITCH, INPUT_PULLUP);
    pinMode(BTN_FORWARD, INPUT_PULLUP);
    pinMode(BTN_BACK, INPUT_PULLUP);
    pinMode(BTN_CW, INPUT_PULLUP);
    pinMode(BTN_CCW, INPUT_PULLUP);

    Serial.println("Starting Timer 1");

initialiseMotorTimer(
    pwmTimer1,
    PWM1_A,
    PWM1_B,
    PWM1_C,
    PWM1_A_CHANNEL,
    PWM1_B_CHANNEL,
    PWM1_C_CHANNEL,
    timer_period1
);

Serial.println("Timer 1 ready");

initialiseMotorTimer(
    pwmTimer2,
    PWM2_A,
    PWM2_B,
    PWM2_C,
    PWM2_A_CHANNEL,
    PWM2_B_CHANNEL,
    PWM2_C_CHANNEL,
    timer_period2
);

Serial.println("Timer 2 ready");

initialiseMotorTimer(
    pwmTimer3,
    PWM3_A,
    PWM3_B,
    PWM3_C,
    PWM3_A_CHANNEL,
    PWM3_B_CHANNEL,
    PWM3_C_CHANNEL,
    timer_period3
);

Serial.println("Timer 3 ready");

    setPhaseVoltages(
        pwmTimer1,
        timer_period1,
        PWM1_A_CHANNEL,
        PWM1_B_CHANNEL,
        PWM1_C_CHANNEL,
        electrical_angle1
    );

    setPhaseVoltages(
        pwmTimer2,
        timer_period2,
        PWM2_A_CHANNEL,
        PWM2_B_CHANNEL,
        PWM2_C_CHANNEL,
        electrical_angle2
    );

    setPhaseVoltages(
        pwmTimer3,
        timer_period3,
        PWM3_A_CHANNEL,
        PWM3_B_CHANNEL,
        PWM3_C_CHANNEL,
        electrical_angle3
    );

    delay(100);

    digitalWrite(DRIVER1_EN, HIGH);
    digitalWrite(DRIVER2_EN, HIGH);
    digitalWrite(DRIVER3_EN, HIGH);

    previous_time = micros();

    Serial.println("System Ready");
}

void loop()
{
    checkStop();
    updateMode();
    readControls();

    uint32_t current_time = micros();

    float dt =
        (current_time - previous_time) * 1e-6f;

    previous_time = current_time;

    if (dt > 0.01f)
    {
        dt = 0.01f;
    }

    current_velocity1 =
        updateVelocity(
            current_velocity1,
            target_velocity1,
            dt
        );

    current_velocity2 =
        updateVelocity(
            current_velocity2,
            target_velocity2,
            dt
        );

    current_velocity3 =
        updateVelocity(
            current_velocity3,
            target_velocity3,
            dt
        );

    electrical_angle1 =
        updateElectricalAngle(
            electrical_angle1,
            current_velocity1,
            dt
        );

    electrical_angle2 =
        updateElectricalAngle(
            electrical_angle2,
            current_velocity2,
            dt
        );

    electrical_angle3 =
        updateElectricalAngle(
            electrical_angle3,
            current_velocity3,
            dt
        );

    setPhaseVoltages(
        pwmTimer1,
        timer_period1,
        PWM1_A_CHANNEL,
        PWM1_B_CHANNEL,
        PWM1_C_CHANNEL,
        electrical_angle1
    );

    setPhaseVoltages(
        pwmTimer2,
        timer_period2,
        PWM2_A_CHANNEL,
        PWM2_B_CHANNEL,
        PWM2_C_CHANNEL,
        electrical_angle2
    );

    setPhaseVoltages(
        pwmTimer3,
        timer_period3,
        PWM3_A_CHANNEL,
        PWM3_B_CHANNEL,
        PWM3_C_CHANNEL,
        electrical_angle3
    );

    if (millis() - previous_print > 1000)
    {
        previous_print = millis();

        if (guidewireMode)
        {
            Serial.println("MODE: GUIDEWIRE");
        }
        else
        {
            Serial.println("MODE: CATHETER");
        }
    }
}