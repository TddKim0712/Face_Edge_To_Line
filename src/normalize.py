## 펜 플로터 머신 camera.py
## 2026 SIOR spring 홍보부스용
## edited: 02/26/2026

## normalize.py
## 좌표 정규화 레이어 

# 주석 추가: 03/05/2026
#  Camera-PC layer to real Hardware physical layer

## px 좌표 → mm 좌표 변환

import numpy as np
import config


def normalize_paths(paths, frame_w, frame_h):
    """
    Input
        paths : vision 단계에서 나온 px 좌표
        frame_w, frame_h : 카메라 프레임 크기

    Output
        norm_paths : mm 좌표 (기계 좌표계 기준)
    """

    norm_paths = []

    # -----------------------------
    # Paper geometry
    # -----------------------------
    paper_w = config.PAPER_W_MM
    paper_h = config.PAPER_H_MM

    # 실제 사용 영역 (margin 제외)
    margin_ratio = config.MARGIN_RATIO
    usable_w = paper_w * (1.0 - margin_ratio)
    usable_h = paper_h * (1.0 - margin_ratio)

    # machine 좌표계에서 종이 위치
    offset_x = config.PAPER_OFFSET_X_MM
    offset_y = config.PAPER_OFFSET_Y_MM

    for p in paths:

        if len(p) < 2:
            continue

        p = p.copy()

        # ------------------------------------------------
        # 1. pixel → normalized (0 ~ 1)
        # ------------------------------------------------
        p[:, 0] /= frame_w
        p[:, 1] /= frame_h

        # ------------------------------------------------
        # 2. normalized → paper mm
        # ------------------------------------------------
        p[:, 0] *= usable_w
        p[:, 1] *= usable_h

        # ------------------------------------------------
        # 3. margin 중앙 정렬
        # ------------------------------------------------
        p[:, 0] += paper_w * margin_ratio * 0.5
        p[:, 1] += paper_h * margin_ratio * 0.5

        # ------------------------------------------------
        # 4. origin 정책 적용
        # OpenCV : top-left
        # Plotter: bottom-left
        # ------------------------------------------------
        if config.ORIGIN == "BOTTOM_LEFT":
            p[:, 1] = paper_h - p[:, 1]

        # ------------------------------------------------
        # 5. machine offset 적용
        # homing 이후 종이 위치 보정
        # ------------------------------------------------
        p[:, 0] += offset_x
        p[:, 1] += offset_y

        norm_paths.append(p)

    return norm_paths