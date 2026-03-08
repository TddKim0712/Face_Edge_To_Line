/*
 * ================================================================
 *  극좌표 펜 플로터 펌웨어 (Polar Plotter)
 * ================================================================
 *
 *  구조: 레코드판 방식
 *    - 원형 종이가 회전 (θ축)
 *    - 펜이 중심에서 직선으로만 이동 (r축)
 *    - 펜 up/down은 서보모터
 *
 *  하드웨어
 *  ──────────────────────────────────────────────────
 *   L293D Motor Shield
 *     M1 + M2 (포트 1) : NEMA 스텝모터 (종이 회전, θ)
 *     M3 + M4 (포트 2) : 28BYJ-48     (펜 직선, r)
 *     SERVO_2 (pin 10) : 서보모터     (펜 up/down)
 *
 *  G-code 축 매핑
 *  ──────────────────────────────────────────────────
 *   R = 반지름  (mm, 중심에서의 거리)  → 28BYJ-48
 *   A = 각도   (degrees)             → NEMA
 *   Z = 펜     (mm, >1 → up, ≤1 → down) → 서보
 *
 *  통신: Serial 115200, 명령 후 "ok" 응답
 *
 *  라이브러리 설치 필요:
 *    Arduino IDE → 라이브러리 매니저 → "Adafruit Motor Shield" v1 검색 → 설치
 */

#include <AFMotor.h>
#include <Servo.h>

// ================================================================
//  모터 객체
// ================================================================

// θ축: NEMA 스텝모터, 포트 1 (M1+M2), 200 full-steps/rev
AF_Stepper thetaMotor(200, 1);

// r축: 28BYJ-48, 포트 2 (M3+M4), 2048 full-steps/rev
AF_Stepper rMotor(2048, 2);

// Z축: 서보모터, SERVO_2 핀
Servo penServo;

// ================================================================
//  기계 파라미터 (캘리브레이션 필요)
// ================================================================

// 서보
const int SERVO_PIN       = 10;    // L293D 쉴드의 SERVO_2
const int PEN_UP_ANGLE    = 60;    // 펜 올림 각도
const int PEN_DOWN_ANGLE  = 30;    // 펜 내림 각도

// NEMA (θ축) — INTERLEAVE 모드: 400 steps/rev
//   400 / 360 = 1.111 steps/degree
const float STEPS_PER_DEG_A = 400.0f / 360.0f;

// 28BYJ-48 (r축) — INTERLEAVE 모드: 4096 steps/rev
//   피니언 지름 12mm → 둘레 = π × 12 = 37.7mm
//   4096 / 37.7 = 108.7 steps/mm
const float PINION_CIRCUM  = 3.14159f * 12.0f;
const float STEPS_PER_MM_R = 4096.0f / PINION_CIRCUM;

// 방향 반전 (모터가 반대로 돌면 -1)
const int DIR_R = 1;
const int DIR_A = 1;

// 속도
const unsigned long STEP_US_G0  = 800;   // G0 고속 이동
const unsigned long STEP_US_MIN = 500;
const unsigned long STEP_US_MAX = 4000;

// ================================================================
//  상태 변수
// ================================================================

long cur_r = 0;    // 현재 r 위치 (steps)
long cur_a = 0;    // 현재 θ 위치 (steps)

float tgt_r = 0.0f;  // 목표 r (mm) — G-code에서 누적
float tgt_a = 0.0f;  // 목표 θ (degrees)

bool pen_is_down = false;
int  path_count  = 0;
int  point_count = 0;

unsigned long g1_step_us = 1500;

// ================================================================
//  서보 제어 (펜 up/down)
// ================================================================

void penUp() {
  penServo.write(PEN_UP_ANGLE);
  pen_is_down = false;
  delay(250);   // 서보 이동 완료 대기
}

void penDown() {
  penServo.write(PEN_DOWN_ANGLE);
  pen_is_down = true;
  delay(250);
}

// ================================================================
//  R-A 동시 이동 (Bresenham 보간)
//  두 모터를 동시에 구동해 직선/곡선 보간
// ================================================================

void moveRA(long tr, long ta, unsigned long delay_us) {
  long dr = abs(tr - cur_r);
  long da = abs(ta - cur_a);
  if (dr == 0 && da == 0) return;

  // AFMotor 방향 상수
  int dir_r_af = ((tr > cur_r) == (DIR_R > 0)) ? FORWARD : BACKWARD;
  int dir_a_af = ((ta > cur_a) == (DIR_A > 0)) ? FORWARD : BACKWARD;

  int step_r = (tr > cur_r) ? 1 : -1;
  int step_a = (ta > cur_a) ? 1 : -1;

  long err = dr - da;

  while (cur_r != tr || cur_a != ta) {
    long e2 = 2L * err;

    if (e2 > -da && cur_r != tr) {
      err -= da;
      rMotor.onestep(dir_r_af, INTERLEAVE);
      cur_r += step_r;
    }
    if (e2 < dr && cur_a != ta) {
      err += dr;
      thetaMotor.onestep(dir_a_af, INTERLEAVE);
      cur_a += step_a;
    }

    delayMicroseconds(delay_us);
  }
}

// ================================================================
//  Feedrate → step delay 변환
// ================================================================

