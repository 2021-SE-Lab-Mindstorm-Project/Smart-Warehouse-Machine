#!/usr/bin/env pybricks-micropython
import time
from threading import Thread

import ujson
import urequests
from pybricks.ev3devices import Motor, ColorSensor, UltrasonicSensor
from pybricks.parameters import Port, Stop, Direction
from pybricks.tools import wait

# Initialize the motors
belt_motor = Motor(Port.D, Direction.COUNTERCLOCKWISE)
catch_motor = Motor(Port.C, Direction.CLOCKWISE)
catch_motor.reset_angle(0)
wheel_motor = Motor(Port.A, Direction.COUNTERCLOCKWISE)
divide_motor = Motor(Port.B, Direction.CLOCKWISE)

# Initialize the sensors
color_sensor = ColorSensor(Port.S1)
distance_sensor = UltrasonicSensor(Port.S2)

# Initialize the constants
BLACK = 'Color.BLACK'
RED = 'Color.RED'
WHITE = 'Color.WHITE'
YELLOW = 'Color.YELLOW'
colors = {BLACK: 0, RED: 1, WHITE: 2, YELLOW: 3}

# Initialize variables
sensed_color = None
sensor_distance = 0
car_at_start = True
object_list = []
object_color = None

# Load settings
settings_file = open("../../settings.json")
settings = ujson.loads(str(settings_file.readlines()))
settings_file.close()


def run_belt(value):
    def _run_belt(value):
        belt_motor.run(value)

    run_belt_thread = Thread(target=_run_belt, args=(value,))
    run_belt_thread.start()

    return run_belt_thread


def watch_object():
    def _watch_object():
        object_buffer = []
        global object_list
        global sensor_distance

        saw_belt = None
        wait_for_belt = False

        while True:
            distance = distance_sensor.distance()
            sensor_distance = min(59, distance)

            if sensor_distance < 56:
                object_buffer = []
                saw_belt = time.time()

                if wait_for_belt:
                    print("two object now..")
                    object_list = [time.time() - 5] * 2

            elif 30 < sensor_distance < 52 and (
                    len(object_list) == 0 or (time.time() - object_list[-1] > 1.5)) and not wait_for_belt:
                if len(object_buffer) < 30:
                    if len(object_buffer) > 0 and time.time() - object_buffer[0] > 0.5:
                        object_buffer = []

                    object_buffer.append(time.time())
                    continue

                object_buffer = []
                object_list.append(time.time())

                if time.time() - saw_belt > 1:
                    wait_for_belt = True

    watch_object_thread = Thread(target=_watch_object)
    watch_object_thread.start()

    return watch_object_thread


def watch_color():
    def _watch_color():
        global object_color
        global object_list
        global sensed_color

        color_buffer = []

        while True:
            color = str(color_sensor.color())

            if color in colors.keys():
                if color == BLACK:
                    color_buffer = []
                elif len(color_buffer) != 0 and color_buffer[-1] != color:
                    color_buffer = []
                elif len(color_buffer) == 0:
                    color_buffer.append(color)
                elif len(color_buffer) < 15 and color_buffer[-1] == color:
                    color_buffer.append(color)
                elif len(color_buffer) >= 15:
                    object_color = color_buffer[-1]
                    sensed_color = color_buffer[-1]

            wait(10)

    watch_color_thread = Thread(target=_watch_color)
    watch_color_thread.start()

    return watch_color_thread


def catch_object():
    def _catch_object():
        global object_list
        global car_at_start

        while True:
            if len(object_list) > 0:

                saw_time = object_list[0]

                if (time.time() - saw_time) < 1.0:
                    continue
                else:
                    wait(500)

                print("catching object..")
                print("object_count :", len(object_list))
                print()

                del object_list[0]

                catch_motor.run_angle(200, -25, Stop.COAST, True)

                wait(1000)
                while not car_at_start:
                    wait(50)

                catch_motor.run_angle(200, 25, Stop.COAST, True)

    catch_object_thread = Thread(target=_catch_object)
    catch_object_thread.start()

    return catch_object_thread


def divide_object():
    def _divide_object():

        global object_color
        global car_at_start
        global sensed_color

        while True:
            if object_color is None:
                continue

            print("dividing object..")
            print("object_color :", object_color)
            print()

            car_at_start = False
            sensed_color = None

            wheel_motor.position = 0
            wait(900)
            wheel_motor.run_angle(200, 95, Stop.COAST, True)

            message = {"sender": 21,
                       "title": "Check Capacity",
                       "msg": {"item_type": colors[object_color]}}

            while True:
                res = urequests.post(settings['edge_classification_address'] + '/api/message/', data=message).json()
                if res.status == 201:
                    print("repository available..")
                    print()
                    break
                print("repository full..")
                wait(1000)

            if object_color == YELLOW:  # right direction
                divide_motor.run_angle(200, 455, Stop.COAST, True)
            elif object_color == RED:  # left direction
                divide_motor.run_angle(200, -465, Stop.COAST, True)
            else:
                pass

            wheel_motor.run_angle(250, 500, Stop.COAST, True)
            wait(100)

            if object_color == YELLOW:
                divide_motor.run_angle(200, -455, Stop.COAST, True)
            elif object_color == RED:
                divide_motor.run_angle(200, 465, Stop.COAST, True)
            else:
                pass

            car_at_start = True
            object_color = None

    divide_object_thread = Thread(target=_divide_object)
    divide_object_thread.start()

    return divide_object_thread


def sensory():
    def _sensory():
        def collect_sensor_values():
            current_time = time.time()

            def motor_position(motor):
                motor.position * (360 / motor.count_per_rot)

            sensory_values = [{"sensorID": "mcm_belt_position",
                               "value": motor_position(belt_motor),
                               "datetime": current_time},
                              {"sensorID": "mcm_catch_position",
                               "value": motor_position(catch_motor),
                               "datetime": current_time},
                              {"sensorID": "mcm_wheel_position",
                               "value": motor_position(wheel_motor),
                               "datetime": current_time},
                              {"sensorID": "mcm_divide_position",
                               "value": motor_position(divide_motor),
                               "datetime": current_time},
                              {"sensorID": "mcs_color_value_h",
                               "value": color_sensor.color().h,
                               "datetime": current_time},
                              {"sensorID": "mcs_color_value_s",
                               "value": color_sensor.color().s,
                               "datetime": current_time},
                              {"sensorID": "mcs_color_value_v",
                               "value": color_sensor.color().v,
                               "datetime": current_time},
                              {"sensorID": "mcs_distance_value",
                               "value": distance_sensor.distnace(),
                               "datetime": current_time}]

            urequests.post(settings['edge_classification_address'] + '/api/sensory/', data=sensory_values)

        while True:
            collect_sensor_values()
            wait(settings['sensory_frequency'])

    sensory_thread = Thread(target=_sensory)
    sensory_thread.start()

    return sensory_thread


threads = [sensory(),
           run_belt(settings['default_conveyor_belt_speed']),
           watch_object(),
           watch_color(),
           catch_object(),
           divide_object()]

while True:
    pass
