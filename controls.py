import time
import numpy as np
import logging
import cv2
import threading
from typing import List
from PIL import Image
from socket import timeout
import urllib

from commands import RobotCommands
from direction import Direction

class RobotController():
    def __init__(self, *args, **kwargs):
        self.robot_cmd = RobotCommands.getInstance(*args, **kwargs)
        self.stop_command = [0,0,0,0,0,0]
        self.init_commands = ["BAT", "GET_SSID", "VIDEO_FLIP", "VIDEO_MIRROR", "ACEAA", "BCQAA", "CCIAA", "INIT_ALL"]
        self.logger = logging.getLogger("Robot Controller")
        for cmd in self.init_commands:
            self.robot_cmd.send_single_command_to_robot(cmd, 0)
        self.logger.info('Initialized robot')
        self.curr_image = None
        self.update_image()

    def update_joint_states(self):
        self.robot_cmd.update_joint_states()
    
    def get_joint_states(self):
        return self.robot_cmd.get_joint_states()
    
    def send_joint_command_to_robot(self, jointValues):
        self.robot_cmd.send_joint_command_to_robot(jointValues)

    def stop(self, milliseconds:float = 0):
        if milliseconds > 0:
            time.sleep(milliseconds/1000)
        
        self.robot_cmd.send_joint_command_to_robot(self.stop_command)

    def wait(self, milliseconds:float):
        if milliseconds > 0:
            time.sleep(milliseconds/1000)

    def rotate(self, direction: Direction, power:float, steps=1):
        wheels_command = [0.0, 0.0]
        if direction == Direction.LEFT or direction == Direction.CCW:
            wheels_command = [-power, power]
        if direction == Direction.RIGHT or direction == Direction.CW:
            wheels_command = [power, -power]
        
        self.logger.info("sending the rotate to {} for {} steps".format(direction.name, steps))

        for i in range(steps):
            self.robot_cmd.send_joint_command_to_robot(wheels_command)
            time.sleep(.5)
        
        self.robot_cmd.send_joint_command_to_robot([0.0, 0.0])

    def move(self, direction: Direction, power:float, steps: int):
        wheels_command = [0.0, 0.0]
        if direction == Direction.FORWARD:
            wheels_command = [power, power]
        if direction == Direction.BACKWARD:
            wheels_command = [-power, -power]
        
        self.logger.info("sending the Move {} for {} steps".format(direction.name, steps))

        for i in range(steps):
            self.robot_cmd.send_joint_command_to_robot(wheels_command)
            time.sleep(.5)
        
        self.robot_cmd.send_joint_command_to_robot([0.0, 0.0])

    def goto_position(self, joints: List[int]):
        self.robot_cmd.send_robot_to_goal(goal=joints)

    def open_gripper(self):
        self.robot_cmd.send_joint_command_to_robot([0, 0, 0, 0, 0, 1])
        time.sleep(2)

    def close_gripper(self):
        self.robot_cmd.send_joint_command_to_robot([0, 0, 0, 0, 0, 100])
        time.sleep(2)    

    def toggle_claw_led(self):
        response = self.robot_cmd.send_single_command_to_robot("CLAW_LED_STATE", 1)
        if response['response'] == "ON":
            self.robot_cmd.send_single_command_to_robot("LIGHT_OFF", 1)
        else:
            self.robot_cmd.send_single_command_to_robot("LIGHT_ON", 1)

    def pick(self):
        self.robot_cmd.send_robot_to_goal([100, 67, 48, 1])
        self.robot_cmd.close_gripper()
        self.robot_cmd.send_robot_to_goal([90, 67, 48, 100])

    def place(self):
        self.robot_cmd.send_robot_to_goal([65, 67, 48, 100])
        self.move(Direction.FORWARD, 25, 2)
        self.robot_cmd.open_gripper()
        self.move(Direction.BACKWARD, 25, 2)
        self.robot_cmd.send_robot_to_goal([100, 67, 48, 1])
    
    def send_robot_to_center(self, goal):
         self.robot_cmd.send_robot_to_center(goal=goal)

    def get_image(self):
        im = self.get_latest_image()
        while im is None:
            time.sleep(1)
            im = self.get_latest_image()
        return im
    
    def get_image_cv2(self):
        return cv2.imdecode(self.curr_image, cv2.IMREAD_COLOR)

    def get_latest_image(self):
        if self.curr_image is None:
            return None
        opencv_im = cv2.imdecode(self.curr_image, cv2.IMREAD_COLOR)
        return Image.fromarray(cv2.cvtColor(opencv_im, cv2.COLOR_BGR2RGB))

    def update_image(self):
        # download the image, convert it to a NumPy array, and then read
        # it into OpenCV format
        try:
            resp = urllib.request.urlopen("http://192.168.99.1/ajax/snapshot.jpg", timeout=0.2)
            latest_image = np.asarray(bytearray(resp.read()), dtype="uint8")
            self.curr_image = np.copy(latest_image)

            threading.Timer(0.2, self.update_image).start()
            # return Image.fromarray(self.latest_image)
        
        except timeout:
            self.logger.debug("updating camera frame request timed out ... skipping")
            threading.Timer(0.2, self.update_image).start()
        except Exception as e:
            threading.Timer(0.2, self.update_image).start()         
