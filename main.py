#!/usr/bin/python2
# coding=utf-8

import sys
import logging
from logging.config import fileConfig

logger = logging.getLogger()
fileConfig('logger.conf', defaults={'logfilename': 'Tri-Zone.log'})

from watchdog import Watchdog

from pinball import Pinball, switch_controller

SOLENOID_CONTROLLER_ADDRESS = 0x20
watchdog = Watchdog(SOLENOID_CONTROLLER_ADDRESS)  # watchdog to make sure the solenoids don't stay on too long

def main():

    watchdog.start()


    pinball_game = Pinball()
    pinball_game.start()



if __name__ == '__main__':
    try:
        main()
    except Exception as ex:
        logger.critical(ex)

    switch_controller.stop_listening()
    watchdog.stop()
    exit()