## 펜 플로터 머신 main.py
## 2026 SIOR spring 홍보부스용
## edited: 02/28/2026

## Entry Point
# 1. 웹캠으로 얼굴 벡터 추출 (mm 좌표)
# 2. G-code 파일 생성
# 3. (선택) USB 시리얼로 아두이노에 전송

import vision
import gcode


GCODE_FILE = "robot_drawing.gcode"

def main():
    # 1. 웹캠 벡터 추출 (반환값: mm 좌표 paths)
    paths = vision.webcam_vector()

    if not paths:
        print("[main] 추출된 경로가 없습니다.")
        return

    # 2. G-code 생성
    #    - feedrate: 28BYJ-48 안전 범위 ~800 mm/min
    #    - z_feedrate: 펜 up/down 속도
    gcode.generate_gcode(
        paths,
        filename=GCODE_FILE,
        feedrate=800,
        z_feedrate=300,
        pen_up_z=5.0,
        pen_down_z=0.0,
        return_home=True,
    )

    # 3. 아두이노 전송 (필요 시 주석 해제)
    # gcode.send_to_arduino(GCODE_FILE, port="COM3", baud=115200)


if __name__ == "__main__":
    main()
