## 펜 플로터 머신 serial_sender.py
## 2026 SIOR spring 홍보부스용
## edited: 03/08/2026

## serial_sender
## 극좌표 G-code 전송 + 실시간 시각화
## arduino UNO + L293D Motor Shield

"""
PC → Arduino 극좌표 G-code streaming

Arduino firmware 조건
    각 명령 처리 후 'ok' 응답
    축: R(반지름 mm), A(각도 deg), Z(펜)
"""

import cv2
import numpy as np
import config
from hardware import serial_manager


# ================================================================
#  LiveView: 극좌표 G-code 실행 중 실시간 시각화
# ================================================================

class LiveView:
    """
    Arduino에 극좌표 G-code를 전송하면서 동시에 OpenCV 창에
    원형 종이 위에 그려지는 모습을 표시합니다.

    polar.py의 polar_preview와 비슷한 시각화.
    """

    def __init__(self, total_paths=0):

        # 종이 반지름 (mm)
        self.paper_r_mm = min(config.PAPER_W_MM, config.PAPER_H_MM) / 2

        # 캔버스 설정
        self.canvas_size = 600
        self.status_h = 50
        self.total_h = self.canvas_size + self.status_h
        margin = 40

        self.draw_r_px = (self.canvas_size - 2 * margin) // 2

        # 캔버스 중심
        self.ccx = self.canvas_size // 2
        self.ccy = self.status_h + self.canvas_size // 2

        # 기본 캔버스 (원형 종이)
        self.base = np.ones((self.total_h, self.canvas_size, 3), dtype=np.uint8) * 220

        # 종이 그림자 + 채우기 + 테두리 + 중심 핀
        cv2.circle(self.base, (self.ccx, self.ccy), self.draw_r_px + 4, (190, 180, 165), -1)
        cv2.circle(self.base, (self.ccx, self.ccy), self.draw_r_px, (248, 243, 233), -1)
        cv2.circle(self.base, (self.ccx, self.ccy), self.draw_r_px, (150, 120, 80), 2)
        cv2.circle(self.base, (self.ccx, self.ccy), 3, (120, 120, 120), -1)

        self.drawn = self.base.copy()

        # 상태
        self.cur_r = 0.0    # mm
        self.cur_a = 0.0    # degrees
        self.pen_down = False
        self.path_num = 0
        self.total_paths = total_paths
        self.point_count = 0

        cv2.namedWindow("Plotter Live", cv2.WINDOW_AUTOSIZE)


    def _polar2px(self, r_mm, a_deg):
        """극좌표 (r mm, a degrees) → OpenCV 픽셀"""
        scale = self.draw_r_px / self.paper_r_mm
        a_rad = np.radians(a_deg)
        x_mm = r_mm * np.cos(a_rad)
        y_mm = r_mm * np.sin(a_rad)
        px = int(self.ccx + x_mm * scale)
        py = int(self.ccy - y_mm * scale)
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
        new_r = self.cur_r
        new_a = self.cur_a
        new_z = None
        for token in upper[1:]:
            if token[0] == "R":
                new_r = float(token[1:])
            elif token[0] == "A":
                new_a = float(token[1:])
            elif token[0] == "Z":
                new_z = float(token[1:])

        # 펜 상태 변화
        if new_z is not None:
            was_down = self.pen_down
            self.pen_down = (new_z <= 1.0)
            if self.pen_down and not was_down:
                self.point_count = 0

        # 그리기 (펜 내린 상태에서 이동할 때만)
        if self.pen_down and (new_r != self.cur_r or new_a != self.cur_a):
            self.point_count += 1
            p1 = self._polar2px(self.cur_r, self.cur_a)
            p2 = self._polar2px(new_r, new_a)
            cv2.line(self.drawn, p1, p2, (30, 30, 30), 2, cv2.LINE_AA)

        self.cur_r = new_r
        self.cur_a = new_a
        self._show()


    def _show(self):

        display = self.drawn.copy()

        # 종이 테두리
        cv2.circle(display, (self.ccx, self.ccy), self.draw_r_px, (150, 120, 80), 2)

        # 펜 축 (고정 수평선)
        cv2.line(display,
                 (self.ccx - self.draw_r_px - 15, self.ccy),
                 (self.ccx + self.draw_r_px + 15, self.ccy),
                 (180, 180, 180), 1, cv2.LINE_AA)

        # 현재 위치 마커
        cur_px = self._polar2px(self.cur_r, self.cur_a)
        if self.pen_down:
            cv2.circle(display, cur_px, 5, (0, 0, 255), -1)       # 빨강 = 그리는 중
        else:
            cv2.circle(display, cur_px, 5, (255, 100, 0), -1)      # 파랑 = 이동 중

        # 펜 위치 (수평 축 위)
        scale = self.draw_r_px / self.paper_r_mm
        pen_px = int(self.ccx + min(self.cur_r, self.paper_r_mm) * scale)
        cv2.circle(display, (pen_px, self.ccy), 5, (255, 120, 30), -1)

        # 중심 핀
        cv2.circle(display, (self.ccx, self.ccy), 3, (100, 100, 100), -1)

        # ── 상단 상태바 ───────────────────────────────────────────
        cv2.rectangle(display, (0, 0), (self.canvas_size, self.status_h), (35, 35, 35), -1)

        state = "DRAWING" if self.pen_down else "MOVING"
        line1 = f"Path {self.path_num}/{self.total_paths}  |  Point {self.point_count}  |  {state}"
        cv2.putText(display, line1, (12, 22),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.50, (255, 255, 255), 1)

        line2 = f"r={self.cur_r:.1f}mm  a={self.cur_a:.1f}deg"
        cv2.putText(display, line2, (12, 42),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.45, (130, 220, 130), 1)

        cv2.imshow("Plotter Live", display)
        cv2.waitKey(1)


    def close(self):
        cv2.waitKey(0)
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

            if resp.startswith("ok"):
                break

            if resp.startswith("error"):
                print("[error]", resp)
                viz.close()
                return

            if resp:
                print("[arduino]", resp)

        # ok 받은 후 → 시각화 업데이트
        viz.on_command(cmd)

    print(f"[serial] 전송 완료: {total_paths}개 경로")
    viz.close()
