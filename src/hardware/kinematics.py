## 펜 플로터 머신 kinematics.py
## 2026 SIOR spring 홍보부스용
## edited: 03/05/2026

## stepping <-> physical info 
# 추후 calibration, tuning 등에 필수적으로 필요함
## mm ↔ step conversion

import config


STEPS_PER_MM = config.STEPS_PER_MM


def mm_to_steps(x_mm, y_mm):

    sx = int(round(x_mm * STEPS_PER_MM))
    sy = int(round(y_mm * STEPS_PER_MM))

    return sx, sy


def steps_to_mm(x_step, y_step):

    x_mm = x_step / STEPS_PER_MM
    y_mm = y_step / STEPS_PER_MM

    return x_mm, y_mm