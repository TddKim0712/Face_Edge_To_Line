## 펜 플로터 머신 main.py
## 2026 SIOR spring 홍보부스용
## edited: 02/28/2026

## Entry Point
# 1. 웹캠으로 얼굴 벡터 추출 (mm 좌표)
# 2. G-code 파일 생성
# 3. (선택) USB 시리얼로 아두이노에 전송

"""
Pipeline

camera
→ vision
→ normalize
→ planning
→ gcode
→ serial_sender (arduino or other serial HW)
"""

## main.py

import vision
import gcode
import polar
import hardware.serial_sender as ss, hardware.calibration_collector as cc


# MODE = "CALIBRATION"
MODE = "DRAW"


GCODE_FILE = "robot_drawing.gcode"


def main():

    if MODE == "CALIBRATION":

        cc.run_collector()
        return


    if MODE == "DRAW":

        paths = vision.webcam_vector()

        if not paths:
            print("no paths")
            return

        # 극좌표 시각화 (원형 종이 회전 + 펜 이동 애니메이션)
        polar.polar_preview(paths)

        # 극좌표 G-code 생성
        polar.generate_polar_gcode(paths, filename=GCODE_FILE)

        ss.send_gcode(GCODE_FILE)


if __name__ == "__main__":
    main()