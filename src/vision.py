## 펜 플로터 머신 vision.py
## 2026 SIOR spring 홍보부스용
## edited: 02/26/2026

# YOLO model -> face segmentation, background removal,only needed edge detection
# pure contour extraction (minimal filtering)
# contour to vector lines

## Input:
# Adjusted Webcam live frames

# ## 과정:
# 1. 사람 클래스 (cls == 0) masking
# 2. masking 된 영역에서만 edge (Canny 기반, 저강도)
# 3. 외곽 contour 추출 (cv2.findContours)
# 4. smoothing (Savitzky–Golay Filter), already includes MovingWindow, PolyFit
# 5. RDP 기반 벡터 단순화

# ## 상태머신:
# LIVE → (space) → DRAWING
# DRAWING → (space 강제완료) → PAUSE
# PAUSE → (space) → LIVE

## output:
# List[Stroke]
# Stroke = np.array([[x,y], [x,y], ...])
# 한 프레임에서 추출된 모든 연속 선들의 벡터 목록이 아웃풋

import cv2
import numpy as np
from ultralytics import YOLO
from scipy.signal import savgol_filter
import planning
import config
from camera import Camera
import normalize


# ===============================
# Default Parameters

DEFAULT_LAPLACIAN_KSIZE = 3
DEFAULT_LAPLACIAN_THRESH = 35

DEFAULT_BLUR_KERNEL = 3

DEFAULT_MORPH_K = 3
DEFAULT_OPEN_ITERS = 1
DEFAULT_CLOSE_ITERS = 0

DEFAULT_CC_MIN_AREA = 80

DEFAULT_MIN_PATH_LEN = 40
DEFAULT_SMOOTH_WIN = 7

DEFAULT_RDP_EPS = 2

DRAW_SPEED = 8
# ===============================


def smooth_polyline(points, win):
    if len(points) < win:
        return points

    if win % 2 == 0:
        win += 1
    if win < 5:
        win = 5

    x = points[:, 0]
    y = points[:, 1]

    x_s = savgol_filter(x, win, 2)
    y_s = savgol_filter(y, win, 2)

    return np.vstack((x_s, y_s)).T


def rdp_simplify(points, eps):
    if points is None or len(points) < 3:
        return points

    cnt = points.reshape(-1, 1, 2).astype(np.float32)
    approx = cv2.approxPolyDP(cnt, eps, False)
    return approx.reshape(-1, 2).astype(np.float32)


def remove_small_components(bin_img, min_area):
    num_labels, labels, stats, _ = cv2.connectedComponentsWithStats(bin_img, connectivity=8)
    out = np.zeros_like(bin_img)

    for lab in range(1, num_labels):
        area = stats[lab, cv2.CC_STAT_AREA]
        if area >= min_area:
            out[labels == lab] = 255

    return out


def contour_paths(edge_img, min_len, smooth_win):

    contours, _ = cv2.findContours(
        edge_img,
        cv2.RETR_EXTERNAL,
        cv2.CHAIN_APPROX_NONE
    )

    paths = []

    for cnt in contours:

        if len(cnt) < min_len:
            continue

        pts = cnt.reshape(-1, 2).astype(np.float32)

        if len(pts) > 20:
            pts = smooth_polyline(pts, smooth_win)

        paths.append(pts)

    return paths


