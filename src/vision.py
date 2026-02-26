## 펜 플로터 머신 vision.py
## 2026 SIOR spring 홍보부스용
## edited: 02/26/2026

# YOLO model -> face segmentation, background removal,edge detection
# edge to vector lines

## Input:
# Webcam live frames

# ## 과정:
# 1. 사람 클래스 (cls == 0) masking
# 2. masking 된 영역에서만 edge
# 3. Skeleton Thinning (1 pixel 두께로 선 만들기)
# 4. Endpoint Tracing (1개의 neighbor 탐색 후 방향 따라가기), branch에서는 dot product로 직진 우선
# 5. smoothing (Savitzky–Golay Filter), already includes MovingWindow, PolyFit
#
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


DRAW_SPEED = 8


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


def skeleton_paths(edge_img, min_len, smooth_win):

    skel = cv2.ximgproc.thinning(edge_img)

    h, w = skel.shape
    visited = np.zeros_like(skel, dtype=bool)
    paths = []

    def neighbors(y, x):
        pts = []
        for dy in [-1, 0, 1]:
            for dx in [-1, 0, 1]:
                if dy == 0 and dx == 0:
                    continue
                ny, nx = y + dy, x + dx
                if 0 <= ny < h and 0 <= nx < w and skel[ny, nx] > 0:
                    pts.append((ny, nx))
        return pts

    endpoints = []
    for y in range(h):
        for x in range(w):
            if skel[y, x] > 0:
                if len(neighbors(y, x)) == 1:
                    endpoints.append((y, x))

    for sy, sx in endpoints:

        if visited[sy, sx]:
            continue

        path = []
        cy, cx = sy, sx
        prev_dir = None

        while True:

            visited[cy, cx] = True
            path.append((cx, cy))

            nbs = neighbors(cy, cx)
            candidates = [(ny, nx) for ny, nx in nbs if not visited[ny, nx]]

            if not candidates:
                break

            if prev_dir is not None:
                best = None
                best_dot = -1e9
                for ny, nx in candidates:
                    dy = ny - cy
                    dx = nx - cx
                    dot = dx * prev_dir[0] + dy * prev_dir[1]
                    if dot > best_dot:
                        best_dot = dot
                        best = (ny, nx)
                ny, nx = best
            else:
                ny, nx = candidates[0]

            prev_dir = (nx - cx, ny - cy)
            cy, cx = ny, nx

        if len(path) > min_len:
            pts = np.array(path, dtype=np.float32)
            pts = smooth_polyline(pts, smooth_win)
            paths.append(pts)

    return paths


def webcam_vector():

    model = YOLO("../models/yolov8n-seg.pt")
    cap = cv2.VideoCapture(0)

    if not cap.isOpened():
        print("Camera open failed")
        return

    cv2.namedWindow("Vector Control")
    cv2.createTrackbar("Canny Low", "Vector Control", 50, 200, lambda x: None)
    cv2.createTrackbar("Canny High", "Vector Control", 120, 300, lambda x: None)
    cv2.createTrackbar("Blur Kernel", "Vector Control", 5, 15, lambda x: None)
    cv2.createTrackbar("Min Path Len", "Vector Control", 40, 200, lambda x: None)
    cv2.createTrackbar("Smooth Win", "Vector Control", 9, 25, lambda x: None)

    mode = "LIVE"
    frozen_frame = None
    paths = []

    draw_path_idx = 0
    draw_point_idx = 0
    force_finish = False

    while True:

        if mode == "LIVE":
            ret, frame = cap.read()
            if not ret:
                break
        else:
            frame = frozen_frame.copy()

        h, w, _ = frame.shape

        canny_low = cv2.getTrackbarPos("Canny Low", "Vector Control")
        canny_high = cv2.getTrackbarPos("Canny High", "Vector Control")
        blur_k = cv2.getTrackbarPos("Blur Kernel", "Vector Control")
        min_len = cv2.getTrackbarPos("Min Path Len", "Vector Control")
        smooth_win = cv2.getTrackbarPos("Smooth Win", "Vector Control")

        if blur_k % 2 == 0:
            blur_k += 1
        if blur_k < 3:
            blur_k = 3

        if smooth_win % 2 == 0:
            smooth_win += 1
        if smooth_win < 5:
            smooth_win = 5

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
        blur = cv2.GaussianBlur(gray, (blur_k, blur_k), 0)
        edges = cv2.Canny(blur, canny_low, canny_high)
        edges_person = cv2.bitwise_and(edges, edges, mask=combined_mask)

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

                # prevent overflow 
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
                paths = skeleton_paths(edges_person, min_len, smooth_win)

                plan = planning.build_plan(paths)
                preview = planning.render_plan(plan, (h, w))

                cv2.imshow("Vector", preview)
                cv2.waitKey(0)

                # preview 보여준 뒤, 실제 DRAWING에 planning 결과 반영
                ordered_paths = [step.path for step in plan if step.pen == "DOWN"]
                paths = ordered_paths

                mode = "DRAWING"
                draw_path_idx = 0
                draw_point_idx = 1
                force_finish = False

            elif mode == "DRAWING":
                force_finish = True

            elif mode == "PAUSE":
                mode = "LIVE"

    cap.release()
    cv2.destroyAllWindows()