#!/usr/bin/python2
# coding=utf-8

from I2C_controller import MCP23017Controller
import time

# tools
# fill in a 8x8 matrix of addresses an names
def fill_compontent_matrix():
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

def ComponentsController(MCP23017Controller):
    def __init_(self, address, name):
        super(ComponentsController, self).__init__(address)

        self.column_value = 0
        self.row_value = 0

    def turn_on_component(self, component):
        self.turn_on_address(component.address)


def SolenoidController(ComponentsController):
    def __init__(self, address, name):
        super(SolenoidController, self).__init__(address)
        self.set_IO_mode('output')
        self.port0 = 'a'
        self.port2 = 'b'

    def turn_on_address(self, light_address):
        column, row = light_address

        column_value = self.column_value + 2**column
        row_value = self.row_value + 2**row

        self.write_port_byte(column, column_value)
        self.write_port_byte(row, row_value)



def LightController(ComponentsController):
    def __init__(self, address ):
        super(SolenoidController, self).__init__(address)
        self.set_IO_mode('output')
        self.port1 = 'a'
        self.port2 = 'b'

    def turn_on_address(self, light_address):
        column, row = light_address

        column_value = self.column_value + 2**column
        row_value = self.row_value + 2**row

        self.write_port_byte(column, column_value)
        self.write_port_byte(row, row_value)


def SwitchController(ComponentsController):
    def __init__(self, address, name ):
        super(SolenoidController, self).__init__(address, name)
        self.set_IO_mode('input')
        self.column_port = 'A'
        self.row_port = 'B'

    def turn_on_address(self, light_address):
        column, row = light_address

        column_value = self.column_value + 2**column
        row_value = self.row_value + 2**row

        self.write_port_byte(column, column_value)
        self.write_port_byte(row, row_value)


#lights, solenoids, and switches are treated as component objects
def Component(Object):
    def __init__(self, name, address):
        if type(address) in [tuple, list] and 0 < len(address) < 3:
            raise ValueError("address must be a tuple or list with length: 1 or 2")
        self.name = name
        self.address = address

lights = []
solenoids = []
switches = []

def Light(Component):
    pass


def Solenoid(Component):
    pass


def Switch(Component):
    pass

for light_name in light_names:
    if light_name == 'NOT USED':
        continue
    light = Light(light_name, component_address[light_name])
    lights.append(light)

for switch_name in switch_names:
    if switch_name == 'NOT USED':
        continue
    switch= Switch(switch_name, component_address[switch_name])
    switches.append(switch)

for solenoid_name in solenoid_names:
    if solenoid_name == "NOT USED":
        continue
    solenoid = Solenoid(solenoid_name, component_address[solenoid_name])
    solenoids.append(solenoid)
