## 펜 플로터 머신 polar.py
## 2026 SIOR spring 홍보부스용
## edited: 03/07/2026

## 극좌표(Polar) 플로터 지원
##   - 원형 종이가 회전 (θ 모터)
##   - 펜이 중심에서 직선으로만 이동 (r 모터)
##   - (x, y) → (r, θ) 변환
##   - 극좌표 G-code 생성
##   - 원형 종이 회전 + 펜 이동 시각화 애니메이션

import cv2
import numpy as np
from datetime import datetime
import config


# ================================================================
#  좌표 변환
# ================================================================

def get_paper_center():
    """종이 중심 좌표 (mm)"""
    cx = config.PAPER_OFFSET_X_MM + config.PAPER_W_MM / 2
    cy = config.PAPER_OFFSET_Y_MM + config.PAPER_H_MM / 2
    return cx, cy


def get_paper_radius():
    """원형 종이 반지름 (mm) — 짧은 변 기준"""
    return min(config.PAPER_W_MM, config.PAPER_H_MM) / 2


def to_polar(paths):
    """
    Cartesian mm paths → polar (r_mm, theta_deg) paths

    원점 = 종이 중심
    r     = 중심에서의 거리 (mm)
    theta = 각도 (degrees, atan2 기준)
    """
    cx, cy = get_paper_center()
    polar_paths = []

    for path in paths:
        dx = path[:, 0] - cx
        dy = path[:, 1] - cy
        r = np.sqrt(dx**2 + dy**2)
        theta = np.degrees(np.arctan2(dy, dx))
        polar_paths.append(np.column_stack([r, theta]))

    return polar_paths


# ================================================================
#  극좌표 G-code 생성
# ================================================================

def generate_polar_gcode(
    paths,
    filename="robot_drawing_polar.gcode",
    feedrate=800,
    z_feedrate=300,
    pen_up_z=5.0,
    pen_down_z=0.0,
):
    """
    극좌표 G-code 생성

    축 매핑:
      R = 반지름 (mm, 중심에서의 거리)
      A = 각도  (degrees)
      Z = 펜 up/down
    """
    polar_paths = to_polar(paths)

    if not polar_paths:
        print("[polar gcode] 변환할 경로가 없습니다.")
        return []

    total_pts = sum(len(p) for p in polar_paths)
    lines = []

    # ── 헤더 ──────────────────────────────────────────────────────
    lines.append("; Polar Plotter G-code")
    lines.append(f"; Generated : {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    lines.append(f"; Paths     : {len(polar_paths)}")
    lines.append(f"; Points    : {total_pts}")
    lines.append(f"; Paper     : radius {get_paper_radius():.1f} mm (circular)")
    lines.append("; Axis      : R=radius(mm)  A=angle(deg)  Z=pen")
    lines.append("G21")
    lines.append("G90")
    lines.append(f"G0 Z{pen_up_z:.3f}")

    active_f = None

    def g1(r=None, a=None, z=None, f=None):
        nonlocal active_f
        parts = ["G1"]
        if r is not None:
            parts.append(f"R{r:.3f}")
        if a is not None:
            parts.append(f"A{a:.3f}")
        if z is not None:
            parts.append(f"Z{z:.3f}")
        if f is not None and f != active_f:
            parts.append(f"F{f}")
            active_f = f
        return " ".join(parts)

    # ── 경로 루프 ─────────────────────────────────────────────────
    for i, polar in enumerate(polar_paths):
        if len(polar) < 2:
            continue

        r0, a0 = polar[0]

        lines.append(f"\n; Path {i + 1}/{len(polar_paths)}")
        lines.append(f"G0 Z{pen_up_z:.3f}")
        lines.append(f"G0 R{r0:.3f} A{a0:.3f}")
        lines.append(g1(z=pen_down_z, f=z_feedrate))

        for j in range(1, len(polar)):
            r, a = polar[j]
            lines.append(g1(r=r, a=a, f=feedrate))

    # ── 푸터 ──────────────────────────────────────────────────────
    lines.append(f"\nG0 Z{pen_up_z:.3f}")
    lines.append("G0 R0.000 A0.000")
    lines.append("M30")

    with open(filename, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))

    print(f"[polar gcode] 저장: {filename}")
    print(f"              경로 {len(polar_paths)}개 / 포인트 {total_pts}개")

    return lines


