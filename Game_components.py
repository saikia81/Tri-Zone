#!/usr/bin/python2
# coding=utf-8
import time
from Queue import Queue
from threading import Thread

from I2C_controllers import MCP23017Controller


# tools
# fill in a 8x8 matrix of addresses an names
def fill_component_matrix():
    matrix = list()
    for column in xrange(0, 8):
        matrix.append(list())
        for row in xrange(0, 8):
            matrix[column].append('NOT USED')

    for column in xrange(0, 8):
        for row in xrange(0, 8):
            name = raw_input('(' + repr(column + 1) + ',' + repr(row + 1) + ') > ')
            matrix[column][row] = name if name != "" else matrix[row][column]
    print matrix
    return matrix


# make 1-dimension from 2-dimenions
def collapse_2dimensional_list(two_dim_list):
    new_list = []
    for column in range(len(two_dim_list)):
        for row in range(len(two_dim_list)):
            new_list.append(two_dim_list[column][row])
    return new_list


# doesn't actually fix anything
# returns new row and column values
def turn_bit_on(column_value, row_value, address):
    address_column, address_row = 2 ** address[0], 2 ** address[1]
    if column_value & address_column == 0:
        column_value += address_column
    if row_value & address_row == 0:
        row_value += address_row
    return column_value, row_value


def turn_bit_off(column_value, row_value, address):
    address_column, address_row = 2 ** address[0], 2 ** address[1]

    if column_value & address_column == 0 or row_value & address_row == 0:
        return column_value, row_value

    if address_row ^ row_value != 0:
        column_value -= address_column

    if address_column ^ column_value != 0:
        row_value -= address_row

    return column_value, row_value


# globals
# bus address for the MCP23017's
SOLENOID_DEVICE_ADDRESS = 0x20
LIGHT_DEVICE_ADDRESS = 0x21
SWTICH_DEVICE_ADDRESS = 0x22

# light and switch matrixes, and solenoid list corresponding with the component address
# solenoids are not in a matrix, thus the address is directly related to there position in the list
# lights and switches address is build up from their row and column position
light_matrix = [
    ['NOT USED', '1000 BONUS', '2000 BONUS', '3000 BONUS', '4000 BONUS', '5000 BONUS', '6000 BONUS', '7000 BONUS'],
    ['8000 BONUS', '9000 BONUS', 'NOT USED', '10000 BONUS', 'X2', 'X3', 'X4', 'X5'],
    ['T', 'R', 'I', 'Z', 'O', 'N', 'E', '"tri" SCORES 3000'],
    ['"tri" SCORES 5000', '"tri" SCORES 10000', '"tri" SCORES EXTRA BALL', '"tri" SCORES SPECIAL', 'LEFT SPECIAL',
     'RIGHT SPECIAL', 'SAME PLAYER SHOOTS AGAIN', 'SPINNER'],
    ['"1"', '"2"', '"3"', '"4"', 'NOT USED', 'TOP JET BUMPER', 'LEFT JET BUMPER', 'BOTTOM JET BUMPER'],
    ['TOP "A"', 'TOP "B"', 'BOTTOM "A"', 'BOTTOM "B"', 'TOP JET BUMPER', 'EJECT HOLE 10000', 'NOT USED', 'NOT USED'],
    ['6000 BONUS', '1 CAN PLAY', '2 CAN PLAY', '3 CAN PLAY', '4 CAN PLAY', 'MATCH', 'BALL IN PLAY', 'CREDITS'],
    ['#1 PLAYER UP', '#2 PLAYER UP', '#3 PLAYER UP', '#4 PLAYER UP', 'TILT', 'GAME OVER', 'SAME PLAYER SHOOTS AGAIN',
     'HIGH SCORE TO DATE']]

