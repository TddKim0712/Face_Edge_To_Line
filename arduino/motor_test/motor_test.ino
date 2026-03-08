/*
 *  모터 자동 테스트 (전원 넣으면 바로 동작)
 *  서보 없음, 시리얼 명령 불필요
 *
 *  L293D Motor Shield
 *    M1+M2 (포트 1) : NEMA (A축)
 *    M3+M4 (포트 2) : 28BYJ-48 (R축)
 *
 *  동작 순서:
 *    1) R축만 전진 → 후진
 *    2) A축만 전진 → 후진
 *    3) R+A 동시 이동
 *    4) 모터 해제
 *    5) 2초 후 반복
 */

#include <AFMotor.h>

AF_Stepper thetaMotor(200, 1);   // NEMA, 포트 1
AF_Stepper rMotor(2048, 2);      // 28BYJ-48, 포트 2

const int TEST_STEPS_R = 500;    // R축 테스트 스텝 수
const int TEST_STEPS_A = 200;    // A축 테스트 스텝 수
const unsigned long STEP_US = 1200;

void moveMotor(AF_Stepper &motor, int steps, int dir, unsigned long us) {
  for (int i = 0; i < steps; i++) {
    motor.onestep(dir, INTERLEAVE);
    delayMicroseconds(us);
  }
}

void setup() {
  Serial.begin(115200);
  thetaMotor.setSpeed(30);
  rMotor.setSpeed(30);
  Serial.println(F("=== Motor Auto Test ==="));
}

void loop() {

  // 1) R축 전진
  Serial.println(F("[R] FORWARD..."));
  moveMotor(rMotor, TEST_STEPS_R, FORWARD, STEP_US);
  delay(500);

  // R축 후진
  Serial.println(F("[R] BACKWARD..."));
  moveMotor(rMotor, TEST_STEPS_R, BACKWARD, STEP_US);
  delay(500);

  // 2) A축 전진
  Serial.println(F("[A] FORWARD..."));
  moveMotor(thetaMotor, TEST_STEPS_A, FORWARD, STEP_US);
  delay(500);

  // A축 후진
  Serial.println(F("[A] BACKWARD..."));
  moveMotor(thetaMotor, TEST_STEPS_A, BACKWARD, STEP_US);
  delay(500);

  // 3) 동시 이동 (수동 Bresenham)
  Serial.println(F("[R+A] simultaneous..."));
  int r = 0, a = 0;
  int tr = TEST_STEPS_R, ta = TEST_STEPS_A;
  long err = tr - ta;
  while (r < tr || a < ta) {
    long e2 = 2L * err;
    if (e2 > -ta && r < tr) {
      err -= ta;
      rMotor.onestep(FORWARD, INTERLEAVE);
      r++;
    }
    if (e2 < tr && a < ta) {
      err += tr;
      thetaMotor.onestep(FORWARD, INTERLEAVE);
      a++;
    }
    delayMicroseconds(STEP_US);
  }
  delay(500);

  // 복귀
  Serial.println(F("[R+A] return..."));
  r = 0; a = 0;
  err = tr - ta;
  while (r < tr || a < ta) {
    long e2 = 2L * err;
    if (e2 > -ta && r < tr) {
      err -= ta;
      rMotor.onestep(BACKWARD, INTERLEAVE);
      r++;
    }
    if (e2 < tr && a < ta) {
      err += tr;
      thetaMotor.onestep(BACKWARD, INTERLEAVE);
      a++;
    }
    delayMicroseconds(STEP_US);
  }

  // 4) 해제
  rMotor.release();
  thetaMotor.release();
  Serial.println(F("--- cycle done, wait 2s ---"));
  delay(2000);
}
