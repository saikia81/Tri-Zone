#!/usr/bin/python2
# coding=utf-8

# game drivers are already instantiated. They have an update method which should limit their update time to that of the
# game loop, however this is not implemented everywhere, but should still be used for consistency
# reading and writing happens with a game component
# turn_on_component(component_name) is used to activate a component
# input is handled with an event system, which can get events that have been discovered
# These events should be collected by the Game in a loop, and handled with their relevant function
#
# get an event, and activate the appropriate function from the event handler code
# variables relevant to the state of the game will be kept in the game object instantiated by Pinball
# Pinball is used as a way to access the game and

import time
import logging
from logging.config import fileConfig

logger = logging.getLogger()
fileConfig('logger.conf', defaults={'logfilename': 'Tri-Zone.log'})
from game_components import lights, solenoids, switches, game_components, switch_matrix, display_controller
from game_components import solenoid_controller, switch_controller, light_controller

# globals
switch_controller.start_listening()


# event handler
# shares a queue with a listening controller
class EventHandler(object):
    def __init__(self, controller):
        self.controller = controller
        self.event_queue = controller.get_event_queue()

    def get_event(self):
        event = self.event_queue.get()
        try:
            column, row = event
            event_component = game_components[switch_matrix[column][row]]  # all events are switches
            logger.debug("event found by event_handler: " + repr(event_component))
            return event_component
        except KeyError:
            logger.error("[-] a component was not found, info: {}".format(str(event)))
            return None

    # adds address
    def put_event(self, component):
        self.event_queue.put(component.address)

    def has_event(self):
        return not self.event_queue.empty()


event_handler = EventHandler(switch_controller)



# this part is the actual game rules and working
# it includes the Game class which has the main loop, and event classes
# als includes all the functions that change the game state depending on the logical rules of the game
# each event is assigned to an game function
# note on expanding:
# If, when expanding this, too many functions start calling eachother, change the game_methods implementation
# the logic would otherwise get too complicated to debug. However some might not be scared to end up in callstack limbo

# yeah the logic...
# this is needed for events that generate no action or consequence,
# why they exist might be unknown at the time
def do_nothing(game):
    pass


# game methods
def add_credit(game):
    game.credit_amount += 1


# loops to the next player choice, when 4 has been reached, it resets to 0
def change_player_amount(game):
    game.player_amount += 1
    if game.player_amount > 4:
        game.player_amount = 0


# freezes the game, but doesn't disable the flippers, these are not controllable without additional hardware
# 6 seconds might be enough to save a ball
def freeze(game):
    time.sleep(6)


# when the tilts get too many notifications in the time specified below, the game freezes
def tilt(game):
    return
    print("Tilt registerer")
    if game.last_tilt_time is None:
        logger.info("tilt registered")
        game.last_tilt_time = time.time()
        return
    if 1.5 < (time.time() - game.last_tilt_time) < 2.5:  # adjust values to realistic tilt time
        logger.info("tilt excess registered")
        print("tilt excess registered")
        freeze(game)
    game.last_tilt_time = time.time()


# there isn't a way to see your score
# will be implemented once scores can be displayed
def reset_highscore(game):
    pass


# free ball at 15,000 points
def free_ball(game):
    game.free_ball_given = False
    game.ball_amount += 1 # value range is [0,1]


def score_light(game):
    # first turn off all lights
    for score_ in xrange(1000, 11000, 1000):
        lights[str(score_) + ' BONUS'].turn_off()

    # turn on the right light
    score = game.score
    if score < 1000:
        return
    elif score >= 10000:
        lights['10000 BONUS'].turn_on()
    else:
        # this figures out the score light for the range 1000 to 9000
        light_name = str(score / 1000 * 1000) + ' BONUS'
        lights[light_name].turn_on()


# should be called every tick
# looks if the score should activate anything
def check_score(game):
    score = game.score
    if score >= 15000:
        if not game.free_ball_given:
            free_ball(game)