solenoid_names = ['Ball Release', 'Eject Hole', '"Z" Drop Target Reset', 'O" Drop Target Reset',
                  '"N" Drop Target Reset', '"E" Drop Target Reset', 'NOT USED', 'NOT USED', 'NOT USED', 'NOT USED',
                  'NOT USED', 'NOT USED', 'NOT USED', 'Credit Knocker', 'Not Used', 'Coin Lockout', 'Top Jet Bumper',
                  'Left Jet Bumper', 'Bottom Jet Bumper', 'Left Kicker', 'Right Kicker', 'Not Used']

switch_matrix = [
    ['PLUMB BOB TILT', 'BALL ROLL TILT', 'CREDIT BUTTON', 'RIGHT COIN SWITCH', 'CENTER COIN SWITCH', 'LEFT COIN SWITCH',
     'SLAM TILT', 'HIGH SCORE RESET'],
    ['OUTHOLE', 'TOP "A" ROLLOVER', 'TOP "B" ROLLOVER', 'LEFT STANDUP', 'TOP JET BUMPER', 'LEFT JET BUMPER',
     'RIGHT JET BUMPER', '"O" DROP TARGET'],
    ['RIGHT STANDUP', '"R" ROLLOVER', '"I" ROLLOVER', '"E" DROP TARGET', 'BOTTOM RIGHT STANDUP',
     'RIGHT OUTSIDE ROLLOVER', 'RIGHT INSIDE ROLLOVER', 'RIGHT KICKER'],
    ['EJECT HOLE', 'LEFT KICKER', 'LEFT INSIDE ROLLOVER', 'LEFT OUTSIDE ROLLOVER', 'BOTTOM LEFT STANDUP',
     '"Z" DROP TARTGET', 'SPINNER', '"T" ROLLOVER'],
    ['"N" DROP TARGET', 'PLAYFIELD TILT', '"ZONE" DROP TARGET SERIES', 'BOTTOM LEFT STANDUP', 'NOT USED', 'NOT USED',
     'NOT USED', 'NOT USED'],
    ['LEFT COIN SWITCH', 'LEFT JET BUMPER', 'RIGHT OUTSIDE ROLLOVER', '"Z" DROP TARTGET', 'NOT USED', 'NOT USED',
     'NOT USED', 'NOT USED'],
    ['SLAM TILT', 'RIGHT JET BUMPER', 'RIGHT INSIDE ROLLOVER', 'SPINNER', 'NOT USED', 'NOT USED', 'NOT USED',
     'NOT USED'],
    ['HIGH SCORE RESET', '"O" DROP TARGET', 'RIGHT KICKER', '"T" ROLLOVER', 'NOT USED', 'NOT USED', 'NOT USED',
     'NOT USED']]

light_names = collapse_2dimensional_list(light_matrix)
switch_names = collapse_2dimensional_list(switch_matrix)

# all component addresses dictionary (lookup), uses name lists/matrixes to build
component_address = {}  # every item has an address

for column_number, column in enumerate(light_matrix):
    for row_number, name in enumerate(column):  # every row
        component_address[name] = (column_number, row_number)

for column_number, column in enumerate(switch_matrix):
    for row_number, name in enumerate(column):  # every row
        component_address[name] = (column_number, row_number)

for index, name in enumerate(solenoid_names):
    component_address[name] = index

# controllers for the solenoids, lights, and switches
solenoides_column = 0
solenoides_row = 0
lightes_column = 0
lightes_row = 0
switches_column = 0
switches_row = 0


class ComponentsController(MCP23017Controller):
    def __init_(self, address):
        super(ComponentsController, self).__init__(address)

        self.column_value = 0
        self.row_value = 0


class InputController(ComponentsController):
    def __init__(self, address):
        super(InputController, self).__init__(address)
        self.set_IO_mode('output')
        self.column_port = 'a'
        self.row_por = 'b'
        self.running = False
        self.event_queue = Queue()

    def get_event_queue(self):
        return self.event_queue

    def read(self):
        pass

    def start_listening(self):
        thread = Thread(target=self.listen)
        thread.start()

    def listen(self):
        self.running = True
        while self.running == True:
            self.read()
            time.sleep(0.1)

    def stop_listening(self):
        self.running = False


