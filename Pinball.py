#!/usr/bin/python2
# coding=utf-8

class Pinball(object):
    def __init__(self, solenoid_controller_address, switch_controller_address, light_controller_address):
        self.solenoid_controller_address = solenoid_controller_address
        self.switch_controller_address = switch_controller_address
        self.light_controller_address = light_controller_address
        self.game = None

    def new_game(self, ball_amount, player_amount):
        self.game = Game(ball_amount, player_amount)


class Game(object):
    def __init__(self, ball_amount, player_amount):
        self.ball_amount == ball_amount
        self.player_amount

    def start(self):
        pass

    def update(self):
        pass
