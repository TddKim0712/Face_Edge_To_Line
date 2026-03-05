/*
 * ================================================================
 *  펜 플로터 아두이노 펌웨어
 *  모터   : 28BYJ-48 (5V DC 스텝모터) × 3 + ULN2003 드라이버
 *  통신   : USB Serial G-code @ 115200 baud
 *  좌표계 : mm, 절대 좌표 (G21 / G90)
 * ================================================================
 *
 *  핀 연결 (ULN2003  IN1~IN4)
 *  ┌──────┬──────────────────────────┐
 *  │  X축 │ IN1=D2  IN2=D3  IN3=D4  IN4=D5  │
 *  │  Y축 │ IN1=D6  IN2=D7  IN3=D8  IN4=D9  │
 *  │  Z축 │ IN1=D10 IN2=D11 IN3=D12 IN4=D13 │
 *  └──────┴──────────────────────────┘
 *  ※ D10~D13은 Uno SPI 핀과 겹치지만 SPI 미사용이므로 OK
 *
 *  G-code 지원
 *  ─────────────────────────────────
 *  G0  X[n] Y[n] Z[n]      고속 이동 (펜 이동)
 *  G1  X[n] Y[n] Z[n] F[n] 드로잉 이동 (F: mm/min)
 *  G21                      mm 단위 (기본값, 파싱만)
 *  G90                      절대 좌표 (기본값, 파싱만)
 *  M30                      프로그램 종료 / 원점 복귀
 *
 *  통신 프로토콜: 명령 수신 → 실행 → "ok\n" 응답
 *  Python이 "ok"를 받은 후 다음 줄을 전송합니다.
 *
 * ================================================================
 *  기계 파라미터 (캘리브레이션 필요)
 * ================================================================
 *  28BYJ-48 하프스텝: 4096 steps/rev
 *  GT2 타이밍벨트 + 20T 풀리: 20 × 2mm = 40mm/rev
 *  → STEPS_PER_MM = 4096 / 40 = 102.4
 *
 *  다른 구성이라면:
 *    리드스크루 M5 (0.8mm/rev): 4096 / 0.8 = 5120  steps/mm
 *    리드스크루 T8 (8mm/rev)  : 4096 / 8   =  512  steps/mm
 *
 *  28BYJ-48 속도 한계:
 *    최대 약 900 steps/sec (풀 토크), ~1500 steps/sec (무부하)
 *    102.4 steps/mm 기준 → 안전 최대속도 ≈ 900/102.4 = 8.8 mm/s ≈ 528 mm/min
 *    Python에서 feedrate=800 으로 설정하면 딜레이 클램핑으로 안전하게 동작
 */

// ================================================================
//  핀 설정
// ================================================================

const uint8_t MOTOR_X[4] = {2,  3,  4,  5 };
const uint8_t MOTOR_Y[4] = {6,  7,  8,  9 };
const uint8_t MOTOR_Z[4] = {10, 11, 12, 13};

// ================================================================
//  기계 상수
// ================================================================

const float SPM_X = 102.4f;   // steps/mm  (GT2 + 20T 풀리 기준)
const float SPM_Y = 102.4f;   // steps/mm
const float SPM_Z = 200.0f;   // steps/mm  (펜 리프트 메커니즘에 따라 조정)

// 모터가 반대 방향으로 움직이면 아래 값을 -1로 바꾸세요
const int DIR_X = 1;
const int DIR_Y = 1;
const int DIR_Z = 1;

// ================================================================
//  속도 설정 (microseconds / step)
// ================================================================

const unsigned long STEP_US_G0  = 800;   // G0 고속 이동
const unsigned long STEP_US_MIN = 700;   // 최고 속도 한계 (28BYJ-48 보호)
const unsigned long STEP_US_MAX = 3000;  // 최저 속도 한계
const unsigned long STEP_US_Z   = 1500;  // Z축 고정 속도

// ================================================================
//  하프스텝 시퀀스 (28BYJ-48)
//  코일 순서: IN1, IN2, IN3, IN4
// ================================================================

