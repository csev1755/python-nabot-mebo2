import time
import numpy as np
import logging
from typing import List

from commands import RobotCommands
from direction import Direction

class RobotController():
    robot_state = [0, 0, 0, 0] # arm, wrist_ud, wrist_rot, gripper
    robot_state_names = ["ARM_QUERY", "WRIST_UD_QUERY", "WRIST_ROTATE_QUERY", "CLAW_QUERY"]

    def __init__(self, *args, **kwargs):
        self.robot_cmd = RobotCommands.getInstance(*args, **kwargs)
        self.stop_command = [0,0,0,0,0,0]
        self.init_commands = ["BAT", "GET_SSID", "VIDEO_FLIP", "VIDEO_MIRROR", "ACEAA", "BCQAA", "CCIAA", "INIT_ALL"]
        self.logger = logging.getLogger("Robot Controller")
        for cmd in self.init_commands:
            self.robot_cmd.send_single_command_to_robot(cmd, 0)
        self.logger.info('Initialized robot')

    def update_joint_states(self):
        for cmd in self.robot_state_names:
            try:
                data = self.robot_cmd.send_single_command_to_robot(cmd, 0)
                aJsonString = data['response']
                if ("ARM" in aJsonString) and (len(aJsonString) >= 4):
                    self.robot_state[0] = int(aJsonString[4:])
                elif ("WRIST_UD" in aJsonString) and len(aJsonString) >= 9:
                    self.robot_state[1] = int(aJsonString[9:])
                elif ("WRIST_ROTATE" in aJsonString) and len(aJsonString) >= 13:
                    self.robot_state[2] = int(aJsonString[13:])
                elif ("CLAW" in aJsonString and len(aJsonString) >= 5):
                    self.robot_state[3] = int(aJsonString[5:])
            except:
                self.logger.warning("Error parsing robot's states")
    
    def get_joint_states(self):
        return self.robot_state
    
    def send_joint_command_to_robot(self, jointValues):
        self.robot_cmd.send_joint_command_to_robot_helper(jointValues)

    def stop(self, milliseconds:float = 0):
        if milliseconds > 0:
            time.sleep(milliseconds/1000)
        
        self.send_joint_command_to_robot(self.stop_command)

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
            self.send_joint_command_to_robot(wheels_command)
            time.sleep(.5)
        
        self.send_joint_command_to_robot([0.0, 0.0])

    def move(self, direction: Direction, power:float, steps: int):
        wheels_command = [0.0, 0.0]
        if direction == Direction.FORWARD:
            wheels_command = [power, power]
        if direction == Direction.BACKWARD:
            wheels_command = [-power, -power]
        
        self.logger.info("sending the Move {} for {} steps".format(direction.name, steps))

        for i in range(steps):
            self.send_joint_command_to_robot(wheels_command)
            time.sleep(.5)
        
        self.send_joint_command_to_robot([0.0, 0.0])

    def goto_position(self, joints: List[int]):
        self.send_robot_to_goal(goal=joints)

    def open_gripper(self):
        self.send_joint_command_to_robot([0, 0, 0, 0, 0, 1])
        time.sleep(2)

    def close_gripper(self):
        self.send_joint_command_to_robot([0, 0, 0, 0, 0, 100])
        time.sleep(2)    

    def toggle_claw_led(self):
        response = self.robot_cmd.send_single_command_to_robot("CLAW_LED_STATE", 1)
        if response['response'] == "ON":
            self.robot_cmd.send_single_command_to_robot("LIGHT_OFF", 1)
        else:
            self.robot_cmd.send_single_command_to_robot("LIGHT_ON", 1)

    def pick(self):
        self.send_robot_to_goal([100, 67, 48, 1])
        self.close_gripper()
        self.send_robot_to_goal([90, 67, 48, 100])

    def place(self):
        self.send_robot_to_goal([65, 67, 48, 100])
        self.move(Direction.FORWARD, 25, 2)
        self.open_gripper()
        self.move(Direction.BACKWARD, 25, 2)
        self.send_robot_to_goal([100, 67, 48, 1])

    def send_robot_to_goal(self, goal=[40, 50, 50, 0]):
        command = [0, 0, 0, 0, 0, 0]
        goal = np.asarray(goal).astype(np.float32)
        loop_counter = 0
        last_command_time = time.time()
        while(True):
            if time.time() - last_command_time > .1:
                self.update_joint_states()
                time.sleep(.1)
                joint_states = np.asarray(self.get_joint_states()).astype(np.float32)
                self.logger.debug(joint_states)
                diff = (goal - joint_states ) * 6
                diff[2] /= 4
                for i, d in enumerate(diff[:-1]):
                    diff[i] = min( 30, max(diff[i], -30))
                #     if -5 < d < 5:
                #         diff[i] = 0
                diff[0] = -diff[0]
                self.logger.debug(diff)
                self.logger.debug(np.max(np.abs(diff[:-1])))
                print(diff )
                if np.max(np.abs(diff[:-1])) < 10 or loop_counter > 10:
                    self.send_joint_command_to_robot([0, 0, 0, 0, 0, goal[-1]])
                    break
                # if np.all(joint_states > 0.1) or loop_counter > 10:
                command[2:5] = diff[:-1]
                command[5] = goal[3]
                self.send_joint_command_to_robot(command)
                last_command_time = time.time()
                loop_counter += 1
                
        self.logger.info('Went to goal position.')                
