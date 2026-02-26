import cv2
import numpy as np
from ultralytics import YOLO
from scipy.signal import savgol_filter


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

        if mode == "DRAWING":

            total_paths = len(paths)

            # 이미 완료된 path
            for i in range(draw_path_idx):
                cv2.polylines(vector_canvas,
                              [paths[i].astype(np.int32)],
                              False,
                              (0, 0, 0),
                              2)

            # 현재 그리는 path
            if draw_path_idx < total_paths:
                p = paths[draw_path_idx]

                if draw_point_idx < len(p):
                    pts = p[:draw_point_idx].astype(np.int32)

                    if len(pts) > 1:
                        cv2.polylines(vector_canvas,
                                      [pts],
                                      False,
                                      (150, 150, 150),
                                      2)

                    cx, cy = p[draw_point_idx - 1].astype(int)

                    cv2.circle(vector_canvas, (cx, cy), 6, (50, 50, 50), -1)

                    cv2.putText(vector_canvas,
                                str(draw_path_idx + 1),
                                (cx + 5, cy - 5),
                                cv2.FONT_HERSHEY_SIMPLEX,
                                0.5,
                                (0, 0, 0),
                                1)

                    draw_point_idx += 2
                else:
                    draw_path_idx += 1
                    draw_point_idx = 1

            cv2.putText(vector_canvas,
                        f"Total Paths: {total_paths}",
                        (20, 30),
                        cv2.FONT_HERSHEY_SIMPLEX,
                        0.8,
                        (0, 0, 0),
                        2)

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

                mode = "DRAWING"
                draw_path_idx = 0
                draw_point_idx = 1

            elif mode == "DRAWING":
                mode = "LIVE"

    cap.release()
    cv2.destroyAllWindows()


if __name__ == "__main__":
    webcam_vector()