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
BLUE = 'Color.BLUE'
colors = {BLACK: 0, RED: 1, WHITE: 2, YELLOW: 3, BLUE: 4}

# Initialize variables
is_running = False
sensed_color = None
sensor_distance = 0
car_at_start = True
object_list = []
object_color = None

# Load settings
settings_file = open("/home/robot/Smart-Warehouse-Machine/settings.json")
settings = ujson.load(settings_file)
settings_file.close()

# Message header
headers = {"Content-type": "application/json"}


def watch_object():
    global is_running
    global object_list
    global sensor_distance

    def not_in_list():
        cond1 = len(object_list) == 0
        cond2 = len(object_list) > 0 and time.time() - object_list[-1] > 1.5

        return cond1 or cond2

    object_buffer = []
    saw_belt = None
    wait_for_belt = False

    while is_running:
        distance = distance_sensor.distance()
        sensor_distance = min(59, distance)

        if sensor_distance > 56:
            object_buffer = []
            saw_belt = time.time()

            if wait_for_belt:
                print("two object now")
                object_list = [time.time() - 5] * 2

            wait_for_belt = False

        elif 30 < sensor_distance < 52 and not_in_list() and not wait_for_belt:
            if len(object_buffer) < 30:
                if len(object_buffer) > 0 and time.time() - object_buffer[0] > 0.5:
                    object_buffer = []

                object_buffer.append(time.time())
                continue

            object_buffer = []
            object_list.append(time.time())

            if time.time() - saw_belt > 1:
                wait_for_belt = True


def catch_object():
    global is_running
    global object_list
    global car_at_start

    while is_running:
        if len(object_list) > 0:
            print("doing catch")
            saw_time = object_list[0]

            if (time.time() - saw_time) < 1.0:
                continue
            else:
                wait(500)

            print("catching object")
            print("object_count :", len(object_list))
            print()

            del object_list[0]

            catch_motor.run_angle(200, -25, Stop.COAST, True)

            wait(1000)
            while not car_at_start:
                wait(50)

            catch_motor.run_angle(200, 25, Stop.COAST, True)


def watch_color():
    global is_running
    global object_color
    global object_list
    global sensed_color

    color_buffer = []

    while is_running:
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


def divide_object():
    global is_running
    global object_color
    global car_at_start
    global sensed_color

    while is_running:
        if object_color is None:
            continue

        print("dividing object")
        print("object_color :", object_color)
        print()

        car_at_start = False
        sensed_color = None

        wheel_motor.position = 0
        wait(900)
        wheel_motor.run_angle(200, 95, Stop.COAST, True)

        message = ujson.dumps({"sender": 21,
                               "title": "Check Capacity",
                               "msg": colors[object_color]}).encode()

        while is_running:
            res = urequests.post(settings['edge_classification_address'] + '/api/message/', data=message,
                                 headers=headers)
            if res.status_code == 201:
                print("repository available")
                print()
                break
            wait(1000)

        if not is_running:
            break

        direction = int(res.text)
        if direction == 2:  # right direction
            divide_motor.run_angle(200, 450, Stop.COAST, True)
        elif direction == 0:  # left direction
            divide_motor.run_angle(200, -460, Stop.COAST, True)
        else:
            pass

        wheel_motor.run_angle(250, 500, Stop.COAST, True)
        wait(100)

        if direction == 2:
            divide_motor.run_angle(200, -450, Stop.COAST, True)
        elif direction == 0:
            divide_motor.run_angle(200, 460, Stop.COAST, True)
        else:
            pass

        car_at_start = True
        object_color = None


def sensory():
    global is_running

    def collect_sensor_values():
        current_time = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
        colors_rgb = color_sensor.rgb()

        sensory_values = ujson.dumps([{"sensorID": "c_m_belt_position",
                                       "value": belt_motor.angle(),
                                       "datetime": current_time},
                                      {"sensorID": "c_m_catch_position",
                                       "value": catch_motor.angle(),
                                       "datetime": current_time},
                                      {"sensorID": "c_m_wheel_position",
                                       "value": wheel_motor.angle(),
                                       "datetime": current_time},
                                      {"sensorID": "c_m_divide_position",
                                       "value": divide_motor.angle(),
                                       "datetime": current_time},
                                      {"sensorID": "c_s_color_value_r",
                                       "value": colors_rgb[0],
                                       "datetime": current_time},
                                      {"sensorID": "c_s_color_value_g",
                                       "value": colors_rgb[1],
                                       "datetime": current_time},
                                      {"sensorID": "c_s_color_value_b",
                                       "value": colors_rgb[2],
                                       "datetime": current_time},
                                      {"sensorID": "c_s_distance_value",
                                       "value": distance_sensor.distance(),
                                       "datetime": current_time}]).encode()

        urequests.post(settings['edge_classification_address'] + '/api/sensory/', data=sensory_values,
                       headers=headers)

    while is_running:
        collect_sensor_values()
        wait(settings['sensory_frequency'])


def initialize_threads():
    return [Thread(target=sensory), Thread(target=watch_object), Thread(target=catch_object),
            Thread(target=watch_color), Thread(target=divide_object)]


message = ujson.dumps({"sender": 21,
                       "title": "Running Check",
                       "msg": ''}).encode()
threads = []

while True:
    res = urequests.post(settings['edge_classification_address'] + '/api/message/', data=message, headers=headers)
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
