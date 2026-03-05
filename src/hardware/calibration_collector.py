## calibration_collector.py
## joystick calibration data collector

import csv
from hardware import serial_manager


def run_collector():

    ser = serial_manager.get_serial()

    data = []

    print("calibration collector started")

    while True:

        line = ser.readline().decode().strip()

        if not line:
            continue

        print("[arduino]", line)

        if line.startswith("REC_STOP"):

            _, dx, dy, px, py = line.split()

            px = float(px)
            py = float(py)

            actual_x = float(input("actual x mm : "))
            actual_y = float(input("actual y mm : "))

            data.append([px,py,actual_x,actual_y])

        if line == "save":

            with open("calibration.csv","w",newline="") as f:

                writer = csv.writer(f)

                writer.writerow([
                    "pred_x",
                    "pred_y",
                    "real_x",
                    "real_y"
                ])

                writer.writerows(data)

            print("calibration saved")