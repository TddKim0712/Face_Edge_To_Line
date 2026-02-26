## 펜 플로터 머신 config.py
## 2026 SIOR spring 홍보부스용
## edited: 02/26/2026

# ===============================
# Camera Expectation (px)
# 카메라 입력 해상도 기대값 (디버그용)

FRAME_W_PX = 1280
FRAME_H_PX = 720


# ===============================
# Paper Geometry (mm)
# 실제 종이 크기 (그림이 그려질 물리 영역)

PAPER_W_MM = 260.0
PAPER_H_MM = 190.0

# 테두리 제외 비율 (좌우/상하 동일, 안전 여백)
MARGIN_RATIO = 0.20


# ===============================
# Paper Placement on Machine (mm)


# Homing 이후 기계 좌표계에서 종이 좌하단이 위치하는 좌표
PAPER_OFFSET_X_MM = 0.0
PAPER_OFFSET_Y_MM = 0.0


# ===============================
# Machine Workspace (mm)
# ===============================

MACHINE_W_MM = 300.0
MACHINE_H_MM = 220.0


# ===============================
# Coordinate Policy
# 좌표 원점 기준

# 권장: BOTTOM_LEFT (CNC/플로터 호환성)
ORIGIN = "BOTTOM_LEFT"