#!/usr/bin/env pybricks-micropython
import time
from threading import Thread

import ujson
import urequests
from pybricks.ev3devices import Motor, ColorSensor
from pybricks.parameters import Port, Stop, Direction
from pybricks.tools import wait

# Initialize the motors
belt_motor = Motor(Port.D, Direction.COUNTERCLOCKWISE)
catch_motor = Motor(Port.C, Direction.CLOCKWISE)
catch_motor.reset_angle(0)
join_motor = Motor(Port.A, Direction.COUNTERCLOCKWISE)

# Initialize the sensors
color_sensor = ColorSensor(Port.S1)

# Initialize the constants
BLACK = 'Color.BLACK'
RED = 'Color.RED'
WHITE = 'Color.WHITE'
YELLOW = 'Color.YELLOW'
colors = {BLACK: 0, RED: 1, WHITE: 2, YELLOW: 3}

# Initialize variables
is_running = False
object_list = []
run_join_belt = None

# Load settings
settings_file = open("/home/robot/Smart-Warehouse-Machine/settings.json")
settings = ujson.load(settings_file)
settings_file.close()

# Message header
headers = {"Content-type": "application/json"}


def watch_color():
    global is_running
    global object_list

    def check_same_stamp(object_buffer, time):
        if len(object_buffer) == 0:
            return False

        last_stamp = object_buffer[-1]

        if time - last_stamp >= 1:
            return False

        return True

    color_buffer = []
    saw_black = True

    while is_running:
        color = str(color_sensor.color())
        if color in (YELLOW, RED, WHITE):
            saw_black = False

            if len(color_buffer) != 0 and color_buffer[-1] != color:
                color_buffer = []
                continue
            else:
                color_buffer.append(color)
                if not saw_black and (len(color_buffer)) < 20:
                    continue

            if saw_black or not check_same_stamp(object_list, time.time()):
                object_list.append(time.time())
                color_buffer = []

        elif color == BLACK:
            saw_black = True


def catch_object():
    global is_running
    global object_list
    global run_join_belt

    while is_running:
        if len(object_list) > 0:

            if time.time() - object_list[0] < 1.4:
                wait(10)
                continue
            else:
                wait(500)

            print("catching object")
            print("object_count :", len(object_list))
            print()

            catch_motor.run_angle(200, -30, Stop.COAST, True)

            message = ujson.dumps({"sender": 24,
                                   "title": "Sending Check",
                                   "msg": ''}).encode()

            while is_running:
                res = urequests.post(settings['edge_repository_address'] + '/api/message/',
                                     data=message, headers=headers)
                if res.status_code == 201:
                    print("releasing object")
                    print()
                    break
                wait(1000)

            if not is_running:
                break

            print("releasing object")
            print()

            catch_motor.run_angle(200, 30, Stop.COAST, True)
            run_join_belt = time.time()

            del object_list[0]


def join_object():
    global is_running
    global run_join_belt

    while is_running:
        if run_join_belt is not None and time.time() - run_join_belt > 0.4:
            join_motor.run_time(400, 3000)
            run_join_belt = None


def sensory():
    global is_running

    def collect_sensor_values():
        current_time = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
        colors_rgb = color_sensor.rgb()

        sensory_values = ujson.dumps([{"sensorID": "r3_m_belt_position",
                                       "value": belt_motor.angle(),
                                       "datetime": current_time},
                                      {"sensorID": "r3_m_catch_position",
                                       "value": catch_motor.angle(),
                                       "datetime": current_time},
                                      {"sensorID": "r3_m_join_position",
                                       "value": join_motor.angle(),
                                       "datetime": current_time},
                                      {"sensorID": "r3_s_color_value_r",
                                       "value": colors_rgb[0],
                                       "datetime": current_time},
                                      {"sensorID": "r3_s_color_value_g",
                                       "value": colors_rgb[1],
                                       "datetime": current_time},
                                      {"sensorID": "r3_s_color_value_b",
                                       "value": colors_rgb[2],
                                       "datetime": current_time}]).encode()

        urequests.post(settings['edge_repository_address'] + '/api/sensory/', data=sensory_values,
                       headers=headers)

    while is_running:
        collect_sensor_values()
        wait(settings['sensory_frequency'])


def initialize_threads():
    return [Thread(target=sensory), Thread(target=watch_color), Thread(target=catch_object), Thread(target=join_object)]


message = ujson.dumps({"sender": 24,
                       "title": "Running Check"}).encode()
threads = []

while True:
    res = urequests.post(settings['edge_repository_address'] + '/api/message/', data=message, headers=headers)
    if res.status_code == 201 and not is_running:
        print("start")
        print()

        sensed_color = None
        sensor_distance = 0
        car_at_start = True
        object_list = []
        object_color = None

        threads = initialize_threads()
        for thread in threads:
            thread.start()
        belt_motor.run(180)
        is_running = True

    elif res.status_code == 201:
        pass


    elif res.status_code == 204 and is_running:
        print("stop")
        print()
        is_running = False
        belt_motor.hold()

    elif res.status_code == 204:
        belt_motor.hold()

    wait(1000)
