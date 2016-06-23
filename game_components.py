#!/usr/bin/python2
# coding=utf-8
import time
import sys
import math
import logging
from logging.config import fileConfig
logger = logging.getLogger()
fileConfig('logger.conf', defaults={'logfilename': 'Tri-Zone.log'})
from Queue import Queue
from threading import Thread

from I2C_controller import MCP23017Controller, repr_binary  # todo: change controllertester

# tools
# fill in a 8x8 matrix of addresses and names
def fill_component_matrix():
    matrix = list()
    # first fills everything with 'NOT USED'
    for column in xrange(0, 8):
        matrix.append(list())
        for row in xrange(0, 8):
            matrix[column].append('NOT USED')

    for column in xrange(0, 8):
        for row in xrange(0, 8):
            name = raw_input('(' + repr(column + 1) + ',' + repr(row + 1) + ') > ')
            matrix[column][row] = name if name != "" else matrix[row][column]
    print(matrix)
    return matrix


# collapses a two dimensional list
def collapse_matrix(two_dim_list):
    new_list = []
    for column in xrange(len(two_dim_list)):
        for row in xrange(len(two_dim_list)):
            new_list.append(two_dim_list[column][row])
    return new_list

# all component addresses dictionary (lookup)
# uses name matrixes to build
def component_address_dictionary_factory(*matrixes):
    component_addresses = {}
    for matrix in matrixes:
        for column_number, column in enumerate(matrix):
            for row_number, name in enumerate(column):  # every row
                component_addresses[name] = (column_number, row_number)
    return component_addresses

# turn a bit on inside a 8-bit address
# takes the address (a number from 0 to 7) and turns the bit corresponding on the given port_value
def turn_bit_on(address, port_value):
    if address > 7:
        address_value = (2 ** address) >> 8
    else:
        address_value = 2 ** address

    if port_value & address_value == 0:
            port_value += address_value
    return port_value

def turn_bit_off(address, port_value):
    if address > 7:
        address_value = (2 ** address) >> 8
    else:
        address_value = 2 ** address

    if port_value & address_value:
            port_value -= address_value
    return port_value

# todo: make matrix functions dependent on turn_bit_on or change function used in light- and switchcontroller
# returns new row and column values
def add_matrix_address(column_value, row_value, address):
    address_column, address_row = 2 ** address[0], 2 ** address[1]
    if column_value & address_column == 0:
        column_value += address_column
    if row_value & address_row == 0:
        row_value += address_row
    return column_value, row_value

# returns new row and column values
def remove_matrix_address(column_value, row_value, address):
    address_column, address_row = 2 ** address[0], 2 ** address[1]
    if column_value & address_column == 0 or row_value & address_row == 0:
        return column_value, row_value
    if address_row ^ row_value != 0:
        column_value -= address_column
    if address_column ^ column_value != 0:
        row_value -= address_row
    return column_value, row_value


def make_event_list(row_value, prev_row_value, column_bit):
    event_list = []
    for i in xrange(8):
        row_bit = repr_binary(row_value)[::-1][i]
        prev_row_bit = repr_binary(prev_row_value)[::-1][i]
        if row_bit != prev_row_bit and row_bit != '0':
            event_list.append([column_bit, i])  # if value is 1 add the address of the bit to the list
    return event_list

# globals
# generally all component addresses consist of: (column, row)
# bus address for the MCP23017's
SOLENOID_CONTROLLER_ADDRESS = 0x20
SWITCH_CONTROLLER_ADDRESS = 0x21
LIGHT_CONTROLLER_ADDRESS = 0X22
DISPLAY_CONTROLLER_ADDRESS = 0x23


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

# testing where what really lies in the Tri-Zone machine
solenoid_names = ['Ball Release', 'Eject Hole', '"Z" Drop Target Reset', '"O" Drop Target Reset',
                  '"N" Drop Target Reset', '"E" Drop Target Reset','Credit Knocker', 'Coin Lockout', 'Top Jet Bumper',
                  'Left Jet Bumper', 'Bottom Jet Bumper', 'Left Kicker', 'Right Kicker']

