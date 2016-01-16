#!/usr/bin/python2
# coding=utf-8

import time
from I2C_controller import MCP23017Controller

class watchdog(MCP23017Controller):
    def __init__(self, address):
        self.address = address

    def watch(self):
        data_a = self.read_port('a')
        data_b = self.read_port('b')

        if data_a != 0:
            self.write_port('a', 0)
        if data_b != 0:
            self.write_port('b', 0)

    def run(self):
        while(True):
            self.watch()






