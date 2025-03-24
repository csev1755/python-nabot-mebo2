# Nabot AI / Mebo 2.0 Python API

This repository contains code for controlling the **Nabot AI** and **Mebo 2.0** robots. Since the original developers of these robots appear to be inactive, I have forked this project to try and maintain it for those who are still interested.

## Installation

### 1. Create a Virtual Environment
```
python3 -m venv venv
```

### 2. Activate the Virtual Environment

#### Windows
```
venv\Scripts\activate
```

#### macOS / Linux
```
source venv/bin/activate
```

### 3. Install Dependencies
```
pip3 install -r requirements.txt
```

## Usage

To manually control the robot, ensure you are connected to it via WiFi, then run:
```
python3 manual_control.py
```
This will open two windows: one displaying the robot's camera feed and another for controlling the robot. Some occasional request timeouts may appear in the logs which is normal.

In addition to manual control, you can control the robot programmatically using the `NabotController` class found in `nabot_controller.py`.

### Example: Move the Robot
```python
from nabot_controller import NabotController
from direction import Direction

nabot = NabotController()
nabot.move(Direction.FORWARD, power=30, steps=2)
```

### Example: Retrieve Joint States
```python
from nabot_controller import NabotController

nabot = NabotController()
nabot.update_joint_states()
print(nabot.get_joint_states())
```
You can extend the `NabotController` class to add more functionalities as needed.

## Object Detection

Object detection allows the robot to analyze images and detect objects using a neural network.

### Example: Detect Objects in an Image
```python
from object_detector import ObjectDetector
from nabot_controller import NabotController

object_detector = ObjectDetector()
nabot = NabotController()
robot_image = nabot.get_image()

bounding_boxes, labels, confidences = object_detector.predict(robot_image)

for i in range(len(bounding_boxes)):
    print(f"Object {i + 1}:")
    print(f"  Label: {labels[i]}")
    print(f"  Bounding Box: {bounding_boxes[i]}")
    print(f"  Confidence: {confidences[i]:.2f}")
```