switch_matrix = [
    ['PLUMB BOB TILT', 'BALL ROLL TILT', 'CREDIT BUTTON', 'RIGHT COIN SWITCH', 'CENTER COIN SWITCH', 'LEFT COIN SWITCH',
     'SLAM TILT', 'HIGH SCORE RESET'],
    ['OUTHOLE', 'TOP "A" ROLLOVER', 'TOP "B" ROLLOVER', 'LEFT STANDUP', 'TOP JET BUMPER', 'LEFT JET BUMPER',
     'RIGHT JET BUMPER', '"O" DROP TARGET'],
    ['RIGHT STANDUP', '"R" ROLLOVER', '"I" ROLLOVER', '"E" DROP TARGET', 'BOTTOM RIGHT STANDUP',
     'RIGHT OUTSIDE ROLLOVER', 'RIGHT INSIDE ROLLOVER', 'RIGHT KICKER'],
    ['NOT USED', 'NOT USED', 'NOT USED', 'NOT USED', 'NOT USED', 'NOT USED', 'NOT USED', 'NOT USED'],
    ['"N" DROP TARGET', 'PLAYFIELD TILT', '"ZONE" DROP TARGET SERIES', 'BOTTOM LEFT STANDUP', 'NOT USED', 'NOT USED',
     'NOT USED', 'NOT USED'],
    ['LEFT COIN SWITCH', 'LEFT JET BUMPER', 'RIGHT OUTSIDE ROLLOVER', '"Z" DROP TARGET', 'NOT USED', 'NOT USED',
     'NOT USED', 'NOT USED'],
    ['NOT USED', 'NOT USED', 'NOT USED', 'NOT USED', 'NOT USED', 'NOT USED', 'NOT USED', 'NOT USED'],
    ['EJECT HOLE', 'LEFT KICKER', 'LEFT INSIDE ROLLOVER', 'LEFT OUTSIDE ROLLOVER', 'BOTTOM LEFT STANDUP',
     '"Z" DROP TARGET', 'SPINNER', '"T" ROLLOVER']]

light_names = collapse_matrix(light_matrix)
switch_names = collapse_matrix(switch_matrix)

component_addresses = component_address_dictionary_factory(light_matrix, switch_matrix)

# solenoid list is already one-dimensional
component_addresses.update((key, value) for value, key in enumerate(solenoid_names))

#all component names, by address
solenoid_and_light_names = {value:key for key, value in component_addresses.items()} # reverse component_addresses

# controllers for the game components connected to a MCP23017
# might components become connected directly to a output pin or other device, the design of hierarchy
# will have to change
class ComponentController(MCP23017Controller):
    def __init_(self, address):
        super(ComponentController, self).__init__(address)
        # todo: get these vars out of here
        self.column_value = 0
        self.row_value = 0

    def __repr__(self):
        # todo: make this consistent with all three controllers
        return "controller {}".format(self.__name__)

# This class acts as an event generator
# when start_listening is called, it starts a thread which keeps looking for any address that constitutes an event
# An even exists as an address, this address should be possible to resolve in  in the
# since there is only one input driver needed, this one has all (except one read) functions
# however might the design change, move some of this code to a child class
class InputController(ComponentController):
    def __init__(self, address):
        super(InputController, self).__init__(address)
        self.column_port = 'a'
        self.row_port = 'b'
        self.port_mode(self.row_port, 'input')
        self.port_mode(self.column_port, 'output')
        self.running = False
        self.event_queue = Queue()
        self.prev_column_value = 0
        self.prev_row_value = 0
        self.change = False

    def get_event_queue(self):
        return self.event_queue

    def start_listening(self):
        thread = Thread(target=self.listen, name='InputController listener')
        logger.debug("started listening")
        thread.start()

    def listen(self):
        self.running = True
        logger.debug("entering loop")
        while self.running:
            self.read()

    def stop_listening(self):
        self.running = False


