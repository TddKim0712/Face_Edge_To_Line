/*
 *  서보 단독 테스트
 *  전원 넣으면 자동으로 UP/DOWN 반복
 *
 *  L293D 쉴드의 SERVO_1(pin 9) / SERVO_2(pin 10) 둘 다 테스트
 *  → 어느 핀에서 동작하는지 확인용
 */

#include <Servo.h>

Servo servo9;
Servo servo10;

const int UP_ANGLE   = 60;
const int DOWN_ANGLE = 30;

void setup() {
  Serial.begin(115200);

  servo9.attach(9);
  servo10.attach(10);

  Serial.println(F("=== Servo Test ==="));
  Serial.println(F("Pin 9 (SERVO_1) + Pin 10 (SERVO_2)"));
  Serial.println(F("UP=60  DOWN=30"));

  // 초기 위치
  servo9.write(UP_ANGLE);
  servo10.write(UP_ANGLE);
  delay(1000);
}

void loop() {
  Serial.println(F("[DOWN] 30 deg"));
  servo9.write(DOWN_ANGLE);
  servo10.write(DOWN_ANGLE);
  delay(1500);

  Serial.println(F("[UP] 60 deg"));
  servo9.write(UP_ANGLE);
  servo10.write(UP_ANGLE);
  delay(1500);
}
