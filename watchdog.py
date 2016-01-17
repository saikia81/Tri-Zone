#!/usr/bin/python2
# coding=utf-8

from threading import Thread
from time import sleep


from I2C_controller import MCP23017Controller



#takes an address
# starts a thread when start is called; continuously watches the device for a high and sets it low
class Watchdog(MCP23017Controller):
    def __init__(self, address):
        super(Watchdog, self).__init__(address)
        self.running = False

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
        print("[+] watchdog thread started")
        print("[+] watching address: " + repr(self.bus_address))
        running = True
        while(running == True):
            self.watch()
            sleep(0.1)

    def start(self):
         self.thread = Thread(target = self.run)
         self.thread.start()

if __name__ == '__main__':
    Watchdog(0x20).start()