# This is a class to implement a output function wrapper, and is ont fit to control outputs on itself
# the wrapper functions are used to turn on components by giving
# to use the turn_on_component and turn_off_component methods there has to be a turn_on_address, and turn_off_address
# method implemented in the child class
class OutputController(ComponentController):
    def __init__(self, address):
        super(OutputController, self).__init__(address)
        self.set_io_mode('output')
        self.port0 = 'a'
        self.port1 = 'b'

    # accepts a GameComponent; uses it's address to turn the solenoid
    def turn_on_component(self, game_component):
        try:
            self.turn_on_address(game_component.address)
        except IOError:
            logger.critical("{} IOError writing to {}".format(self.__name__, game_component.name))

    def turn_off_component(self, game_component):
        try:
            self.turn_off_address(game_component.address)
        except IOError:
            logger.critical("{} IOError writing to {}".format(self.__name__, game_component.name))

class DisplayController(ComponentController):
    def __init__(self, address):
        super(DisplayController, self).__init__(address)
        self.running = False
        self.digits0 = [0] * 4
        self.digits1 = [0] * 4
        self.score = 0
        self.address_port = 'B'
        self.control_port = 'A'
        self.address_port_value = 0
        self.control_port_value = 0
        self.latch_pin = 1
        self.clock_pin = 2
        self.serial_pin = 4
        self.display_segments = {'.' : '11111110', 'mid' : 0b11111101, 'left_up': 0b11111011, 'left_down': 0b11110111,
                                 'down': 0b11101111, 'right_down': 0b11011111, 'right_up': 0b10111111, 'up': 0b01111111}
        self.number_values = [3, 243, 37, 13, 153, 73, 65, 31, 1, 9]

        try:
            self.init_device()
        except Exception as ex:
            logger.debug(ex)

    def init_device(self):
        self.write_reg(0,0) # low level init, redundancy in case of code changes...
        self.write_reg(1,0)

    def set_score(self, score):
        self.score = score

    def shift_out(self, number):
        latch_value = 0b10000000
        clock_value = 0b01000000
        serial_value = 0b00100000

        # write 2 bytes to shift register
        for bit in repr_binary(self.number_values[number]):
            control_byte = clock_value + (serial_value if bit == '1' else 0) # add serial bit, if the number_value bit is 1
            self.write_port(self.control_port, control_byte)
            self.write_port(self.control_port, control_byte - clock_value) # set clock low
        self.write_port(self.control_port, latch_value) # set latch high !!! moet hier wel een clock bij?

        # Marcel

    def update(self):
        pass

    def display(self):
        digits = list( '0'*(8 - len(str(self.score))) + str(self.score)) # makes a array of numbers based on the score
        for i in xrange(0, 4):
            digit0 = int(digits[i])
            digit1 = int(digits[i+4]) # take the digit for the second display
            self.shift_out(digit1) # reverse? not reverse? the questions...
            self.shift_out(digit0)
            self.write_port(self.address_port, 2**i + 2**(i+4)) # address selection      CHECK THIS FIRST! MY GOD, LOOK AT IT
            time.sleep(0.001)
            self.write_port(self.address_port, 0) # address selection      CHECK THIS FIRST! MY GOD, LOOK AT IT


    def runny(self):
        while self.running:
            self.display() # no delay!

    def start_running(self):
        self.running = True
        self.thread = Thread(target=self.runny, name='DisplayController listener')
        self.thread.start()

    def stop_running(self):
        self.running = False


# used to turn on and off solenoids
# uses solenoid.address
class SolenoidController(OutputController):
    def __init__(self, address):
        super(SolenoidController, self).__init__(address)
        self.port0_value = 0
        self.port1_value = 0
        self.port0 = 'a'
        self.port1 = 'b'
        self.change = False

    def init_device(self):
        self.write_reg(0,0)
        self.write_reg(1,0)

    # if the watchdog is implemented with update:
    # using the update for the solenoids will mean that solenoids will not interfere with eachother
    #   note: however this means they will turn on at the same time!
    def update(self):
        if not self.change: return
        # if needed possibly double speed: register change on port a, and b separately
        self.write_port(self.port0, self.port0_value)
        self.write_port(self.port1, self.port1_value)
        self.change = False

    # the way solenoid addresses work is here used to turn the component off on the IO-expander
    # address is turned into a value that sets a bit high in on of the 'port_value's (the bit pos is address)
    def turn_off_address(self, address):
        if 0 > address > 16:
            raise ValueError("address has to be 0 to 15, instead address: {}".format(address))

        port_value = turn_bit_off(address, self.port0_value if address < 8 else self.port1_value)

        if address < 8:
            self.port0_value = port_value
        else:
            self.port1_value = port_value

        self.change = True

    # the way solenoid addresses work is here used to turn the component on on the IO-expander
    def turn_on_address(self, address):
        if 0 > address > 16:
            raise ValueError("address has to be 0 to 15, instead address: {}".format(address))

        port_value = turn_bit_on(address, self.port0_value if address < 8 else self.port1_value)

        if address < 8:
            self.port0_value = port_value
        else:
            self.port1_value = port_value

        self.change = True


