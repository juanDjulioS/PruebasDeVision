#include <Servo.h>

const int ENCODER_PIN = 2;           // Pin ENA para el Encoder
const int MOTOR_PWM_PIN = 5;         // Salida PWM del motor
const byte OBSTACLE_SENSOR_PIN = 22;  // Pin digital utilizado para el sensor de obstáculos
const int SERVO_PIN = 9;             // Pin de señal del servo
const int START_ANGLE = 0;
const float ENCODER_PULSES_PER_REVOLUTION = 374.22;  // Número de pulsos por revolución del Encoder
volatile byte pulses = 0;

void counter() {
  pulses++;
}

class MotorEncoder {
public:
  MotorEncoder(int pwmPin, int encoderPin, float pulsesPerRevolution)
    : pwmPin(pwmPin), encoderPin(encoderPin), pulsesPerRevolution(pulsesPerRevolution),
      rpm(0), lastTime(0), sampleTime(100) {
    pinMode(pwmPin, OUTPUT);
    analogWrite(pwmPin, 0);
    pinMode(encoderPin, INPUT);
    attachInterrupt(0, counter, RISING);
  }
  
  void setSpeed(int speed) {
    analogWrite(pwmPin, speed);
  }
  
  void update() {
    unsigned long currentMillis = millis();
    if ((currentMillis - lastTime) >= sampleTime) {
      detachInterrupt(0);
      lastTime = currentMillis;
      rpm = 0.1 * (10 * pulses * (60.0 / pulsesPerRevolution)) + 0.9 * rpm;
      pulses = 0;
      attachInterrupt(0, counter, RISING);
    }
  }

  int getRPM() {
    return rpm;
  }
private:
  int pwmPin;
  int encoderPin;
  float pulsesPerRevolution;
  float rpm;
  unsigned long lastTime;
  unsigned long sampleTime;
};

class ServoMotor {
public:
  ServoMotor(int servoPin, int angle)
    : servoPin(servoPin) {
    servo.attach(servoPin);
    servo.write(angle);
  }

  void setAngle(int angle) {
    servo.write(angle);
  }
private:
  int servoPin;
  Servo servo;
};

class ObstacleSensor {
public:
  ObstacleSensor(byte sensorPin)
    : sensorPin(sensorPin), lastReadTime(0), readInterval(150), state(0) {
    pinMode(sensorPin, INPUT);
  }

  void update() {
    unsigned long currentTime = millis();
    if ((currentTime - lastReadTime) >= readInterval) {
      lastReadTime = currentTime;
      state = digitalRead(sensorPin) == LOW ? 1 : 0;
    }
  }

  int getState() {
    return state;
  }
private:
  byte sensorPin;
  unsigned long lastReadTime;
  unsigned long readInterval;
  int state;
};

MotorEncoder motor(MOTOR_PWM_PIN, ENCODER_PIN, ENCODER_PULSES_PER_REVOLUTION);
ServoMotor servo(SERVO_PIN, START_ANGLE);
ObstacleSensor obstacleSensor(OBSTACLE_SENSOR_PIN);

int angles[] = { 110, 135, 180 };  // Ángulos del servo

void setup() {
  Serial.begin(9600);
}

void loop() {
  if (Serial.available() > 0) {
    char inputString[20];
    int bytesRead = Serial.readBytesUntil('\n', inputString, sizeof(inputString) - 1);
    inputString[bytesRead] = '\0';

    char *motorString = strtok(inputString, "_");
    char *servoString = strtok(NULL, "_");  // variable que recibe lo estados del servo ( 0,1,2 )

    motor.setSpeed(atoi(motorString));

    byte servoIndex = atoi(servoString);
    if (servoIndex >= 0 && servoIndex < sizeof(angles) / sizeof(angles[0])) {
      servo.setAngle(angles[servoIndex]);
    }
  }
  obstacleSensor.update();
  motor.update();

  String msg = String(motor.getRPM()) + "_" + String(obstacleSensor.getState());  // rpm + estado del infrarrojo
  Serial.println(msg);
  delay(50);
}
