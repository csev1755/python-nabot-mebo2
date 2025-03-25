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

In addition to manual control, you can control the robot programmatically using the `RobotController` class found in `controls.py`.

### Example: Move the Robot
```python
from controls import RobotController
from direction import Direction

robot = RobotController()
robot.move(Direction.FORWARD, power=30, steps=2)
```

### Example: Retrieve Joint States
```python
from controls import RobotController

robot = RobotController()
robot.update_joint_states()
print(robot.get_joint_states())
```

## Object Detection

Object detection allows the robot to analyze images and detect objects using a neural network.

You can try out this funcitonality by running:

```
python3 object_detector.py
```

The `ObjectDetector` class can be used separately as well.

### Example: Detect Objects in an Image
```python
from object_detector import ObjectDetector
from controls import RobotController

object_detector = ObjectDetector()
robot = RobotController()
robot_image = robot.get_image()

bounding_boxes, labels, confidences = object_detector.predict(robot_image)

for i in range(len(bounding_boxes)):
    print(f"Object {i + 1}:")
    print(f"  Label: {labels[i]}")
    print(f"  Bounding Box: {bounding_boxes[i]}")
    print(f"  Confidence: {confidences[i]:.2f}")
```
