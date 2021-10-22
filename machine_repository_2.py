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

# Initialize the sensors
color_sensor = ColorSensor(Port.S1)

# Initialize the constants
BLACK = 'Color.BLACK'
RED = 'Color.RED'
WHITE = 'Color.WHITE'
YELLOW = 'Color.YELLOW'
colors = {BLACK: 0, RED: 1, WHITE: 2, YELLOW: 3}

# Initialize variables
saw_object = False
object_list = []

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


def watch_color():
    def _watch_color():
        def check_same_stamp(object_buffer, time):
            if len(object_buffer) == 0:
                return False

            last_stamp = object_buffer[-1]

            if time - last_stamp >= 1:
                return False

            return True

        color_buffer = []
        saw_black = True

        while True:
            color = str(color_sensor.color())
            if color in (YELLOW, RED, WHITE):
                saw_black = False

                if len(color_buffer) != 0 and color_buffer[-1] != color:
                    color_buffer = []
                    continue
                else:
                    color_buffer.append(color)
                    if not saw_black and len(color_buffer) < 20:
                        continue

                if saw_black or (not check_same_stamp(object_list, time.time())):
                    object_list.append(time.time())
                    color_buffer = []

            elif str(color) == BLACK:
                saw_black = True

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

                if (time.time() - saw_time) < 1.4:
                    wait(10)
                    continue
                else:
                    wait(500)

                print("catching object..")
                print("object_count :", len(object_list))
                print()

                del object_list[0]

                catch_motor.run_angle(200, -30, Stop.COAST, True)

                message = {"sender": 23,
                           "title": "Sending Check",
                           "msg": ''}

                while True:
                    res = urequests.post(settings['edge_repository_address'] + '/api/message/', data=message).json()
                    if res.status == 201:
                        print("releasing object..")
                        print()
                        break
                    print("shipment full..")
                    wait(1000)

                catch_motor.run_angle(200, 30, Stop.COAST, True)

                del object_list[0]

    catch_object_thread = Thread(target=_catch_object)
    catch_object_thread.start()

    return catch_object_thread


def sensory():
    def _sensory():
        def collect_sensor_values():
            current_time = time.time()

            def motor_position(motor):
                motor.position * (360 / motor.count_per_rot)

            sensory_values = [{"sensorID": "mr1m_belt_position",
                               "value": motor_position(belt_motor),
                               "datetime": current_time},
                              {"sensorID": "mr1m_catch_position",
                               "value": motor_position(catch_motor),
                               "datetime": current_time},
                              {"sensorID": "mr2s_color_value_h",
                               "value": color_sensor.color().h,
                               "datetime": current_time},
                              {"sensorID": "mr2s_color_value_s",
                               "value": color_sensor.color().s,
                               "datetime": current_time},
                              {"sensorID": "mr2s_color_value_v",
                               "value": color_sensor.color().v,
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
           watch_color(),
           catch_object()]

while True:
    pass