class LightController(OutputController):
    def __init__(self, address):
        super(LightController, self).__init__(address)
        self.column_value = 0
        self.row_value = 0
        self.column_port = 'A'
        self.row_port = 'B'
        self.change = False

    def init_device(self):
        self.write_reg(0, 0)
        self.write_reg(1, 0)

    def update(self):
        if not self.change: return
        self.write_port(self.row_port, self.row_value)
        self.write_port(self.column_port, self.column_value)
        self.change = False

    def turn_off_address(self, address):
        column, row = address

        if 0 > column > 8 or 0 > row > 8:
            raise ValueError("column and row have to be 0 to 8, instead\nrow: {}\ncolumn: {}".format(row, column))

        self.column_value, self.row_value = remove_matrix_address(self.column_value, self.row_value, address)
        self.change = True

    def turn_on_address(self, address):
        column, row = address

        if 0 > column > 8 or 0 > row > 8:
            raise ValueError("column and row have to be 0 to 8, instead\nrow: {}\ncolumn: {}".format(row, column))

        self.column_value, self.row_value = add_matrix_address(self.column_value, self.row_value, address)
        self.change = True

    def light_show(self):
        pass # todo: write light show


class SwitchController(InputController):
    def __init__(self, address):
        super(SwitchController, self).__init__(address)
        self.row_values = [0] * 8
        self.prev_row_values = [0] * 8
        self.change = False
        self.column_value = 0 # all on means the drive is low
        self.drive = 'B'
        self.input = 'A'
        self.set_io_mode('input', self.input)
        self.set_io_mode('output', self.drive)

    def init_device(self):
        self.write_reg(0,255)
        self.write_reg(1,0)

    def update(self):
        # let prev_row_values be assigned here, and the row value won't change faster than the update interval
        # of the game
        #   note: will have to adapt read!
        pass

    # sets the drive (column) pins on one for one, reads the input (row) byte for every drive pin
    def read(self):
        logger.debug("[d] -- switch read --")
        #logger.debug("[d] rows: {}".format(repr(self.row_values)))
        for column_bit in xrange(8):
            self.column_value = 2**column_bit # note: using powers means there's always one bit on
            self.write_port(self.drive, self.column_value)
            #logger.debug("column: {}".format(repr(self.column_value)))

            #logger.debug("port value: {} |actually: {}".format(repr_binary(255 - self.column_value), repr_binary(self.read_port(self.drive))))
            logger.debug("row value: {} |column value: ".format(repr(self.row_values[column_bit]), str(self.read_port(self.drive))))
            self.row_values[column_bit] = self.read_port(self.input)

            event_list = make_event_list(self.row_values[column_bit], self.prev_row_values[column_bit], column_bit)

            if len(event_list) > 0:
                logger.debug("event list: {}".format(repr(event_list)))

            self.prev_row_values[column_bit] = self.row_values[column_bit]

            for event in event_list:
                try:
                    self.event_queue.put_nowait(event)
                except Exception as ex:
                    logger.error("Queu might have become full! Event can't be added")
                    logger.critical(ex.message)
                    logger.critical("queue exception:\n{}".format(ex.message))
                logger.info("event put in queue: {}".format(switch_matrix[event[0]][event[1]]))


            #logger.debug("[d] input value: {} |drive address: {}".format(self.row_values[column_bit], column_bit))

