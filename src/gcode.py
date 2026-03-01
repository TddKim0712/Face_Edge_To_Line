## 펜 플로터 머신 gcode.py
## 2026 SIOR spring 홍보부스용
## edited: 02/28/2026

## Input : List[np.ndarray]  – paths in mm (from vision.webcam_vector)
## Output: G-code file

# 주요 개선사항:
#  - 좌표 이미 mm (normalize 완료) → scale/canvas_height 제거
#  - F 파라미터 모달 처리 (중복 출력 제거)
#  - Z축 전용 feedrate (z_feedrate)
#  - G0 이동엔 F 없음 (rapid)
#  - 기계 범위 초과 경고
#  - 경로/포인트 통계 헤더

import numpy as np
from datetime import datetime
import config


def generate_gcode(
    paths,
    filename="output.gcode",
    feedrate=800,       # XY 드로잉 속도 (mm/min) – 28BYJ-48 최대 ~900mm/min
    z_feedrate=300,     # Z축 속도 (mm/min)
    pen_up_z=5.0,       # 펜 올린 위치 (mm)
    pen_down_z=0.0,     # 펜 내린 위치 (mm)
    return_home=True,   # 완료 후 원점 복귀
):
    """
    mm 좌표 paths → G-code 파일로 변환.

    paths: vision.webcam_vector() 반환값 (이미 mm 단위, Y 반전 완료)
    """
    if not paths:
        print("[gcode] 변환할 경로가 없습니다.")
        return []

    # ── 범위 초과 검사 ────────────────────────────────────────────
    max_x = config.MACHINE_W_MM
    max_y = config.MACHINE_H_MM
    out_of_bounds = []
    for i, path in enumerate(paths):
        for pt in path:
            x, y = float(pt[0]), float(pt[1])
            if x < 0 or x > max_x or y < 0 or y > max_y:
                out_of_bounds.append((i, x, y))
                break

    # ── 통계 계산 ─────────────────────────────────────────────────
    total_points = sum(len(p) for p in paths)
    pen_down_mm = sum(
        np.sum(np.linalg.norm(p[1:] - p[:-1], axis=1))
        for p in paths if len(p) >= 2
    )

    lines = []

    # ── 헤더 ──────────────────────────────────────────────────────
    lines.append(f"; Pen Plotter G-code")
    lines.append(f"; Generated : {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    lines.append(f"; Paths     : {len(paths)}")
    lines.append(f"; Points    : {total_points}")
    lines.append(f"; PenDown   : {pen_down_mm:.1f} mm")
    lines.append(f"; Machine   : {max_x} x {max_y} mm")
    if out_of_bounds:
        lines.append(f"; WARNING   : {len(out_of_bounds)} 경로가 기계 범위 초과!")

    lines.append("G21 ; mm 단위")
    lines.append("G90 ; 절대 좌표")
    lines.append(f"G0 Z{pen_up_z:.3f}  ; 초기 펜 올리기")

    # ── 모달 feedrate 추적 (중복 F 출력 제거) ────────────────────
    active_f = None

    def g1(x=None, y=None, z=None, f=None):
        """F는 변경될 때만 출력."""
        nonlocal active_f
        parts = ["G1"]
        if x is not None:
            parts.append(f"X{x:.3f}")
        if y is not None:
            parts.append(f"Y{y:.3f}")
        if z is not None:
            parts.append(f"Z{z:.3f}")
        if f is not None and f != active_f:
            parts.append(f"F{f}")
            active_f = f
        return " ".join(parts)

    # ── 경로 루프 ──────────────────────────────────────────────────
    for i, path in enumerate(paths):
        if len(path) < 2:
            continue

        x0, y0 = float(path[0][0]), float(path[0][1])

        lines.append(f"\n; Path {i + 1}/{len(paths)}")
        lines.append(f"G0 Z{pen_up_z:.3f}")               # 펜 올리기 (rapid)
        lines.append(f"G0 X{x0:.3f} Y{y0:.3f}")           # 이동 (rapid)
        lines.append(g1(z=pen_down_z, f=z_feedrate))       # 펜 내리기

        # 첫 점은 이미 이동했으니 두 번째부터
        for pt in path[1:]:
            lines.append(g1(x=float(pt[0]), y=float(pt[1]), f=feedrate))

    # ── 푸터 ──────────────────────────────────────────────────────
    lines.append(f"\nG0 Z{pen_up_z:.3f}  ; 최종 펜 올리기")
    if return_home:
        lines.append("G0 X0.000 Y0.000   ; 원점 복귀")
    lines.append("M30 ; 프로그램 종료")

    # ── 파일 저장 ─────────────────────────────────────────────────
    with open(filename, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))

    print(f"[gcode] 저장 완료: {filename}")
    print(f"        경로 {len(paths)}개 / 포인트 {total_points}개 / 드로잉 {pen_down_mm:.1f}mm")
    if out_of_bounds:
        print(f"        ⚠ 범위 초과 경로 {len(out_of_bounds)}개 (기계 한계: {max_x}x{max_y}mm)")

    return lines

# 시리얼 전송 (아두이노 연결 시 사용)
def send_to_arduino(filename, port="COM3", baud=115200):
    """
    G-code 파일을 아두이노로 한 줄씩 전송.
    아두이노 펌웨어가 각 명령 처리 후 'ok'를 응답해야 합니다.

    pip install pyserial
    """
    try:
        import serial
        import time
    except ImportError:
        print("[serial] pyserial이 없습니다: pip install pyserial")
        return

    with open(filename, encoding="utf-8") as f:
        lines = f.readlines()

    print(f"[serial] {port} @ {baud} 연결 중...")
    with serial.Serial(port, baud, timeout=5) as ser:
        time.sleep(2)                        # 아두이노 리셋 대기
        startup = ser.readline().decode().strip()
        print(f"[arduino] {startup}")

        sent = 0
        for raw_line in lines:
            line = raw_line.strip()

            # 주석·빈 줄 건너뜀 (아두이노 버퍼 절약)
            if not line or line.startswith(";"):
                continue

            # 인라인 주석 제거 후 전송
            cmd = line.split(";")[0].strip()
            if not cmd:
                continue

            ser.write((cmd + "\n").encode())
            response = ser.readline().decode().strip()
            sent += 1

            print(f"  >> {cmd}")
            print(f"  << {response}")

            if response.startswith("error"):
                print("[serial] 아두이노 오류 발생, 중단합니다.")
                break

    print(f"[serial] 완료: {sent}개 명령 전송")
