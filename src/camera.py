## 펜 플로터 머신 camera.py
## 2026 SIOR spring 홍보부스용
## edited: 02/26/2026

## Input:
# Webcam live frames

## modify cam frames to adjust to unified format
# cropping out unless the input frame is same with required frmae

## output:
# Modified Webcam Frames 



import cv2


class Camera:

    def __init__(self, cam_index=0):
        self.cap = cv2.VideoCapture(cam_index)
        if not self.cap.isOpened():
            raise RuntimeError("Camera open failed")

    def release(self):
        self.cap.release()

    def _center_crop_to_ratio(self, frame, target_ratio):
        h, w = frame.shape[:2]
        current_ratio = w / h

        if current_ratio > target_ratio:
            new_w = int(h * target_ratio)
            x0 = (w - new_w) // 2
            return frame[:, x0:x0 + new_w]
        else:
            new_h = int(w / target_ratio)
            y0 = (h - new_h) // 2
            return frame[y0:y0 + new_h, :]

    def get_frame(self, paper_w_mm, paper_h_mm):
        ret, frame = self.cap.read()
        if not ret:
            return None

        target_ratio = paper_w_mm / paper_h_mm
        frame = self._center_crop_to_ratio(frame, target_ratio)

        return frame