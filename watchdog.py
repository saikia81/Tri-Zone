#!/usr/bin/python2
# coding=utf-8

import threading
import time

from I2C_controller import MCP23017Controller

running = False

class Watchdog(MCP23017Controller):
    def watch(self):
        data_a = self.read_port('a')
        data_b = self.read_port('b')

        if data_a != 0:
            print("[+] port a is turned on: " + repr(data_a))
            self.write_port('a', 0)
            print("[+] port a turned off")
        if data_b != 0:
            print("[+] port b is turned on: " + repr(data_b))
            self.write_port('b', 0)
            print("[+] port b turned off")

    def stop(self):
        global running
        running = False
        self.write_port('a', 0)
        self.write_port('b', 0)

    def run(self):
        global running
        running = True
        while(running == True):
            self.watch()

    def start(self):
        self.run()

if __name__ == '__main__':
    Watchdog(0x20).run()