unsigned long feedToDelay(float f_mm_min) {
  if (f_mm_min <= 0.0f) return STEP_US_MAX;
  float sps = (f_mm_min / 60.0f) * STEPS_PER_MM_R;
  return (unsigned long)constrain((long)(1000000.0f / sps), STEP_US_MIN, STEP_US_MAX);
}

// ================================================================
//  G-code 파서
// ================================================================

float getParam(const char *line, char key) {
  const char *p = strchr(line, key);
  return p ? (float)atof(p + 1) : NAN;
}

bool hasKey(const char *line, char key) {
  return strchr(line, key) != nullptr;
}

void processLine(char *line) {
  // 대문자 변환 + 개행 제거
  for (int i = 0; line[i]; i++) {
    if (line[i] == '\r' || line[i] == '\n') { line[i] = '\0'; break; }
    line[i] = (char)toupper((unsigned char)line[i]);
  }

  // 주석 제거
  char *sc = strchr(line, ';');
  if (sc) *sc = '\0';
  if (!strlen(line)) { Serial.println(F("ok")); return; }

  // 파라미터 파싱
  bool hr = hasKey(line, 'R');
  bool ha = hasKey(line, 'A');
  bool hz = hasKey(line, 'Z');
  bool hf = hasKey(line, 'F');

  if (hr) tgt_r = getParam(line, 'R');
  if (ha) tgt_a = getParam(line, 'A');
  if (hf) g1_step_us = feedToDelay(getParam(line, 'F'));

  if (line[0] == 'G') {
    int gnum = atoi(line + 1);

    if (gnum == 0 || gnum == 1) {
      unsigned long delay_us = (gnum == 0) ? STEP_US_G0 : g1_step_us;

      // ── Z (펜 up/down) ─────────────────────────────────────
      if (hz) {
        float z_val = getParam(line, 'Z');
        bool want_up = (z_val > 1.0f);

        if (want_up && pen_is_down) {
          penUp();
          Serial.print(F("▲ PEN UP   [Path "));
          Serial.print(path_count);
          Serial.print(F(" 완료] pt "));
          Serial.println(point_count);
        }
        else if (!want_up && !pen_is_down) {
          penDown();
          path_count++;
          point_count = 0;
          Serial.print(F("▼ PEN DOWN [Path "));
          Serial.print(path_count);
          Serial.println(F("]"));
        }
      }

      // ── R, A (모터 이동) ───────────────────────────────────
      if (hr || ha) {
        long tr = (long)(tgt_r * STEPS_PER_MM_R);
        long ta = (long)(tgt_a * STEPS_PER_DEG_A);
        moveRA(tr, ta, delay_us);

        if (pen_is_down) {
          point_count++;
        }
      }

      Serial.println(F("ok"));
    }
    else if (gnum == 21 || gnum == 90) {
      Serial.println(F("ok"));
    }
    else {
      Serial.print(F("error: unknown G"));
      Serial.println(gnum);
    }
  }
  else if (line[0] == 'M') {
    int mnum = atoi(line + 1);

    if (mnum == 30) {
      penUp();
      moveRA(0, 0, STEP_US_G0);
      rMotor.release();
      thetaMotor.release();
      Serial.println(F("========================================"));
      Serial.print(F("  완료: 총 "));
      Serial.print(path_count);
      Serial.println(F("개 경로"));
      Serial.println(F("========================================"));
      Serial.println(F("ok; DONE"));
    }
    else {
      Serial.print(F("error: unknown M"));
      Serial.println(mnum);
    }
  }
  else {
    Serial.print(F("error: unknown: "));
    Serial.println(line);
  }
}

// ================================================================
//  시리얼 버퍼
// ================================================================

#define BUF_SIZE 80
char    sbuf[BUF_SIZE];
uint8_t slen = 0;

// ================================================================
//  setup / loop
// ================================================================

void setup() {
  Serial.begin(115200);

  penServo.attach(SERVO_PIN);
  penUp();

  // AFMotor 속도 설정 (step() 함수용, onestep()에는 영향 없음)
  thetaMotor.setSpeed(30);
  rMotor.setSpeed(30);

  Serial.println(F("========================================"));
  Serial.println(F("  Polar Plotter Ready"));
  Serial.println(F("  R=28BYJ-48(M3+M4)  A=NEMA(M1+M2)"));
  Serial.print(F("  SPM_R="));   Serial.print(STEPS_PER_MM_R, 1);
  Serial.print(F("  SPD_A="));   Serial.println(STEPS_PER_DEG_A, 3);
  Serial.print(F("  Servo pin=")); Serial.print(SERVO_PIN);
  Serial.print(F("  UP="));      Serial.print(PEN_UP_ANGLE);
  Serial.print(F("  DOWN="));    Serial.println(PEN_DOWN_ANGLE);
  Serial.println(F("========================================"));
  Serial.println(F("ready"));
}

void loop() {
  while (Serial.available()) {
    char c = (char)Serial.read();
    if (c == '\n' || c == '\r') {
      if (slen > 0) {
        sbuf[slen] = '\0';
        processLine(sbuf);
        slen = 0;
      }
    } else if (slen < BUF_SIZE - 1) {
      sbuf[slen++] = c;
    }
  }
}
