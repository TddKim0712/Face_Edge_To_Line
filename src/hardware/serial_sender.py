## 펜 플로터 머신 serial_sender.py
## 2026 SIOR spring 홍보부스용
## edited: 03/05/2026

## serial_sender
## G-code 전송 전용 모듈 + 실시간 시각화
## arduino UNO 사용
# Digital Pin 2,3,4,5 / 6,7,8,9 / 10,11,12,13 --> 각각 corresponding to X,Y,Z stepper motor drive IN(1,2,3,4)

"""
PC → Arduino G-code streaming

Arduino firmware 조건
    각 명령 처리 후 'ok' 응답
"""

import cv2
import numpy as np
import config
from hardware import serial_manager


# ================================================================
#  LiveView: G-code 실행 중 실시간 시각화
# ================================================================

class LiveView:
    """
    Arduino에 G-code를 전송하면서 동시에 OpenCV 창에
    지금 어떤 경로(Path)의 어떤 점(Point)을 그리고 있는지 표시합니다.

    vision.py의 DRAWING 모드와 비슷한 시각화.
    """

    def __init__(self, total_paths=0):

        # 캔버스 크기 (mm → px 변환)
        self.scale = 3.0
        margin = 20
        self.margin = margin
        self.cw = int(config.MACHINE_W_MM * self.scale) + margin * 2
        self.ch = int(config.MACHINE_H_MM * self.scale) + margin * 2 + 40  # 상단 상태바 공간

        # 그려진 선 (영구 레이어)
        self.canvas = np.ones((self.ch, self.cw, 3), dtype=np.uint8) * 255

        # 종이 영역 표시
        p1 = self._mm2px(config.PAPER_OFFSET_X_MM, config.PAPER_OFFSET_Y_MM)
        p2 = self._mm2px(
            config.PAPER_OFFSET_X_MM + config.PAPER_W_MM,
            config.PAPER_OFFSET_Y_MM + config.PAPER_H_MM
        )
        cv2.rectangle(self.canvas, p1, p2, (200, 170, 140), 1)

        # 상태
        self.pos = (0.0, 0.0)
        self.pen_down = False
        self.path_num = 0
        self.total_paths = total_paths
        self.point_count = 0

        cv2.namedWindow("Plotter Live", cv2.WINDOW_AUTOSIZE)


    def _mm2px(self, x_mm, y_mm):
        """mm 좌표 → OpenCV 픽셀 (Y 반전)"""
        px = int(x_mm * self.scale) + self.margin
        py = self.ch - self.margin - int(y_mm * self.scale)
        return (px, py)


    def on_path(self, label):
        """'; Path N/M' 주석이 감지되면 호출"""
        parts = label.split()
        if len(parts) >= 2 and "/" in parts[1]:
            n, m = parts[1].split("/")
            self.path_num = int(n)
            self.total_paths = int(m)
        self.point_count = 0


    def on_command(self, cmd):
        """G-code 명령 하나가 실행된 후 호출 → 캔버스 업데이트"""

        upper = cmd.upper().split()
        if not upper or upper[0] not in ("G0", "G1"):
            return

        # 파라미터 파싱
        new_x, new_y = self.pos
        new_z = None
        for token in upper[1:]:
            if token[0] == "X":
                new_x = float(token[1:])
            elif token[0] == "Y":
                new_y = float(token[1:])
            elif token[0] == "Z":
                new_z = float(token[1:])

        # 펜 상태 변화
        if new_z is not None:
            was_down = self.pen_down
            self.pen_down = (new_z <= 1.0)
            if self.pen_down and not was_down:
                self.point_count = 0          # 새 경로 시작

        # 그리기 (펜 내린 상태에서 이동할 때만)
        if self.pen_down and (new_x, new_y) != self.pos:
            self.point_count += 1
            p1 = self._mm2px(*self.pos)
            p2 = self._mm2px(new_x, new_y)
            cv2.line(self.canvas, p1, p2, (0, 0, 0), 2)

        self.pos = (new_x, new_y)
        self._show()


    def _show(self):

        display = self.canvas.copy()

        # ── 현재 위치 마커 ────────────────────────────────────────
        px, py = self._mm2px(*self.pos)
        if self.pen_down:
            cv2.circle(display, (px, py), 5, (0, 0, 255), -1)      # 빨강 = 그리는 중
        else:
            cv2.circle(display, (px, py), 5, (255, 100, 0), -1)     # 파랑 = 이동 중

        # ── 상단 상태바 ───────────────────────────────────────────
        cv2.rectangle(display, (0, 0), (self.cw, 36), (40, 40, 40), -1)

        state = "DRAWING" if self.pen_down else "MOVING"

        text = f"Path {self.path_num}/{self.total_paths}  |  Point {self.point_count}  |  {state}"
        cv2.putText(display, text, (10, 24),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.55, (255, 255, 255), 1)

        coord = f"X={self.pos[0]:.1f}  Y={self.pos[1]:.1f}"
        cv2.putText(display, coord, (self.cw - 200, 24),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (180, 180, 180), 1)

        cv2.imshow("Plotter Live", display)
        cv2.waitKey(1)


    def close(self):
        cv2.waitKey(0)           # 완료 후 아무 키나 누를 때까지 결과 표시
        cv2.destroyWindow("Plotter Live")


# ================================================================
#  Serial 전송
# ================================================================

def wait_ready():

    ser = serial_manager.get_serial()

    while True:

        line = ser.readline().decode(errors="replace").strip()

        if line:
            print("[arduino]", line)

        if line == "ready":
            break


def send_gcode(filename):

    ser = serial_manager.get_serial()

    with open(filename, encoding="utf-8") as f:
        lines = f.readlines()

    # 총 경로 수 미리 집계
    total_paths = sum(1 for l in lines if l.strip().startswith("; Path "))
    viz = LiveView(total_paths)

    wait_ready()

    for raw in lines:

        line = raw.strip()

        # 경로 주석 → 시각화에 전달 (Arduino에는 보내지 않음)
        if line.startswith("; Path "):
            viz.on_path(line[2:])
            continue

        if not line or line.startswith(";"):
            continue

        cmd = line.split(";")[0].strip()
        if not cmd:
            continue

        ser.write((cmd + "\n").encode())

        # ok 올 때까지 읽기 (중간 디버그 줄은 무시)
        while True:

            resp = ser.readline().decode(errors="replace").strip()

            if resp == "ok":
                break

            if resp.startswith("error"):
                print("[error]", resp)
                viz.close()
                return

        # ok 받은 후 → 시각화 업데이트
        viz.on_command(cmd)

    print(f"[serial] 전송 완료: {total_paths}개 경로")
    viz.close()
