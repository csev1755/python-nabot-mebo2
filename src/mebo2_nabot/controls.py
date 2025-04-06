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

    def apply_limits(self, command: list[float], current_pos: list[float]) -> list[float] | None:
        limited_command = []
        limited_command.extend(command[:2])

        for idx, (cmd, pos) in enumerate(zip(command[2:5], current_pos[:3]), start=2):
            if cmd == 0.0:
                limited_command.append(0.0)
                continue
            if (cmd > 0 and pos >= 90) or (cmd < 0 and pos <= 10): return None
            limited_command.append(cmd)

        if len(command) > 5:
            target_claw = command[5]
            limited_command.append(max(1, min(100, target_claw)))
        return limited_command

    def do_steps(self, command: list[float], steps, sleep):
        for i in range(steps):
            self.update_joint_states()
            current_pos = self.get_joint_states()
            safe_command = self.apply_limits(command, current_pos)
            if safe_command:
                self.set_values(safe_command)
                time.sleep(sleep)
            else: break

    def left(self, power: float, steps=1, sleep=0.5):
        self.do_steps([-power, power], steps, sleep)
        self.stop()

    def right(self, power: float, steps=1, sleep=0.5):
        self.do_steps([power, -power], steps, sleep)
        self.stop()

    def forward(self, power: float, steps=1, sleep=0.5):
        self.do_steps([power, power], steps, sleep)
        self.stop()

    def backward(self, power: float, steps=1, sleep=0.5):
        self.do_steps([-power, -power], steps, sleep)            
        self.stop()

    def arm_up(self, power: float, steps=1, sleep=0.1):
        self.do_steps([0, 0, power], steps, sleep) 
        self.stop()

    def arm_down(self, power: float, steps=1, sleep=0.1):
        self.do_steps([0, 0, -power], steps, sleep)           
        self.stop()

    def wrist_up(self, power: float, steps=1, sleep=0.1):
        self.do_steps([0, 0, 0, power], steps, sleep)
        self.stop()

    def wrist_down(self, power: float, steps=1, sleep=0.1):
        self.do_steps([0, 0, 0, -power], steps, sleep)
        self.stop()

    def wrist_left(self, power: float, steps=1, sleep=0.1):
        self.do_steps([0, 0, 0, 0, power], steps, sleep)
        self.stop()

    def wrist_right(self, power: float, steps=1, sleep=0.1):
        self.do_steps([0, 0, 0, 0, -power], steps, sleep)  
        self.stop()

    def claw_open(self, steps=10):
        self.update_joint_states()
        current_pos = self.get_joint_states()
        new_position = current_pos[3] - steps
        safe_command = self.apply_limits([0, 0, 0, 0, 0, new_position], current_pos)
        self.set_values(safe_command)

    def claw_close(self, steps=10):
        self.update_joint_states()
        current_pos = self.get_joint_states()
        new_position = current_pos[3] + steps
        safe_command = self.apply_limits([0, 0, 0, 0, 0, new_position], current_pos)
        self.set_values(safe_command)    

    def toggle_claw_led(self):
        response = self.robot_cmd.send_single_command("CLAW_LED_STATE")
        if response['response'] == "ON":
            self.robot_cmd.send_single_command("LIGHT_OFF")
        else:
            self.robot_cmd.send_single_command("LIGHT_ON")

    def pick(self):
        self.set_joint_positions([100, 67, 48, 1])
        self.claw_close(steps=100)
        self.set_joint_positions([90, 67, 48, 100])

    def place(self):
        self.set_joint_positions([65, 67, 48, 100])
        self.forward(25, 2)
        self.claw_open(steps=100)
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
                