import time
import numpy as np
import logging

from .commands import RobotCommands

class RobotController():
    robot_state = [0, 0, 0, 0] # arm, wrist_ud, wrist_rot, gripper
    robot_state_names = ["ARM_QUERY", "WRIST_UD_QUERY", "WRIST_ROTATE_QUERY", "CLAW_QUERY"]

    def __init__(self, *args, **kwargs):
        self.robot_cmd = RobotCommands.getInstance(*args, **kwargs)
        self.stop_command = [0,0,0,0,0]
        self.init_commands = ["BAT", "GET_SSID", "VIDEO_FLIP", "VIDEO_MIRROR", "ACEAA", "BCQAA", "CCIAA", "INIT_ALL"]
        self.logger = logging.getLogger("Robot Controller")
        for cmd in self.init_commands:
            self.robot_cmd.send_single_command(cmd, 0)
        self.logger.info('Initialized robot')

    def update_joint_states(self):
        for cmd in self.robot_state_names:
            try:
                data = self.robot_cmd.send_single_command(cmd, 0)
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
    
    def set_values(self, jointValues):
        self.robot_cmd.send_joined_command(jointValues)

    def stop(self, milliseconds:float = 0):
        if milliseconds > 0:
            time.sleep(milliseconds/1000)
        
        self.set_values(self.stop_command)

    def do_steps(self, command: list[float], steps=1):
        for i in range(steps):
            self.set_values(command)
            time.sleep(0.5)
        self.set_values([0.0, 0.0])

    def left(self, power: float, steps=1):
        self.do_steps([-power, power], steps)

    def right(self, power: float, steps=1):
        self.do_steps([power, -power], steps)

    def forward(self, power: float, steps=1):
        self.do_steps([power, power], steps)

    def backward(self, power: float, steps=1):
        self.do_steps([-power, -power], steps)            

    def open_gripper(self):
        self.set_values([0, 0, 0, 0, 0, 1])
        time.sleep(2)

    def close_gripper(self):
        self.set_values([0, 0, 0, 0, 0, 100])
        time.sleep(2)    

    def toggle_claw_led(self):
        response = self.robot_cmd.send_single_command("CLAW_LED_STATE")
        if response['response'] == "ON":
            self.robot_cmd.send_single_command("LIGHT_OFF")
        else:
            self.robot_cmd.send_single_command("LIGHT_ON")

    def pick(self):
        self.set_joint_positions([100, 67, 48, 1])
        self.close_gripper()
        self.set_joint_positions([90, 67, 48, 100])

    def place(self):
        self.set_joint_positions([65, 67, 48, 100])
        self.forward(25, 2)
        self.open_gripper()
        self.backward(25, 2)
        self.set_joint_positions([100, 67, 48, 1])

    def set_joint_positions(self, goal, max_loops=15, max_speed=20, stop_threshold=3):
        if goal is None or len(goal) != 4:
            raise ValueError("Goal must be a list of 4 elements (use None for joints that should remain unchanged).")

        command = [0, 0, 0, 0, 0, 0]
        current_states = np.asarray(self.get_joint_states()).astype(np.float32)

        goal = np.array([g if g is not None else c for g, c in zip(goal, current_states)], dtype=np.float32)

        loop_counter = 0
        last_command_time = time.time()

        while True:
            if time.time() - last_command_time > 0.1:
                self.update_joint_states()
                time.sleep(0.1)
                joint_states = np.asarray(self.get_joint_states()).astype(np.float32)
                self.logger.debug(joint_states)

                diff = (goal - joint_states) * 6
                diff[2] /= 4 

                for i, d in enumerate(diff[:-1]):
                    diff[i] = min(max_speed, max(diff[i], -max_speed))

                diff[0] = -diff[0]
                self.logger.debug(diff)
                self.logger.debug(np.max(np.abs(diff[:-1])))

                if np.max(np.abs(diff[:-1])) < stop_threshold or loop_counter > max_loops:
                    self.set_values([0, 0, 0, 0, 0, goal[-1]])
                    break

                command[2:5] = diff[:-1]
                command[5] = goal[3]
                self.set_values(command)

                last_command_time = time.time()
                loop_counter += 1
                