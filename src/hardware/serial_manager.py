## serial_manager.py
## Serial transport layer
## 모든 모듈이 이 객체를 공유

import serial
import config


_ser = None


def get_serial():

    global _ser

    if _ser is None:

        _ser = serial.Serial(
            config.SERIAL_PORT,
            config.SERIAL_BAUD,
            timeout=config.SERIAL_TIMEOUT
        )

    return _ser