## 펜 플로터 머신 serial_sender.py
## 2026 SIOR spring 홍보부스용
## edited: 03/05/2026

## serial_sender
## G-code 전송 전용 모듈
## arduino UNO 사용
# Digital Pin 2,3,4,5 / 6,7,8,9 / 10,11,12,13 --> 각각 corresponding to X,Y,Z stepper motor drive IN(1,2,3,4) 

"""
PC → Arduino G-code streaming

Arduino firmware 조건
    각 명령 처리 후 'ok' 응답
"""
## serial_sender.py
## G-code streaming

from hardware import serial_manager


def wait_ready():

    ser = serial_manager.get_serial()

    while True:

        line = ser.readline().decode().strip()

        if line:

            print("[arduino]", line)

        if line == "ready":
            break


def send_gcode(filename):

    ser = serial_manager.get_serial()

    with open(filename, encoding="utf-8") as f:
        lines = f.readlines()

    wait_ready()

    for raw in lines:

        line = raw.strip()

        if not line or line.startswith(";"):
            continue

        cmd = line.split(";")[0].strip()

        ser.write((cmd + "\n").encode())

        while True:

            resp = ser.readline().decode().strip()

            if resp == "ok":
                break

            if resp.startswith("error"):
                print(resp)
                return