# controllers are instantiated here, and can be controlled directly by importing them
# however it is preferred that the game components be used unless exception handling isn't a concern
switch_controller = SwitchController(SWITCH_CONTROLLER_ADDRESS)
light_controller = LightController(LIGHT_CONTROLLER_ADDRESS)
solenoid_controller = SolenoidController(SOLENOID_CONTROLLER_ADDRESS)
display_controller = DisplayController(DISPLAY_CONTROLLER_ADDRESS)



# takes a list of component names, and a class to instantiate components into a dictionary
# returns a dictionary with the name as key, and an instantiated component as value
# lights, solenoids, and switches are game_component objects
# any component with the name 'NOT USED' will not be instantiated or added to the dictionary
#   note: 'NOT USED' is the only valid exception (lower key values won't be affected)
def component_dictionary_factory(component_names_, class_object):
    component_dic = dict()
    for component_name in component_names_:
        if component_name == 'NOT USED':
            continue
        component = class_object(component_name, component_addresses[component_name])
        component_dic[component_name] = component
    return component_dic

# base class for the game components (lights, switches, solenoids)
# this class should not be used directly
# A controller has to be assigned in the child class instantiation
# turn_on_component must be implemented as well
# On extendability: this code can be used with different types of controllers
# the only requirement for a controller to work is that it implements the method turn_on_component
# This is a base class with wrapper methods for the output, and basic component methods
class GameComponent(object):
    def __init__(self, name, address, active=False):
        self.name = name
        self.active = active
        self.address = address
        self.controller = None

    def __repr__(self):
        return "gameComponent: {} on {} is {}".format(self.name, self.address, 'active' if self.active else 'inactive')

    def __str__(self):
        return self.name

    def __cmp__(self, other):
        return self.name == other.name

    # uses self.controller to turn a component on
    def turn_on(self):
        try:
            self.controller.turn_on_component(self)
            logger.info("gc: turned on: {}".format(self.name))
        except Exception as ex:
            logger.error("gc: {} while turning on '{}' on address: {}".format(type(ex), self.name, self.address))
        self.active = True

    # uses self.controller to turn a component off
    def turn_off(self):
        try:
            self.controller.turn_off_component(self)
            logger.info("gc: turned off: {}".format(self.name))
        except Exception as ex:
            logger.error("gc: {} while turning off '{}' on address: {}".format(type(ex), self.name, self.address))
        self.active = False


# game component types
class Light(GameComponent):
    def __init__(self, name, address, active = False):
        if type(address) not in [tuple, list] or 0 > len(address) > 3:
            raise ValueError("gc: address must be a tuple or list with length: 1 or 2")
        super(Light, self).__init__(name, address, active)  # super should always be called before any var assignment
        self.controller = light_controller

class Solenoid(GameComponent):
    def __init__(self, name, address, active = False):
        if type(address) != int and 0 <= address < 18:
            raise ValueError("gc: address must be a int 0 to 17")
        super(Solenoid, self).__init__(name, address, active) # super should always be called before any var assignment
        self.controller = solenoid_controller

class Switch(GameComponent):
    def __init__(self, name, address, active = False):
        if type(address) not in [tuple, list] or 0 > len(address) > 3:
            raise ValueError("gc: address must be a tuple or list with length: 1 or 2")
        super(Switch, self).__init__(name, address, active)  # super should always be called before any var assignment
        self.controller = switch_controller

# the components are accessed by their name
game_components = {}
lights = component_dictionary_factory(light_names, Light)
solenoids = component_dictionary_factory(solenoid_names, Solenoid)
print(solenoids)
switches = component_dictionary_factory(switch_names, Switch)
game_components.update(lights)
game_components.update(solenoids)
game_components.update(switches)

if __name__ == '__main__':
    SwitchController(0x21).start_listening()
    while True:
        pass
    exit()  # easily exclude code from running
    for light in lights.values():
        light.turn_on()

    #tests all solenoids, by setting them on
    if raw_input("gc: lookout! this will slowly turn on all solenoids, are you sure you want to continue?").lower() not in ['y','yes']:
        exit()
    for solenoid in solenoids.values():
        time.sleep(2)
        solenoid.turn_on()
        solenoid_controller.update()
        logger(repr(solenoid))