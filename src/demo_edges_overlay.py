import cv2
import numpy as np
import mediapipe as mp

# ---------------------------
# MediaPipe 사람 마스크
# ---------------------------
mp_selfie = mp.solutions.selfie_segmentation
segmenter = mp_selfie.SelfieSegmentation(model_selection=1)

mp_face = mp.solutions.face_detection
face_detector = mp_face.FaceDetection(model_selection=0, min_detection_confidence=0.6)


# ---------------------------
# 벡터 기반 선 병합 함수
# ---------------------------
def angle_between(v1, v2):
    v1 = v1 / (np.linalg.norm(v1) + 1e-6)
    v2 = v2 / (np.linalg.norm(v2) + 1e-6)
    dot = np.clip(np.dot(v1, v2), -1.0, 1.0)
    return np.arccos(dot)


def merge_polylines(polylines, dist_thresh=20, angle_thresh_deg=25):

    angle_thresh = np.deg2rad(angle_thresh_deg)
    merged = []
    used = [False] * len(polylines)

    for i in range(len(polylines)):
        if used[i]:
            continue

        base = polylines[i].copy()
        used[i] = True
        changed = True

        while changed:
            changed = False
            for j in range(len(polylines)):
                if used[j]:
                    continue

                p = polylines[j]

                # base 끝점과 p 시작점 거리
                d = np.linalg.norm(base[-1] - p[0])

                if d < dist_thresh:

                    v1 = base[-1] - base[-2]
                    v2 = p[1] - p[0]

                    if angle_between(v1, v2) < angle_thresh:
                        base = np.vstack((base, p))
                        used[j] = True
                        changed = True

        merged.append(base)

    return merged


# ---------------------------
# 메인 처리
# ---------------------------
def process_frame(frame):

    rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

    # 1) 사람 마스크
    seg = segmenter.process(rgb)
    if seg.segmentation_mask is None:
        blank = np.zeros_like(frame)
        return blank, blank[:,:,0], blank, blank

    mask = (seg.segmentation_mask > 0.5).astype(np.uint8)
    mask = cv2.GaussianBlur(mask.astype(np.float32), (11,11), 0)
    mask = (mask > 0.3).astype(np.uint8)

    person = frame.copy()
    person[mask == 0] = 0

    # 2) 엣지
    gray = cv2.cvtColor(person, cv2.COLOR_BGR2GRAY)
    gray = cv2.equalizeHist(gray)

    edges = cv2.Canny(gray, 40, 100)

    kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3,3))
    edges = cv2.morphologyEx(edges, cv2.MORPH_CLOSE, kernel)

    edges_255 = (edges > 0).astype(np.uint8) * 255

    # 3) Contour → Polyline
    contours, _ = cv2.findContours(edges_255, cv2.RETR_LIST, cv2.CHAIN_APPROX_NONE)

    polylines = []

    for cnt in contours:
        if cnt.shape[0] < 40:
            continue
        approx = cv2.approxPolyDP(cnt, epsilon=2.0, closed=False)
        pts = approx.reshape(-1, 2).astype(np.float32)
        if pts.shape[0] < 2:
            continue
        polylines.append(pts)

    # 4) 벡터 병합
    merged = merge_polylines(polylines, dist_thresh=25, angle_thresh_deg=30)

    # 5) Overlay (원본 위)
    overlay = frame.copy()
    for line in merged:
        cv2.polylines(overlay, [line.astype(np.int32)], False, (255,255,255), 2, cv2.LINE_AA)

    # 6) FinalLines (완전 검은 배경)
    final_lines = np.zeros_like(frame)
    for line in merged:
        cv2.polylines(final_lines, [line.astype(np.int32)], False, (255,255,255), 2, cv2.LINE_AA)

    return person, edges_255, overlay, final_lines
# ---------------------------
# 실행
# ---------------------------
def main():

    cap = cv2.VideoCapture(0)

    if not cap.isOpened():
        print("Camera open failed")
        return

    paused = False
    current_frame = None

    while True:

        if not paused:
            ret, frame = cap.read()
            if not ret:
                break
            current_frame = frame.copy()

        if current_frame is None:
            continue

        person, edges, overlay, final_lines = process_frame(current_frame)
        cv2.imshow("Camera", person)
        cv2.imshow("Edges", edges)
        cv2.imshow("Overlay", overlay)
        cv2.imshow("FinalLines", final_lines)

        key = cv2.waitKey(0 if paused else 1) & 0xFF

        if key == 27 or key == ord('q'):
            break

        # 스페이스바 → pause / 다음 프레임
        if key == ord(' '):
            if paused:
                # 다음 프레임 하나 읽고 다시 멈춤
                ret, frame = cap.read()
                if ret:
                    current_frame = frame.copy()
                paused = True
            else:
                paused = True

        # r 누르면 실시간 모드 복귀
        if key == ord('r'):
            paused = False

    cap.release()
    cv2.destroyAllWindows()

if __name__ == "__main__":
    main()