#include <Stepper.h>

#define STEPS_PER_REV 2048  // 28BYJ-48 (기어 포함)

// ★ 핀 순서 중요 ★
// 라이브러리는 (IN1, IN3, IN2, IN4) 순서로 넣는 게 일반적
Stepper motor(STEPS_PER_REV, 2, 4, 3, 5);

int testStep = 256;   // 눈에 보이게 약 45도 정도

void setup() {
  Serial.begin(115200);
  motor.setSpeed(10);   // RPM (천천히)

  Serial.println("=== Single Motor DEBUG ===");
  Serial.println("f : forward");
  Serial.println("b : backward");
  Serial.println("1 : 1 step");
  Serial.println("r : 1 revolution");
  Serial.println("==========================");
}

void loop() {
  if (Serial.available()) {
    char cmd = Serial.read();

    switch (cmd) {

      case 'f':
        Serial.println("Forward");
        motor.step(testStep);
        break;

      case 'b':
        Serial.println("Backward");
        motor.step(-testStep);
        break;

      case '1':
        Serial.println("1 step");
        motor.step(1);
        break;

      case 'r':
        Serial.println("1 revolution");
        motor.step(STEPS_PER_REV);
        break;

      default:
        break;
    }
  }
}