const uint8_t HALF_STEP[8][4] = {
  {1, 0, 0, 0},  // 0
  {1, 1, 0, 0},  // 1
  {0, 1, 0, 0},  // 2
  {0, 1, 1, 0},  // 3
  {0, 0, 1, 0},  // 4
  {0, 0, 1, 1},  // 5
  {0, 0, 0, 1},  // 6
  {1, 0, 0, 1},  // 7
};

// ================================================================
//  상태 변수
// ================================================================

long  cur_x = 0, cur_y = 0, cur_z = 0;  // 현재 위치 (steps)
int8_t idx_x = 0, idx_y = 0, idx_z = 0; // 하프스텝 인덱스

float tgt_x = 0.0f, tgt_y = 0.0f, tgt_z = 0.0f; // 현재 목표 mm (누적)

unsigned long g1_step_us = 1200;  // G1 드로잉 딜레이 (feedrate에서 계산)

// ================================================================
//  모터 제어 기본 함수
// ================================================================

void applyCoils(const uint8_t pins[4], int8_t idx) {
  const uint8_t *row = HALF_STEP[(uint8_t)(idx & 7)];
  for (int i = 0; i < 4; i++) {
    digitalWrite(pins[i], row[i]);
  }
}

void releaseCoils(const uint8_t pins[4]) {
  for (int i = 0; i < 4; i++) {
    digitalWrite(pins[i], LOW);
  }
}

// 단일 스텝 (dir: +1 또는 -1, 방향 보정 포함)
inline void stepX(int dir) {
  idx_x = (int8_t)((idx_x + dir * DIR_X + 8) & 7);
  applyCoils(MOTOR_X, idx_x);
}
inline void stepY(int dir) {
  idx_y = (int8_t)((idx_y + dir * DIR_Y + 8) & 7);
  applyCoils(MOTOR_Y, idx_y);
}
inline void stepZ(int dir) {
  idx_z = (int8_t)((idx_z + dir * DIR_Z + 8) & 7);
  applyCoils(MOTOR_Z, idx_z);
}

// ================================================================
//  Z축 독립 이동 (펜 up/down)
//  완료 후 코일 해제 (Z는 위치 유지 불필요, 과열 방지)
// ================================================================

void moveZ(long target_steps) {
  int dir = (target_steps > cur_z) ? 1 : -1;
  while (cur_z != target_steps) {
    stepZ(dir);
    cur_z += dir;
    delayMicroseconds(STEP_US_Z);
  }
  releaseCoils(MOTOR_Z);
}

// ================================================================
//  XY 동시 이동 – Bresenham 직선 보간
//  두 축을 동시에 구동해 직선 경로를 유지합니다.
// ================================================================

void moveXY(long tx, long ty, unsigned long step_us) {
  long dx = abs(tx - cur_x);
  long dy = abs(ty - cur_y);
  if (dx == 0 && dy == 0) return;

  int sx = (tx > cur_x) ? 1 : -1;
  int sy = (ty > cur_y) ? 1 : -1;

  long err = dx - dy;

  while (cur_x != tx || cur_y != ty) {
    long e2 = 2L * err;

    if (e2 > -dy && cur_x != tx) {
      err -= dy;
      stepX(sx);
      cur_x += sx;
    }
    if (e2 < dx && cur_y != ty) {
      err += dx;
      stepY(sy);
      cur_y += sy;
    }
    delayMicroseconds(step_us);
  }
}

// ================================================================
//  Feedrate → step 딜레이 변환
//  F 단위: mm/min
// ================================================================

unsigned long feedrateToDelay(float f_mm_min) {
  if (f_mm_min <= 0.0f) return STEP_US_MAX;
  // X 기준 steps/sec 계산 (대각선 이동 시 실제 속도는 조금 다름)
  float steps_per_sec = (f_mm_min / 60.0f) * SPM_X;
  unsigned long us = (unsigned long)(1000000.0f / steps_per_sec);
  return constrain(us, STEP_US_MIN, STEP_US_MAX);
}

// ================================================================
//  G-code 파서 유틸리티
// ================================================================

// 문자 키 다음의 float 값 추출 ("X-12.5" → -12.5)
float extractParam(const char *line, char key) {
  const char *p = strchr(line, key);
  if (!p) return NAN;
  return (float)atof(p + 1);
}

bool hasParam(const char *line, char key) {
  return strchr(line, key) != nullptr;
}

