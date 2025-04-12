# Nabot AI / Mebo 2.0 Python Module

This repository contains a Python module along with some examples of controlling **Nabot AI** and **Mebo 2.0** robots.  

This project is inspired by <https://github.com/meborobot/letsrobot-mebo> and is originally forked from <https://github.com/Ximpatico/NabotPythonAPI>. Both of these projects seem to be abandoned and are each missing functionality and/or proper documentation. The goal for this project is to expose all functionality of the original Mebo along with the Nabot AI in one easy to use module. Thank you to the contributers of both of these repositories as they were able to give me lots of good information. 

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

## Examples

### Move the Robot
```python
import mebo2_nabot

robot = mebo2_nabot.Robot()
robot.forward(power=30, steps=2)
```

### Retrieve Joint Positions
```python
import mebo2_nabot

robot = mebo2_nabot.Robot()
print(robot.get_joint_positions())
```

### GUI Control

To control the robot with a GUI, ensure ffplay/ffmpeg is installed then run:
```
python3 examples/graphical_interface.py
```
This will open two windows: one displaying the robot's camera feed and another for controlling the robot.
