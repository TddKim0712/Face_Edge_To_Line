## 펜 플로터 머신 camera.py
## 2026 SIOR spring 홍보부스용
## edited: 02/26/2026

## normalize.py
## 좌표 정규화 레이어

import numpy as np
import config


def normalize_paths(paths, frame_w, frame_h):

    norm_paths = []

    paper_w = config.PAPER_W_MM
    paper_h = config.PAPER_H_MM

    margin_ratio = config.MARGIN_RATIO

    usable_w = paper_w * (1.0 - margin_ratio)
    usable_h = paper_h * (1.0 - margin_ratio)

    offset_x = config.PAPER_OFFSET_X_MM
    offset_y = config.PAPER_OFFSET_Y_MM

    for p in paths:

        if len(p) < 2:
            continue

        p = p.copy()

        # 1. px → 0~1 normalize
        p[:, 0] /= frame_w
        p[:, 1] /= frame_h

        # 2. 0~1 → usable paper mm
        p[:, 0] *= usable_w
        p[:, 1] *= usable_h

        # 3. margin 중앙 배치
        p[:, 0] += paper_w * margin_ratio * 0.5
        p[:, 1] += paper_h * margin_ratio * 0.5

        # 4. origin policy
        if config.ORIGIN == "BOTTOM_LEFT":
            p[:, 1] = paper_h - p[:, 1]

        # 5. machine offset
        p[:, 0] += offset_x
        p[:, 1] += offset_y

        norm_paths.append(p)

    return norm_paths