# solenoids generally don't need turning off, since there is a watchdog turning them off
def activate_outhole(game):
    game.ball_amount -= 1  # when the outhole detects a ball, the ball is removed from game
    if game.ball_amount >= 1:
        solenoids['Ball Release'].turn_on()
    #game.timed_activate(game_components['Ball Release'], 1000, 'on')


def top_jet_bumper(game):
    solenoids['Top Jet Bumper'].turn_on()
    game.score += 500


def left_jet_bumper(game):
    solenoids['Left Jet Bumper'].turn_on()
    game.score += 500


def right_jet_bumper(game):
    solenoids['Right Jet Bumper'].turn_on()
    game.score += 500


def top_jet_bumper(game):
    light = lights['TOP JET BUMPER']
    if light:  # light is True or False depending on it's state (on, off)
        light.turn_off()
    else:
        light.turn_on()
        event_handler.add_event(light)
    game.score += 500


def right_standup(game):
    game.score += 200

def bottom_right_standup(game):
    game.score += 200


def left_standup(game):
    game.score += 200


def bottom_left_standup(game):
    game.score += 200


# might use multithreading for the lights, or implement a general light flashing possibility
# also could just limit the update speed
# this code might give a impression of using too many different functions, but taking into account
# the need to add functions, and change the game mechanics this amount of functions will be needed, maybe even more
def top_a_rollover(game):
    light = lights['TOP "A"']
    if light:  # light is True or False depending on it's state (on, off)
        light.turn_off()
    else:
        light.turn_on()
        event_handler.add_event(light)
    game.score += 1000


def top_b_rollover(game):
    lights['TOP "B"'].turn_on()
    game.score += 1000


def spinner(game):
    game.score += 200


def roll_over(game, letter):
    light = lights[letter]
    if light:  # light is True or False depending on it's state (on, off)
        light.turn_off()
    else:
        light.turn_on()
        event_handler.add_event(light)
    game.score += 1000


def t_roll_over(game):
    roll_over(game, 'T')


def r_roll_over(game):
    roll_over(game, 'R')


def i_rollover(game):
    roll_over(game, 'I')


def drop_target(game, letter):
    lights[letter].turn_on()
    game.score += 200


def z_drop_target(game):
    drop_target(game, 'Z')


def o_drop_target(game):
    drop_target(game, 'O')


def n_drop_target(game):
    drop_target(game, 'N')


def e_drop_target(game):
    drop_target(game, 'E')


def series(game):
    game.score += 2000
    for letter in 'ZONE':
        solenoids['"{}" Drop Target Reset'.format(letter)].turn_on()

def right_outside_rollover(game):
    game.score += 500


def left_inside_rollover(game):
    game.score += 500


def left_outside_rollover(game):
    game.score += 500


def right_inside_rollover(game):
    game.score += 1000


def right_kicker(game):
    solenoids["Right Kicker"].turn_on()


def left_kicker(game):
    solenoids["Left Kicker"].turn_on()


def eject_hole(game):
    solenoids['Eject Hole'].turn_on()


# uses all the names in the switch objects dictionary (game_components.switches.keys())
# added are some custom events
game_methods = {'PLUMB BOB TILT': tilt, 'BALL ROLL TILT': tilt, 'CREDIT BUTTON': change_player_amount,
                'RIGHT COIN SWITCH': add_credit, 'CENTER COIN SWITCH': add_credit, 'LEFT COIN SWITCH': add_credit,
                'SLAM TILT': tilt, 'HIGH SCORE RESET': reset_highscore, 'OUTHOLE': activate_outhole,
                'TOP "A" ROLLOVER': top_a_rollover, 'TOP "B" ROLLOVER': top_b_rollover, 'LEFT STANDUP': do_nothing,
                'TOP JET BUMPER': top_jet_bumper, 'LEFT JET BUMPER': left_jet_bumper,
                'RIGHT JET BUMPER': right_jet_bumper, '"O" DROP TARGET': o_drop_target,
                'RIGHT STANDUP': right_standup, '"R" ROLLOVER': r_roll_over, '"I" ROLLOVER': i_rollover,
                '"E" DROP TARGET': e_drop_target, 'BOTTOM RIGHT STANDUP': bottom_right_standup,
                'RIGHT OUTSIDE ROLLOVER': right_outside_rollover, 'RIGHT INSIDE ROLLOVER': right_inside_rollover,
                'RIGHT KICKER': right_kicker, 'EJECT HOLE': eject_hole, 'LEFT KICKER': left_kicker,
                'LEFT INSIDE ROLLOVER': left_inside_rollover, 'LEFT OUTSIDE ROLLOVER': left_outside_rollover,
                'BOTTOM LEFT STANDUP': bottom_left_standup, '"Z" DROP TARGET': z_drop_target, 'SPINNER': spinner,
                '"T" ROLLOVER': t_roll_over, '"N" DROP TARGET': n_drop_target, 'PLAYFIELD TILT': tilt,
                '"ZONE" DROP TARGET SERIES': series
                }


