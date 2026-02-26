## 펜 플로터 머신 planning.py
## 2026 SIOR spring 홍보부스용
## edited: 02/26/2026

# Pen Plotter Route Planner
## Input: List[Stroke] (from vision.py)

# RDP
# Connected Grouping
# Path Ordering (TSP)
# Spline

## Output : List[Ordered Stroke]
## planning.py
## Path Planning Layer

import numpy as np
import cv2
from dataclasses import dataclass
from typing import List


# ---------------------------
# Data Structures
# ---------------------------

@dataclass
class Segment:
    points: np.ndarray
    start: np.ndarray
    end: np.ndarray
    length: float


@dataclass
class PlanStep:
    pen: str
    path: np.ndarray


# ---------------------------
# Utilities
# ---------------------------

def polyline_length(points):
    if len(points) < 2:
        return 0.0
    return np.sum(np.linalg.norm(points[1:] - points[:-1], axis=1))


# ---------------------------
# Strokes → Segments
# ---------------------------

def to_segments(strokes):

    segments = []

    for s in strokes:
        if len(s) < 2:
            continue

        seg = Segment(
            points=s,
            start=s[0],
            end=s[-1],
            length=polyline_length(s)
        )

        segments.append(seg)

    return segments


# ---------------------------
# Greedy Ordering
# ---------------------------

def order_segments(segments):

    if not segments:
        return []

    ordered = []
    remaining = segments.copy()

    current = remaining.pop(0)
    ordered.append(current)

    while remaining:

        last = ordered[-1].end

        distances = [
            np.linalg.norm(last - seg.start)
            for seg in remaining
        ]

        idx = int(np.argmin(distances))
        ordered.append(remaining.pop(idx))

    return ordered


# ---------------------------
# Compile Plan
# ---------------------------

def compile_plan(segments):

    plan = []

    if not segments:
        return plan

    current_pos = segments[0].start

    for seg in segments:

        if np.linalg.norm(current_pos - seg.start) > 1e-6:
            move = np.vstack([current_pos, seg.start])
            plan.append(PlanStep("UP", move))

        plan.append(PlanStep("DOWN", seg.points))

        current_pos = seg.end

    return plan


# ---------------------------
# Public API
# ---------------------------

def build_plan(strokes):

    segs = to_segments(strokes)
    ordered = order_segments(segs)
    plan = compile_plan(ordered)

    return plan


# ---------------------------
# Visualization
# ---------------------------
def render_plan(plan, canvas_size):

    h, w = canvas_size
    canvas = np.ones((h, w, 3), dtype=np.uint8) * 255

    pen_up_total = 0.0
    pen_down_total = 0.0
    step_idx = 0

    for step in plan:

        pts = step.path.astype(np.int32)

        if step.pen == "DOWN":
            cv2.polylines(canvas, [pts], False, (0, 0, 0), 2)

            # 길이 계산
            if len(step.path) > 1:
                pen_down_total += np.sum(
                    np.linalg.norm(step.path[1:] - step.path[:-1], axis=1)
                )

            # 번호 표시
            cx, cy = pts[0]
            cv2.putText(canvas,
                        str(step_idx),
                        (cx + 3, cy - 3),
                        cv2.FONT_HERSHEY_SIMPLEX,
                        0.5,
                        (0, 0, 0),
                        1)

        else:
            cv2.polylines(canvas, [pts], False, (180, 180, 180), 1)

            if len(step.path) > 1:
                pen_up_total += np.linalg.norm(step.path[1] - step.path[0])

        step_idx += 1

    cv2.putText(canvas,
                f"PenDown Length: {pen_down_total:.1f}",
                (20, 30),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.6,
                (0, 0, 0),
                2)

    cv2.putText(canvas,
                f"PenUp Length: {pen_up_total:.1f}",
                (20, 60),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.6,
                (0, 0, 0),
                2)

    print("==== Planning Statistics ====")
    print("PenDown Length:", pen_down_total)
    print("PenUp Length:", pen_up_total)
    print("Total Steps:", len(plan))

    return canvas