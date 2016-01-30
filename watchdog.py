#!/usr/bin/python2
# coding=utf-8

import datetime as dt
from threading import Thread
from time import sleep

from I2C_controller import MCP23017Controller, repr_binary


# takes an address
# starts a thread when start is called; continuously watches the device for a high and sets it low
class Watchdog(MCP23017Controller):
    def __init__(self, address, delay = 0.1):
        super(Watchdog, self).__init__(address)
        self.running = False
        self.device_activation_time = dict()
        self.thread = None
        self.delay = delay

    def add_devices(self, devices):
        pass  # todo: add device time start to check if devices get turned off too quickly
        # IO with I2C is done automair, so in the case that a new alue is written, and another value came in at the same
        # time as that writing. The value that came in will not be registered by the program.
        # should change it to a model where only one gets turned off and not the entire port

    # looks for any port not null, and turns it off.
    # In between it measures the time the device has been on
    def check_port(self, port):
        data = self.read_port(port)
        if data != 0:
            start_time = dt.datetime.now()
            print("\n[+] port {} is turned on: {}".format(port, repr_binary(data)))
            try:
                self.write_port(port, 0)
            except Exception:
                print("[-] watchdog write error on port: {}".format(port))
            end_time = dt.datetime.now()
            elapsed_milliseconds = (end_time - start_time).microseconds / 1000
            print("[+] port {} turned off in: {} ms".format(port, elapsed_milliseconds))

    # repeatedly calls check_port on the two ports until running is set to False
    def watch(self):
        self.running = True
        while self.running == True:
            sleep(self.delay)
            self.check_port('a')
            self.check_port('b')

    # sets running to False and tries to write 0 to both ports
    def stop(self):
        self.running = False
        try:
            self.write_port('a', 0)
            self.write_port('b', 0)
        except:
            print("[-] watchdog write error")

    def run(self):
        print("[+] watchdog thread started")
        print("[+] watching address: " + repr(self.device_address))
        self.watch()

    # start a new thread which runs the function run
    def start(self):
        self.thread = Thread(target=self.run)
        self.thread.start()


if __name__ == '__main__':
    Watchdog(0x20).start()