def webcam_vector():

    model = YOLO("../models/yolov8n-seg.pt")
    cam = Camera()

    cv2.namedWindow("Vector Control")

    cv2.createTrackbar("Lap KSize", "Vector Control",
                       DEFAULT_LAPLACIAN_KSIZE, 7, lambda x: None)
    cv2.createTrackbar("Lap Thresh", "Vector Control",
                       DEFAULT_LAPLACIAN_THRESH, 120, lambda x: None)

    cv2.createTrackbar("Blur Kernel", "Vector Control",
                       DEFAULT_BLUR_KERNEL, 15, lambda x: None)

    cv2.createTrackbar("Morph K", "Vector Control",
                       DEFAULT_MORPH_K, 15, lambda x: None)
    cv2.createTrackbar("Open Iters", "Vector Control",
                       DEFAULT_OPEN_ITERS, 5, lambda x: None)
    cv2.createTrackbar("Close Iters", "Vector Control",
                       DEFAULT_CLOSE_ITERS, 5, lambda x: None)

    cv2.createTrackbar("CC MinArea", "Vector Control",
                       DEFAULT_CC_MIN_AREA, 400, lambda x: None)

    cv2.createTrackbar("Min Path Len", "Vector Control",
                       DEFAULT_MIN_PATH_LEN, 250, lambda x: None)
    cv2.createTrackbar("Smooth Win", "Vector Control",
                       DEFAULT_SMOOTH_WIN, 25, lambda x: None)

    cv2.createTrackbar("RDP Eps", "Vector Control",
                       DEFAULT_RDP_EPS, 10, lambda x: None)

    mode = "LIVE"
    frozen_frame = None
    paths = []

    draw_path_idx = 0
    draw_point_idx = 0
    force_finish = False

    while True:

        if mode == "LIVE":
            frame = cam.get_frame(
                config.PAPER_W_MM,
                config.PAPER_H_MM
            )
            if frame is None:
                break

            debug = frame.copy()
            h0, w0 = debug.shape[:2]
            cv2.putText(debug,
                        f"Crop Size: {w0} x {h0}",
                        (20, 30),
                        cv2.FONT_HERSHEY_SIMPLEX,
                        0.8,
                        (0, 0, 255),
                        2)
            cv2.imshow("Crop Debug", debug)

        else:
            frame = frozen_frame.copy()

        h, w, _ = frame.shape

        blur_k = cv2.getTrackbarPos("Blur Kernel", "Vector Control")
        cc_min_area = cv2.getTrackbarPos("CC MinArea", "Vector Control")
        min_len = cv2.getTrackbarPos("Min Path Len", "Vector Control")
        smooth_win = cv2.getTrackbarPos("Smooth Win", "Vector Control")
        rdp_eps = cv2.getTrackbarPos("RDP Eps", "Vector Control")

        if blur_k % 2 == 0:
            blur_k += 1
        if blur_k < 1:
            blur_k = 1

        results = model(frame, verbose=False)[0]
        combined_mask = np.zeros((h, w), dtype=np.uint8)

        if results.masks is not None:
            for i, cls in enumerate(results.boxes.cls):
                if int(cls) == 0:
                    mask = results.masks.data[i].cpu().numpy()
                    mask = cv2.resize(mask, (w, h))
                    mask = (mask > 0.5).astype(np.uint8) * 255
                    combined_mask = cv2.bitwise_or(combined_mask, mask)

        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        gray = cv2.GaussianBlur(gray, (blur_k, blur_k), 0)

        edges = cv2.Canny(gray, 50, 120)
        edges_person = cv2.bitwise_and(edges, edges, mask=combined_mask)
        edges_person = remove_small_components(edges_person, cc_min_area)

        sketch = np.ones((h, w), dtype=np.uint8) * 255
        sketch[edges_person > 0] = 0
        sketch_color = cv2.cvtColor(sketch, cv2.COLOR_GRAY2BGR)

        vector_canvas = np.ones((h, w, 3), dtype=np.uint8) * 255

        if mode in ["DRAWING", "PAUSE"]:

            total_paths = len(paths)

            if force_finish:
                draw_path_idx = total_paths
                draw_point_idx = 0
                force_finish = False
                mode = "PAUSE"

            for i in range(draw_path_idx):
                cv2.polylines(vector_canvas,
                              [paths[i].astype(np.int32)],
                              False,
                              (0, 0, 0),
                              2)

            if mode == "DRAWING" and draw_path_idx < total_paths:

                p = paths[draw_path_idx]

                if draw_point_idx >= len(p):
                    draw_point_idx = len(p) - 1

                cx, cy = p[draw_point_idx].astype(int)

                cv2.putText(vector_canvas,
                            str(draw_path_idx + 1),
                            (cx + 5, cy - 5),
                            cv2.FONT_HERSHEY_SIMPLEX,
                            0.5,
                            (0, 0, 0),
                            1)

                cv2.putText(vector_canvas,
                            f"Total Paths: {total_paths}",
                            (20, 30),
                            cv2.FONT_HERSHEY_SIMPLEX,
                            0.8,
                            (0, 0, 0),
                            2)

                if draw_point_idx < len(p) - 1:
                    pts = p[:draw_point_idx].astype(np.int32)

                    if len(pts) > 1:
                        cv2.polylines(vector_canvas,
                                      [pts],
                                      False,
                                      (150, 150, 150),
                                      2)

                    draw_point_idx += DRAW_SPEED
                else:
                    draw_path_idx += 1
                    draw_point_idx = 0

            if draw_path_idx >= total_paths:
                mode = "PAUSE"

        cv2.imshow("Camera", frame)
        cv2.imshow("Sketch", sketch_color)
        cv2.imshow("Vector", vector_canvas)

        key = cv2.waitKey(1) & 0xFF

        if key == 27 or key == ord("q"):
            break

        if key == ord(" "):

            if mode == "LIVE":

                frozen_frame = frame.copy()

                raw_paths = contour_paths(edges_person, min_len, smooth_win)

                simplified = []
                for p in raw_paths:
                    p2 = rdp_simplify(p, rdp_eps)
                    if p2 is not None and len(p2) >= 2:
                        simplified.append(p2)

                paths = simplified

                norm_paths = normalize.normalize_paths(paths, w, h)

                preview_paths = []
                for p in norm_paths:
                    p2 = p.copy()

                    if config.ORIGIN == "BOTTOM_LEFT":
                        p2[:, 1] = config.PAPER_H_MM - p2[:, 1]

                    p2[:, 0] = (p2[:, 0] / config.PAPER_W_MM) * w
                    p2[:, 1] = (p2[:, 1] / config.PAPER_H_MM) * h

                    preview_paths.append(p2)

                plan_preview = planning.build_plan(preview_paths)
                preview = planning.render_plan(plan_preview, (h, w))

                cv2.imshow("Normalize Preview (MM)", preview)
                cv2.waitKey(0)

                plan = planning.build_plan(norm_paths)

                ordered_paths = [step.path for step in plan_preview if step.pen == "DOWN"]
                paths = ordered_paths

                mode = "DRAWING"
                draw_path_idx = 0
                draw_point_idx = 1
                force_finish = False

            elif mode == "DRAWING":
                force_finish = True

            elif mode == "PAUSE":
                mode = "LIVE"

    cam.release()
    cv2.destroyAllWindows()

    return paths