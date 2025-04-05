# Nabot AI / Mebo 2.0 Python Module

This repository contains a Python module along with some examples of controlling **Nabot AI** and **Mebo 2.0** robots.

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

### 3. Install Module
```
pip3 install .
```

### 4. Install Example Dependencies
```
pip3 install -r examples/requirements.txt
```

## Usage

To control the robot with a GUI, ensure ffplay/ffmpeg is installed then run:
```
python3 examples/graphical_interface.py
```
This will open two windows: one displaying the robot's camera feed and another for controlling the robot.

You can control the robot programmatically using the `RobotController` class found in `controls.py`.

### Example: Move the Robot
```python
from mebo2_nabot import RobotController

robot = RobotController()
robot.forward(power=30, steps=2)
```

### Example: Retrieve Joint States
```python
from mebo2_nabot import RobotController

robot = RobotController()
robot.update_joint_states()
print(robot.get_joint_states())
```