# ================================================================
#  시각화 애니메이션
# ================================================================

DRAW_SPEED = 5  # 프레임당 처리할 포인트 수


def polar_preview(paths, draw_speed=DRAW_SPEED, record=True, video_file=f"polar_preview_{datetime.now().strftime('%Y%m%d_%H%M%S')}.mp4", fps=30):
    """
    극좌표 플로터 시각화 애니메이션

    원형 종이가 회전하고 펜이 중심에서 직선으로 움직이는 모습을 보여줍니다.

    시각 요소:
      ● 갈색 원    = 원형 종이 경계
      ─ 회색 수평선 = 펜 이동 축 (고정)
      ● 파란 점     = 펜 위치 (축 위, 중심에서 r만큼)
      ● 빨간 점     = 현재 그리는 위치 (종이 위)
      ▌ 초록 선     = 종이 회전 표시 (12시 방향 기준 마크)

    Controls: ESC/Q = 종료, SPACE = 일시정지

    record     : True이면 영상 파일로 저장
    video_file : 저장할 파일명 (.mp4)
    fps        : 녹화 프레임 레이트
    """
    if not paths:
        print("[polar preview] 경로가 없습니다.")
        return

    # ── 좌표계 설정 ───────────────────────────────────────────────
    cx_mm, cy_mm = get_paper_center()
    paper_r_mm = get_paper_radius()

    canvas_size = 700
    status_h = 50
    total_h = canvas_size + status_h
    margin = 50

    draw_r_px = (canvas_size - 2 * margin) // 2
    scale = draw_r_px / paper_r_mm

    # 캔버스 중심 (원형 종이 중심)
    ccx = canvas_size // 2
    ccy = status_h + canvas_size // 2

    def mm2px(x_mm, y_mm):
        px = int((x_mm - cx_mm) * scale + ccx)
        py = int(-(y_mm - cy_mm) * scale + ccy)
        return (px, py)

    # ── 극좌표 변환 ───────────────────────────────────────────────
    polar_paths = to_polar(paths)
    total_paths = len(paths)

    # ── 기본 캔버스 (종이) ────────────────────────────────────────
    base = np.ones((total_h, canvas_size, 3), dtype=np.uint8) * 220

    # 종이 그림자 + 종이 채우기 + 테두리 + 중심 핀
    cv2.circle(base, (ccx, ccy), draw_r_px + 4, (190, 180, 165), -1)
    cv2.circle(base, (ccx, ccy), draw_r_px, (248, 243, 233), -1)
    cv2.circle(base, (ccx, ccy), draw_r_px, (150, 120, 80), 2)
    cv2.circle(base, (ccx, ccy), 3, (120, 120, 120), -1)

    drawn = base.copy()

    cv2.namedWindow("Polar Preview", cv2.WINDOW_AUTOSIZE)

    # ── 녹화 설정 ────────────────────────────────────────────────
    writer = None
    if record:
        fourcc = cv2.VideoWriter_fourcc(*"mp4v")
        writer = cv2.VideoWriter(video_file, fourcc, fps, (canvas_size, total_h))
        if writer.isOpened():
            print(f"[polar preview] 녹화 시작: {video_file}  ({fps} fps)")
        else:
            print(f"[polar preview] VideoWriter 열기 실패 — 녹화 없이 진행")
            writer = None

    # ── 애니메이션 루프 ───────────────────────────────────────────
    for pi in range(total_paths):
        path = paths[pi]
        polar = polar_paths[pi]

        if len(path) < 2:
            continue

        qi = 1
        while qi < len(path):

            # 이번 프레임에 그릴 세그먼트들
            end = min(qi + draw_speed, len(path))
            for j in range(qi, end):
                p1 = mm2px(path[j - 1][0], path[j - 1][1])
                p2 = mm2px(path[j][0], path[j][1])
                cv2.line(drawn, p1, p2, (30, 30, 30), 2, cv2.LINE_AA)
            qi = end

            cur = min(qi - 1, len(polar) - 1)
            r_now = polar[cur][0]
            theta_deg = polar[cur][1]
            theta_rad = np.radians(theta_deg)

            # ── 디스플레이 프레임 구성 ────────────────────────────
            display = drawn.copy()

            # 종이 테두리 (다시 그려야 세그먼트 위에 표시됨)
            cv2.circle(display, (ccx, ccy), draw_r_px, (150, 120, 80), 2)

            # ① 펜 축 (고정 수평선)
            cv2.line(display,
                     (ccx - draw_r_px - 20, ccy),
                     (ccx + draw_r_px + 20, ccy),
                     (180, 180, 180), 1, cv2.LINE_AA)

            # ② 종이 회전 표시 (12시 방향 마크, 종이와 함께 회전)
            #    종이가 -θ 만큼 회전하므로 마크는 π/2 - θ 위치
            mark_angle = np.pi / 2 - theta_rad
            mk_in = draw_r_px - 14
            mk_out = draw_r_px + 3
            mk1 = (int(ccx + mk_in  * np.cos(mark_angle)),
                    int(ccy - mk_in  * np.sin(mark_angle)))
            mk2 = (int(ccx + mk_out * np.cos(mark_angle)),
                    int(ccy - mk_out * np.sin(mark_angle)))
            cv2.line(display, mk1, mk2, (0, 160, 0), 3, cv2.LINE_AA)

            # ③ θ 방향선 (중심 → 현재 점 방향, 얇은 초록)
            t_end = (int(ccx + draw_r_px * 0.85 * np.cos(theta_rad)),
                     int(ccy - draw_r_px * 0.85 * np.sin(theta_rad)))
            cv2.line(display, (ccx, ccy), t_end,
                     (100, 210, 100), 1, cv2.LINE_AA)

            # ④ 펜 위치 (파란 점, 수평 축 위에서 r만큼)
            pen_px = int(ccx + min(r_now, paper_r_mm) * scale)
            cv2.circle(display, (pen_px, ccy), 6, (255, 120, 30), -1)

            # ⑤ 현재 그리는 위치 (빨간 점, 종이 위)
            cur_px = mm2px(path[cur][0], path[cur][1])
            cv2.circle(display, cur_px, 4, (0, 0, 255), -1)

            # 중심 핀
            cv2.circle(display, (ccx, ccy), 3, (100, 100, 100), -1)

            # ── 상단 상태바 ───────────────────────────────────────
            cv2.rectangle(display, (0, 0), (canvas_size, status_h), (35, 35, 35), -1)

            line1 = f"Path {pi + 1}/{total_paths}   Point {cur}/{len(path) - 1}"
            cv2.putText(display, line1, (12, 22),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.50, (255, 255, 255), 1)

            line2 = f"r = {r_now:.1f} mm    theta = {theta_deg:.1f} deg"
            cv2.putText(display, line2, (12, 42),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.45, (130, 220, 130), 1)

            cv2.imshow("Polar Preview", display)
            if writer:
                writer.write(display)

            key = cv2.waitKey(1) & 0xFF
            if key == 27 or key == ord("q"):
                if writer:
                    writer.release()
                    print(f"[polar preview] 녹화 저장: {video_file}")
                cv2.destroyWindow("Polar Preview")
                return
            if key == ord(" "):
                cv2.waitKey(0)

    # ── 완료 화면 (1초간 녹화 + 아무 키나 누르면 닫힘) ────────────
    display = drawn.copy()
    cv2.circle(display, (ccx, ccy), draw_r_px, (150, 120, 80), 2)
    cv2.rectangle(display, (0, 0), (canvas_size, status_h), (35, 35, 35), -1)
    cv2.putText(display, f"Complete  |  {total_paths} paths",
                (12, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (255, 255, 255), 1)
    cv2.imshow("Polar Preview", display)
    if writer:
        for _ in range(fps):        # 완료 화면 1초간 녹화
            writer.write(display)
        writer.release()
        print(f"[polar preview] 녹화 저장: {video_file}")
    cv2.waitKey(0)
    cv2.destroyWindow("Polar Preview")
