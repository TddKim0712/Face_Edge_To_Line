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
from hardware import serial_sender, calibration_collector


MODE = "CALIBRATION"
# MODE = "DRAW"


GCODE_FILE = "robot_drawing.gcode"


def main():

    if MODE == "CALIBRATION":

        calibration_collector.run_collector()
        return


    if MODE == "DRAW":

        paths = vision.webcam_vector()

        if not paths:
            print("no paths")
            return

        gcode.generate_gcode(
            paths,
            filename=GCODE_FILE
        )

        serial_sender.send_gcode(GCODE_FILE)


if __name__ == "__main__":
    main()