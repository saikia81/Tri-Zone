#!/usr/bin/python2
# coding=utf-8

# todo: add device time start to check if devices get turned off too quickly
# IO with I2C is done atomic, so in the case that a new value is written, and another value came in at the same
# time as that writing, and is gone before writing is done. The value that came in will not be registered by the program.
# this depends on how the chip handles reading, it might keep a value longer, and there shouldn't be anything
# that has to be read in such a small time frame. However with python not knowing parallel execution of code (the GIL)
# this might pose as a limitation in our watchdog. (this is relevant for other classes as well!
#   note: this is a very small limitation, and probably won't be a problem, unless the program becomes very slow
#   or the requirements ask for more speed, at the moment no inspection has been done on the program speed
# should add a model where only one bit gets turned off and not the entire 8-bit
import logging
from logging.config import fileConfig
SOLENOID_CONTROLLER_ADDRESS = 0x20
logger = logging.getLogger()
fileConfig('logger.conf', defaults={'logfilename': 'Tri-Zone.log'})

import datetime as dt
from threading import Thread
from time import sleep

from I2C_controller import MCP23017Controller, repr_binary


# takes an address
# starts a thread when start is called; continuously watches the device for a high and sets it low at a choosen speed
#   note: limiting the speed makes it's interval between reads higher (value should probably never bee higher than 1s)
#         if this number gets higher it might interfere with the activation of other solenoids
class Watchdog(MCP23017Controller):
    def __init__(self, address, delay = 0.2):
        super(Watchdog, self).__init__(address)
        self.running = False
        self.device_activation_time = dict()
        self.thread = None
        self.delay = delay  # read speed for finding devices that are on.
        self.exception_list = []
        self.set_io_mode('output', ['A', 'B'])

    def add_devices(self, devices):
        raise NotImplementedError()

    # todo: make the list actually mean something (in other words: implement this)
    # choose out a bit, you don't want written to
    def add_exception_addresses(self, exception_list):
        self.exception_list = exception_list

    # looks for any port not null, and turns it off.
    # In between it measures the time the device has been on
    def check_port(self, port):
        data = self.read_port(port)
        if data != 0:
            try:
                self.set_io_mode('output', ['A', 'B'])
            except Exception as ex:
                logger.debug(ex)
            start_time = dt.datetime.now()
            logger.info("watchdog: port {} is turned on: {}".format(port, repr_binary(data)))
            try:
                # wait time untill output is set low (value should probably not be higher than 1)
                sleep(0.5)
                # if interference with other solenoids is detected, try adding a read statement here
                self.write_port(port, 0)
            except Exception:
                logger.critical("watchdog: write error on port: {}".format(port))
            end_time = dt.datetime.now()
            elapsed_milliseconds = (end_time - start_time).microseconds / 1000
            logger.info("watchdog: port {} turned off in: {}ms".format(port, elapsed_milliseconds))

    # repeatedly calls check_port on the two ports until running is set to False
    def watch(self):
        self.running = True
        while self.running:
            sleep(self.delay)
            self.check_port('a')
            self.check_port('b')

    # sets running to False and tries to write 0 to both ports
    def stop(self):
        self.running = False
        try:
            self.write_port('a', 0)
        except:
            logger.critical("watchdog: write error on port a")

        try:
            self.write_port('b', 0)
        except:
            logger.critical("watchdog: write error on port b")

    def run(self):
        logger.info("watchdog thread started")
        logger.info("watching address: " + repr(self.device_address))
        self.watch()

    # start a new thread which runs the function run
    def start(self):
        self.thread = Thread(target=self.run, name='Watchdog listener')
        self.thread.start()


if __name__ == '__main__':
    import sys
    arg = sys.argv[1:]
    if len(arg) > 0:
        try:
            address = int(arg)
        except Exception:
            address = 0x20
    else:
        address = 0x20

    try:
        Watchdog(address).start()
    except Exception:
        pass