// ================================================================
//  G-code 한 줄 처리
// ================================================================

void processLine(char *line) {
  // 대문자 변환 + 개행 제거
  for (int i = 0; line[i]; i++) {
    if (line[i] == '\r' || line[i] == '\n') { line[i] = '\0'; break; }
    line[i] = (char)toupper((unsigned char)line[i]);
  }

  // 인라인 주석 제거
  char *sc = strchr(line, ';');
  if (sc) *sc = '\0';

  // 빈 줄
  if (strlen(line) == 0) {
    Serial.println(F("ok"));
    return;
  }

  // 파라미터 파싱
  bool hx = hasParam(line, 'X');
  bool hy = hasParam(line, 'Y');
  bool hz = hasParam(line, 'Z');
  bool hf = hasParam(line, 'F');

  if (hx) tgt_x = extractParam(line, 'X');
  if (hy) tgt_y = extractParam(line, 'Y');
  if (hz) tgt_z = extractParam(line, 'Z');
  if (hf) g1_step_us = feedrateToDelay(extractParam(line, 'F'));

  // 명령 번호 파싱 (G0/G00/G1/G01 등 모두 처리)
  if (line[0] == 'G') {
    int gnum = atoi(line + 1);

    if (gnum == 0 || gnum == 1) {
      long tx = hx ? (long)(tgt_x * SPM_X) : cur_x;
      long ty = hy ? (long)(tgt_y * SPM_Y) : cur_y;
      long tz = hz ? (long)(tgt_z * SPM_Z) : cur_z;

      unsigned long step_us = (gnum == 0) ? STEP_US_G0 : g1_step_us;

      // 펜 올리기 → XY 이동 → 펜 내리기 순서
      if (hz && tz > cur_z) moveZ(tz);      // 올리기 먼저
      if (hx || hy)         moveXY(tx, ty, step_us);
      if (hz && tz <= cur_z) moveZ(tz);     // 내리기 나중

      Serial.println(F("ok"));
    }
    else if (gnum == 21 || gnum == 90) {
      // mm / 절대좌표 – 기본값이므로 파싱만
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
      // 프로그램 종료: 펜 올리고 원점으로
      long pen_up = (long)(5.0f * SPM_Z);
      moveZ(pen_up);
      moveXY(0, 0, STEP_US_G0);
      releaseCoils(MOTOR_X);
      releaseCoils(MOTOR_Y);
      releaseCoils(MOTOR_Z);
      Serial.println(F("ok; DONE"));
    }
    else {
      Serial.print(F("error: unknown M"));
      Serial.println(mnum);
    }
  }
  else {
    Serial.print(F("error: unknown cmd: "));
    Serial.println(line);
  }
}

// ================================================================
//  시리얼 수신 버퍼
// ================================================================

#define BUF_SIZE 80
char  serial_buf[BUF_SIZE];
uint8_t buf_len = 0;

// ================================================================
//  setup / loop
// ================================================================

void setup() {
  Serial.begin(115200);

  // 모든 핀 OUTPUT 설정
  for (int i = 0; i < 4; i++) {
    pinMode(MOTOR_X[i], OUTPUT);
    pinMode(MOTOR_Y[i], OUTPUT);
    pinMode(MOTOR_Z[i], OUTPUT);
  }

  // 초기 펜 올리기 (5mm)
  long init_z = (long)(5.0f * SPM_Z);
  moveZ(init_z);

  Serial.println(F("Pen Plotter Ready"));
  Serial.print(F("SPM_X="));  Serial.print(SPM_X);
  Serial.print(F(" SPM_Y=")); Serial.print(SPM_Y);
  Serial.print(F(" SPM_Z=")); Serial.println(SPM_Z);
}

void loop() {
  // 시리얼 수신 (줄 단위 버퍼링)
  while (Serial.available()) {
    char c = (char)Serial.read();

    if (c == '\n' || c == '\r') {
      if (buf_len > 0) {
        serial_buf[buf_len] = '\0';
        processLine(serial_buf);
        buf_len = 0;
      }
    } else if (buf_len < BUF_SIZE - 1) {
      serial_buf[buf_len++] = c;
    }
    // buf_len >= BUF_SIZE-1 이면 나머지 문자 무시 (overflow 방지)
  }
}
