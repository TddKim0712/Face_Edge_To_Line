## 펜 플로터 머신 config.py
## 2026 SIOR spring 홍보부스용
## edited: 03/05/2026


# ===============================
# Serial Configuration

SERIAL_PORT = "COM3"
SERIAL_BAUD = 115200
SERIAL_TIMEOUT = 2


# ===============================
# Camera Expectation (px)
# 카메라 입력 해상도 기대값 (디버그용)

FRAME_W_PX = 1280
FRAME_H_PX = 720


# Paper Geometry (mm)
# 실제 종이 크기 (그림이 그려질 물리 영역)

PAPER_W_MM = 260.0
PAPER_H_MM = 190.0


# 테두리 제외 공간 비율 (좌우/상하 동일, 안전 여백)
## 일단 20% 제거 후 중앙 그리기
MARGIN_RATIO = 0.20


# ===============================
# Paper Placement on Machine (mm)
# Homing 이후 기계 좌표계에서 종이 좌하단이 위치하는 좌표
PAPER_OFFSET_X_MM = 0.0
PAPER_OFFSET_Y_MM = 0.0


# Machine Workspace (mm)
MACHINE_W_MM = 300.0
MACHINE_H_MM = 220.0

# Z Axis (Servo Control)
# 서보 각도 (degree)
SERVO_PEN_UP_ANGLE = 60
SERVO_PEN_DOWN_ANGLE = 30

# Coordinate Policy
# 좌표 원점 기준
# 권장: BOTTOM_LEFT (CNC/플로터 호환성)
ORIGIN = "BOTTOM_LEFT"


# ===============================
# Kinematics (Machine parameters, 스텝핑 모터에 필요한 값들로 치환 레이어)

# 28BYJ-48 full step equivalent
STEPS_PER_REV = 4096

# 피니언 지름 (mm)
PINION_DIAMETER_MM = 12.0

# 계산된 이동거리
PINION_CIRCUM_MM = 3.141592 * PINION_DIAMETER_MM

# mm → step 변환 (기계 정확도랑 직결)
STEPS_PER_MM = STEPS_PER_REV / PINION_CIRCUM_MM

# backlash 보정 (mm)
BACKLASH_X_MM = 0.2
BACKLASH_Y_MM = 0.2
