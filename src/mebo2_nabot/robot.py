import time
import logging
import requests
import numpy as np

class Robot():
    robot_command = [0, 0, 0, 0, 0, 0]
    last_robot_command = [0, 0, 0, 0, 0, 0]
    stop_command = [0, 0, 0, 0, 0]
    robot_command_names = ["WHEEL_LEFT_FORWARD", "WHEEL_RIGHT_FORWARD", "ARM_UP", "WRIST_UD_UP", "WRIST_ROTATE_LEFT", "CLAW_POSITION"]
    robot_state = [0, 0, 0, 0]
    robot_state_names = ["ARM_QUERY", "WRIST_UD_QUERY", "WRIST_ROTATE_QUERY", "CLAW_QUERY"]
    init_commands = ["BAT", "GET_SSID", "VIDEO_FLIP", "VIDEO_MIRROR", "ACEAA", "BCQAA", "CCIAA", "INIT_ALL"]
    messageCount = 0
    
    __instance = None

    @staticmethod
    def getInstance():
      if Robot.__instance == None:
         Robot()
      return Robot.__instance
    
    def __init__(self):
        if Robot.__instance != None:
            raise Exception("Robot is a singleton!")
        else:
            Robot.__instance = self

        self.logger = logging.getLogger('Robot Commands')

        for cmd in self.init_commands:
            self._send_single_cmd(cmd, 0)

        self.get_joint_states()

        self.logger.info('Initialized robot')

    def _new_cmd(self):
        result = "!" + self._to_base64(self.messageCount & 63)
        self.messageCount += 1
        return result

    def _enc_spd(self, speed):
        if speed:
            return self._enc_base64(speed, 2)
        else: return ""
    
    def _to_base64(self, val):
        str = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-_"
        return "" + str[val & 63]

    def _enc_base64(self, val, chars_count):
        result = ""
        for i in range(chars_count):
            result += self._to_base64(int(val) >> int(i * 6))
        return result            

    def _send_single_cmd(self, cmd, value=None, retries=5, delay=0.5):
        URL = "http://192.168.99.1/ajax/command.json?" + self._gen_single_cmd(1, cmd, value)

        for attempt in range(retries):
            try:
                r = requests.get(url=URL, verify=False, timeout=1)
                return r.json()
            except requests.RequestException as e:
                self.logger.warning(f"Attempt {attempt + 1}/{retries} failed: {e}")
                time.sleep(delay)

        self.logger.error(f"Failed to send {cmd} after multiple retries")
    
    def _send_joined_cmd(self, jointValues):
        self.robot_command = jointValues
        URL = "http://192.168.99.1/ajax/command.json?"

        for i in range(len(self.robot_command)) :
            if (i > 0):
                URL += "&";
            URL += self._gen_single_cmd(i + 1, self.robot_command_names[i], self.robot_command[i])
            self.last_robot_command[i] = self.robot_command[i]
        time.sleep(0.01)
        try:
            r = requests.get(url = URL, verify=False, timeout=1)
        except requests.exceptions.Timeout:
            self.logger.warning("request timeout")
        except Exception as e:
            self.logger.warning(e)

    def _gen_single_cmd(self, number, command, parameter):
        cmd_str = self._command_string(command, parameter)
        if(command == "EYE_LED_STATE"):
            return "command" + str(number) + "=eye_led_state()"
        if(command == "CLAW_LED_STATE"):
            return "command" + str(number) + "=claw_led_state()"
        if(command == "GET_SSID"):
            return "command" + str(number) + "=get_ssid()"
        if(command == "VIDEO_FLIP"):
            return "command" + str(number) + "=video_flip(0)"
        if(command == "VIDEO_MIRROR"):
            return "command" + str(number) + "=video_mirror(0)"
        if(command == "ACEAA"):
            return "command" + str(number) + "=mebolink_message_send(!ACEAA)"
        if(command == "BCQAA"):
            return "command" + str(number) + "=mebolink_message_send(!BCQAA)"
        if(command == "CCIAA"):
            return "command" + str(number) + "=mebolink_message_send(!CCIAA)"
        if(command == "INIT_ALL"):
            return "command" + str(number) + "=mebolink_message_send(!CVVDSAAAAAAAAAAAAAAAAAAAAAAAAYtBQfA4uAAAAAAAAAAQfAoPAcXAAAA)"
        return "command" + str(number) + "=mebolink_message_send(" + cmd_str + ")"
    
    def _command_string(self, cmd, para):
        if ( cmd == "BAT"):
            return "BAT=?"
        elif ( cmd == "LIGHT_ON"):
            return self._new_cmd() + "RAAAAAAAad"
        elif ( cmd == "LIGHT_OFF"):
            return self._new_cmd() + "RAAAAAAAac"

        elif ( cmd == "WHEEL_LEFT_FORWARD"):
            return self._new_cmd() + "F" + self._enc_spd(para)
        elif ( cmd == "WHEEL_RIGHT_FORWARD"):
            return self._new_cmd() + "E" + self._enc_spd(para)

        elif ( cmd == "ARM_UP"):
            return self._new_cmd() + "G" + self._enc_spd(para)
        elif ( cmd == "ARM_QUERY"):
            return "ARM=?"

        elif ( cmd == "WRIST_UD_UP"):
            return self._new_cmd() + "H" + self._enc_spd(para)
        elif ( cmd == "WRIST_UD_QUERY"):
            return "WRIST_UD=?"

        elif ( cmd == "WRIST_ROTATE_LEFT"):
            return self._new_cmd() + "I" + self._enc_spd(para)
        elif ( cmd == "WRIST_ROTATE_QUERY"):
            return "WRIST_ROTATE=?"

        elif ( cmd == "CLAW_POSITION"):
            return self._new_cmd() + "N" + self._enc_spd(para)
        elif ( cmd == "CLAW_QUERY"):
            return "CLAW=?"

        elif ( cmd == "CAL_ARM"):
            return self._new_cmd() + "DE"
        elif ( cmd == "CAL_WRIST_UD"):
            return self._new_cmd() + "DI"
        elif ( cmd == "CAL_WRIST_ROTATE"):
            return self._new_cmd() + "DQ"
        elif ( cmd == "CAL_CLAW"):
            return self._new_cmd() + "Dg"
        elif ( cmd == "CAL_ALL"):
            return self._new_cmd() + "D_"

        elif ( cmd == "VERSION_QUERY"):
            return "VER=?"
        elif ( cmd == "REBOOT_CMD"):
            return self._new_cmd() + "DE"

        elif ( cmd == "SET_REG"):
            return ""
        elif ( cmd == "QUERY_REG"):
            return "REG" + (para / 100 % 10) + (para / 10 % 10) + (para % 10) + "=?"
        elif ( cmd == "SAVE_REG"):
            return "REG=FLUSH"

        elif ( cmd == "WHEEL_LEFT_SPEED"):
            return self._new_cmd() + "F" + self._enc_spd(para)
        elif ( cmd == "WHEEL_RIGHT_SPEED"):
            return self._new_cmd() + "E" + self._enc_spd(para)

        elif ( cmd == "QUERY_EVENT"):
            return "*"
        else:
            return ""
        
    def _apply_limits(self, command: list[float], current_pos: list[float]) -> list[float] | None:
        limited_command = []
        limited_command.extend(command[:2])  # base movement (no limits)

        for idx, (cmd, pos) in enumerate(zip(command[2:5], current_pos[:3]), start=2):
            
            if cmd == 0.0:
                limited_command.append(0.0)
                continue
            if idx == 2:
                if (cmd < 0 and pos >= 90) or (cmd > 0 and pos <= 10):
                    return None
            else:
                if (cmd > 0 and pos >= 90) or (cmd < 0 and pos <= 10):
                    return None

            limited_command.append(cmd)

        if len(command) > 5:
            target_claw = command[5]
            limited_command.append(max(1, min(100, target_claw)))

        return limited_command


    def _do_steps(self, command: list[float], steps, sleep):
        for i in range(steps):
            current_pos = self.get_joint_states()
            safe_command = self._apply_limits(command, current_pos)
            if safe_command:
                self.set_values(safe_command)
                time.sleep(sleep)
            else: break        

    def get_joint_states(self):
        fallback_state = self.robot_state
        for cmd in self.robot_state_names:
            try:
                data = self._send_single_cmd(cmd, 0)
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
                return fallback_state

        return self.robot_state    
    
    def set_values(self, jointValues):
        self._send_joined_cmd(jointValues)

    def stop(self, milliseconds:float = 0):
        if milliseconds > 0:
            time.sleep(milliseconds/1000)
        
        self.set_values(self.stop_command)

    def left(self, power: float, steps=1, sleep=0.5):
        self._do_steps([-power, power], steps, sleep)
        self.stop()

    def right(self, power: float, steps=1, sleep=0.5):
        self._do_steps([power, -power], steps, sleep)
        self.stop()

    def forward(self, power: float, steps=1, sleep=0.5):
        self._do_steps([power, power], steps, sleep)
        self.stop()

    def backward(self, power: float, steps=1, sleep=0.5):
        self._do_steps([-power, -power], steps, sleep)            
        self.stop()

    def arm_up(self, power: float, steps=1, sleep=0.1):
        self._do_steps([0, 0, power], steps, sleep) 
        self.stop()

    def arm_down(self, power: float, steps=1, sleep=0.1):
        self._do_steps([0, 0, -power], steps, sleep)           
        self.stop()

    def wrist_up(self, power: float, steps=1, sleep=0.1):
        self._do_steps([0, 0, 0, power], steps, sleep)
        self.stop()

    def wrist_down(self, power: float, steps=1, sleep=0.1):
        self._do_steps([0, 0, 0, -power], steps, sleep)
        self.stop()

    def wrist_left(self, power: float, steps=1, sleep=0.1):
        self._do_steps([0, 0, 0, 0, power], steps, sleep)
        self.stop()

    def wrist_right(self, power: float, steps=1, sleep=0.1):
        self._do_steps([0, 0, 0, 0, -power], steps, sleep)  
        self.stop()

    def claw_open(self, steps=10):
        current_pos = self.get_joint_states()
        new_position = current_pos[3] - steps
        safe_command = self._apply_limits([0, 0, 0, 0, 0, new_position], current_pos)
        self.set_values(safe_command)

    def claw_close(self, steps=10):
        current_pos = self.get_joint_states()
        new_position = current_pos[3] + steps
        safe_command = self._apply_limits([0, 0, 0, 0, 0, new_position], current_pos)
        self.set_values(safe_command)    

    def toggle_claw_led(self):
        response = self._send_single_cmd("CLAW_LED_STATE")
        if response['response'] == "ON":
            self._send_single_cmd("LIGHT_OFF")
        else:
            self._send_single_cmd("LIGHT_ON")

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