class OutputController(ComponentsController):  # fix dependency issue: lights and solenoids
    def __init__(self, address):
        super(OutputController, self).__init__(address)
        self.set_IO_mode('output')
        self.port0 = 'a'
        self.port1 = 'b'
        self.change = True

    # accepts a GameComponent; uses it's address to turn the solenoid
    def turn_on(self, game_component):
        self.turn_on_address(game_component.address)


class SolenoidController(OutputController):
    def __init__(self, address):
        super(SolenoidController, self).__init__(address)
        self.port0_value = 0
        self.port1_value = 0
        self.port0 = 'a'
        self.port1 = 'b'

    def update(self):
        if not self.change: return  # small speed boost, if needed change port a, and b seperately
        self.write_port(self.port0, self.port0_value)
        self.write_port(self.port1, self.port1_value)
        self.change = False

    def turn_off_address(self, address):
        if 0 > address > 16:
            raise ValueError("[-] address has to be 0 to 15, instead address: {}".format(address))
        address_value = 2 ** address if address <= 8 else 2 ** (address - 8)

        if address <= 8:
            if self.port0_value & address_value:
                self.port0_value -= address_value
                change = True
        else:
            if self.port1_value & address_value << 8:
                self.port1_value -= address_value
                change = True

    def turn_on_address(self, address):
        if 0 > address > 16:
            raise ValueError("[-] address has to be 0 to 15, instead address: {}".format(address))
        address_value = 2 ** address if address <= 8 else 2 ** (address - 8)

        if address <= 8:
            if not self.port0_value & address_value:
                self.port0_value += address_value
                change = True
        else:
            if not self.port1_value & address_value << 8:
                self.port1_value += address_value
                change = True


class LightController(OutputController):
    def __init__(self, address):
        super(LightController, self).__init__(address)
        self.column_value = 0
        self.row_value = 0
        self.column_port = 'a'
        self.row_port = 'b'

    def update(self):
        if not self.change: return
        self.write_port(self.row_port, self.row_value)
        self.write_port(self.column_port, self.column_value)
        self.change = False

    def turn_off_address(self, address):
        column, row = address

        if 0 > column > 8 or 0 > row > 8:
            raise ValueError("[-] column and row have to be 0 to 8, instead\nrow: {}\ncolumn: {}".format(row, column))

        self.column_value, self.row_value = turn_bit_off(self.column_value, self.row_value, address)
        change = True

    def turn_on_address(self, address):
        column, row = address

        if 0 > column > 8 or 0 > row > 8:
            raise ValueError("[-] column and row have to be 0 to 8, instead\nrow: {}\ncolumn: {}".format(row, column))

        self.column_value, self.row_value = turn_bit_on(self.column_value, self.row_value, address)
        change = True


class SwitchController(InputController):
    pass


# lights, solenoids, and switches are treated as component objects
def device_dictionary_factory(device_names, class_object):
    device_dic = dict()
    for device_name in device_names:
        if device_name == 'NOT USED':
            continue
        device = Light(device_name, component_address[device_name])
        device_dic[device_name] = device
    return device_dic


class GameComponent(object):
    def __init__(self, name, address):
        if type(address) not in [tuple, list] or 0 > len(address) > 3:
            raise ValueError("address must be a tuple or list with length: 1 or 2")
        self.name = name
        self.address = address


# device types and instantiation
class Light(GameComponent):
    pass


class Solenoid(GameComponent):
    pass


class Switch(GameComponent):
    pass


# the devices are accessed by their name
lights = device_dictionary_factory(light_names, Light)
solenoids = device_dictionary_factory(solenoid_names, Solenoid)
switches = device_dictionary_factory(switch_names, Switch)
all_devices = dict().update(lights).update(solenoids).update(switches)

if __name__ == '__main__':
    solenoid_controller = SolenoidController(0x20)
    for solenoid in solenoids:
        solenoid_controller.turn_on(solenoid)
