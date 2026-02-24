import cv2
import numpy as np
from ultralytics import YOLO
from scipy.signal import savgol_filter
import os
import time


# ---------------------------
# Polyline smoothing
# ---------------------------
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


# ---------------------------
# Skeleton → Path extraction
# ---------------------------
def skeleton_paths(edge_img, min_len, smooth_win):

    skel = cv2.ximgproc.thinning(edge_img)

    h, w = skel.shape
    visited = np.zeros_like(skel, dtype=bool)
    paths = []

    def neighbors(y, x):
        for dy in [-1, 0, 1]:
            for dx in [-1, 0, 1]:
                if dy == 0 and dx == 0:
                    continue
                ny, nx = y + dy, x + dx
                if 0 <= ny < h and 0 <= nx < w and skel[ny, nx] > 0:
                    yield ny, nx

    for y in range(h):
        for x in range(w):
            if skel[y, x] and not visited[y, x]:

                stack = [(y, x)]
                path = []

                while stack:
                    cy, cx = stack.pop()
                    if visited[cy, cx]:
                        continue

                    visited[cy, cx] = True
                    path.append((cx, cy))

                    for ny, nx in neighbors(cy, cx):
                        if not visited[ny, nx]:
                            stack.append((ny, nx))

                if len(path) > min_len:
                    pts = np.array(path, dtype=np.float32)
                    pts = smooth_polyline(pts, smooth_win)
                    paths.append(pts)

    return paths


# ---------------------------
# Main
# ---------------------------
def webcam_vector():

    model = YOLO("yolov8n-seg.pt")
    cap = cv2.VideoCapture(0)

    if not cap.isOpened():
        print("Camera open failed")
        return

    # -------- Control Window --------
    cv2.namedWindow("Vector Control")
    cv2.createTrackbar("Canny Low", "Vector Control", 50, 200, lambda x: None)
    cv2.createTrackbar("Canny High", "Vector Control", 120, 300, lambda x: None)
    cv2.createTrackbar("Blur Kernel", "Vector Control", 5, 15, lambda x: None)
    cv2.createTrackbar("Min Path Len", "Vector Control", 40, 200, lambda x: None)
    cv2.createTrackbar("Smooth Win", "Vector Control", 9, 25, lambda x: None)

    paused = False
    current_frame = None

    os.makedirs("captures", exist_ok=True)

    while True:

        if not paused:
            ret, frame = cap.read()
            if not ret:
                break
            current_frame = frame.copy()

        if current_frame is None:
            continue

        frame = current_frame.copy()
        h, w, _ = frame.shape

        # -------- Read parameters --------
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

        # -------- YOLO Segmentation --------
        results = model(frame, verbose=False)[0]
        combined_mask = np.zeros((h, w), dtype=np.uint8)

        if results.masks is not None:
            for i, cls in enumerate(results.boxes.cls):
                if int(cls) == 0:
                    mask = results.masks.data[i].cpu().numpy()
                    mask = cv2.resize(mask, (w, h))
                    mask = (mask > 0.5).astype(np.uint8) * 255
                    combined_mask = cv2.bitwise_or(combined_mask, mask)

        # -------- Canny --------
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        blur = cv2.GaussianBlur(gray, (blur_k, blur_k), 0)

        edges = cv2.Canny(blur, canny_low, canny_high)
        edges_person = cv2.bitwise_and(edges, edges, mask=combined_mask)

        # -------- Pixel Sketch (흰 배경 + 검은 선) --------
        sketch = np.ones((h, w), dtype=np.uint8) * 255
        sketch[edges_person > 0] = 0
        sketch_color = cv2.cvtColor(sketch, cv2.COLOR_GRAY2BGR)

        # -------- Vector Extraction --------
        paths = skeleton_paths(edges_person, min_len, smooth_win)

        # -------- Vector Canvas (흰 배경 + 검은 선) --------
        vector_canvas = np.ones((h, w, 3), dtype=np.uint8) * 255

        for p in paths:
            cv2.polylines(
                vector_canvas,
                [p.astype(np.int32)],
                False,
                (0, 0, 0),  # 검은 선
                2,
                cv2.LINE_AA,
            )

        # -------- Display --------
        cv2.imshow("Camera", frame)
        cv2.imshow("Sketch", sketch_color)
        cv2.imshow("Vector", vector_canvas)

        key = cv2.waitKey(0 if paused else 1) & 0xFF

        if key == 27 or key == ord("q"):
            break

        # SPACE → step mode
        if key == ord(" "):
            if paused:
                ret, frame = cap.read()
                if ret:
                    current_frame = frame.copy()
            paused = True

        # r → real-time
        if key == ord("r"):
            paused = False

        # s → save
        if key == ord("s"):
            timestamp = time.strftime("%Y%m%d_%H%M%S")
            cv2.imwrite(f"captures/{timestamp}_camera.png", frame)
            cv2.imwrite(f"captures/{timestamp}_sketch.png", sketch_color)
            cv2.imwrite(f"captures/{timestamp}_vector.png", vector_canvas)
            print("Saved:", timestamp)

    cap.release()
    cv2.destroyAllWindows()


if __name__ == "__main__":
    webcam_vector()