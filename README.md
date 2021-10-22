# Smart-Warehouse-Machine

## Overall Description

The LEGO EV3 device only serves the one single code at a time. Therefore, this repository contains the codes for each
single machine.

There are 3 kinds of EV3s.

* `machine_classification.py`
* `machine_repository_*.py`
* `machine_shipment.py`

## Common Parts
To achieve the multi-task EV3, we used the `Thread`. For each functionality, a single thread processes it.

Every machine has a conveyor belt, color sensor, and catcher.
The conveyor belt moves the item through the belt with `run_belt()`.
You can set the speed of belt by modifying `settings.json`.
The color sensor senses the color of the item, send it to the edge, and get the direction of the edge server.
Basically, in this project, we used red, white, and yellow.
The catcher holds the item at the end of the belt to prevent the processing without any directions of edge server.

## Repository Machine
Repository machine has unique conveyor belt, `join`.
It allows items to join at one conveyor belt - shipment.

Repository Device uses 3 EV3s because they are classified into three colors.
The relationship between the color, device num, file name is as follows.
|Color|Repository Device Num|File Name|
|-------|-----|-----|
|Red|1|`machine_repository_1.py`|
|White|2|`machine_repository_2.py`|
|Yellow|3|`machine_repository_3.py`|

## Classification and Shipment Machine
Classification and shipment machine has ultrasonic sensor and dividing unit.
Ultrasonic sensor is for observing the location of the items.
Dividing unit is for distribute the items based on the proper destination.

## Run the machines
### Prerequisite
* LEGO EV3 (Installed based on the manual)
* Micropython 1.9.4
* brickrun 1.2.1
* pybricks 3.0
### Running Manual
1. Clone this repository `git clone https://github.com/2021-SE-Lab-Mindstorm-Project/Smart-Warehouse-Machine`
2. Move to `Smart-Warehouse-Machine`
3. `brickrun -r /home/robot/Smart-Warehouse-Machine/*.py"`


