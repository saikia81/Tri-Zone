#!/usr/bin/python2
# coding=utf-8

import pinball
from watchdog import Watchdog

SOLENOID_CONTROLLER_ADDRESS = 0x20
SWITCH_CONTROLLER_ADDRESS = 0x21
LIGHT_CONTROLLER_ADDRESS = 0X22

if __name__ == '__main__':
    watchdog = Watchdog(SOLENOID_CONTROLLER_ADDRESS)
    watchdog.start()

    try:
        pinball = pinball.Pinball(SOLENOID_CONTROLLER_ADDRESS, SWITCH_CONTROLLER_ADDRESS, LIGHT_CONTROLLER_ADDRESS)
    except Exception as ex:
        print("[-] game crashed")
        print(ex.message)

    watchdog.stop()