# this class is in place to act as a handler for starting games and playing multiplayer mode
# this implements accepting payment and player selection
class Pinball(object):
    def __init__(self):
        self.players = []
        self.credits = 2  # gotta have some credit
        self.active_game = None

    def new_game(self, ball_amount, player_amount):
        if self.active_game != None:
            self.players.append(self.active_game)
        game = Game(ball_amount, player_amount)
        self.active_game = game
        game.start()

    def start(self):
        for cred in xrange(self.credits):
            logger.info("\ngame: player {}!")
            self.new_game(4, event_handler)
            self.credits -= 1


# game main class
# all game parts will come together here
class Game(object):
    def __init__(self, ball_amount, handler=event_handler):
        self.event_history = []
        self.score = 1000  # todo: change to 0, debug value is 1000
        self.ball_amount = ball_amount
        self.last_tilt_time = None  # don't let it be pushed too many times
        self.tilt_amount = 0
        self.game_has_ended = False
        self.event_handler = handler  # see EventHandler
        self.delayed_deactivate = []
        self.delayed_activate = []
        self.free_ball_given = False
        series(self)

    def __repr__(self):
        return "game: ball amount: {}, score: {}".format(self.ball_amount, self.score)

    def check_end(self):
        if self.ball_amount == 0:
            self.game_has_ended = True

    def timed_action(self, component, delay_time, action):
        if action == 'off':
            self.delayed_deactivate.append((component, time.time() + delay_time))
        elif action == 'on':
            self.delayed_activate.append((component, time.time() + delay_time))
        else:
            logger.error("component delay action erroneous: {}".format(action))

    def check_delayed_components(self):
        now = time.time()  # lowering the amount of times the time is called
        for component, activation_time in self.delayed_deactivate:
                if activation_time >= now:
                    component.turn_off()
        for component, activation_time in self.delayed_activate:
                if activation_time >= now:
                    component.turn_on()

    def check_event(self):
        event = event_handler.get_event()

        if event is None:
            return None
        logger.info("game: event: " + repr(event))
        self.event_history.append((event, time.time()))
        print("event debug: " + str(event))
        game_methods[event.name](self)  # calls an appropriate function for the event

    def start(self):
        series(self) # reset solenoids at start of the game
        i = 0 # loop debugging
        while not self.game_has_ended:
            #debugging
            print("loop " + str(i))
            if not event_handler.has_event():
                logger.info("game: waiting for event...")


            logger.info("score: {}".format(str(self.score)))  # log the score

            # get and handle event+`
            try:
                self.check_event()
            except Exception as ex:
                logger.critical("couldn't get event: {}".format(ex.message))

            # hadnles components that should be turned off or on later
            self.check_delayed_components()
            check_score(self)
            self.check_end()
            display_controller.set_score(self.score)

            # updating all controllers every (few) game tick
            solenoid_controller.update()
            switch_controller.update()
            light_controller.update()
            display_controller.update()
            i += 1
            time.sleep(0.5)  # limiting to sleeptime (1=1s|0.1=100ms)
            # might need replacing with a delta time calculation
            # this is the reverse of ticks per second (ticks/s=1/sleeptime)
            # this should be adjusted too take into account speed at which events are generated


if __name__ == '__main__':
    Game(2).start()
