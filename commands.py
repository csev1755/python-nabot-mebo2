import time
import requests
import logging

class RobotCommands():
    robot_command = [0, 0, 0, 0, 0, 0] # forward, left_right, arm, wrist_ud, wrist_rot, gripper
    last_robot_command = [0, 0, 0, 0, 0, 0] # forward, left_right, arm, wrist_ud, wrist_rot, gripper
    robot_command_names = ["WHEEL_LEFT_FORWARD", "WHEEL_RIGHT_FORWARD", "ARM_UP", "WRIST_UD_UP", "WRIST_ROTATE_LEFT", "CLAW_POSITION"]
    
    messageCount = 0
    
    __instance = None

    @staticmethod
    def getInstance(*args, **kwargs):
      """ Static access method. """
      if RobotCommands.__instance == None:
         RobotCommands(*args, **kwargs)
      return RobotCommands.__instance
    
    def __init__(self, *args, **kwargs):
        """ Virtually private constructor. """
        if RobotCommands.__instance != None:
            raise Exception("RobotCommands is a singleton!")
        else:
            RobotCommands.__instance = self

        self.logger = logging.getLogger('Robot Commands')

    def send_single_command_to_robot(self, cmd, value, retries=5, delay=0.5):
        URL = "http://192.168.99.1/ajax/command.json?" + self.generate_single_command(1, cmd, value)

        for attempt in range(retries):
            try:
                r = requests.get(url=URL, verify=False, timeout=1)
                return r.json()
            except requests.RequestException as e:
                self.logger.warning(f"Attempt {attempt + 1}/{retries} failed: {e}")
                time.sleep(delay)

        self.logger.error(f"Failed to send {cmd} after multiple retries")
    
    def send_joint_command_to_robot_helper(self, jointValues):
        self.robot_command = jointValues
        URL = "http://192.168.99.1/ajax/command.json?"

        for i in range(len(self.robot_command)) :
            if (i > 0):
                URL += "&";
            URL += self.generate_single_command(i + 1, self.robot_command_names[i], self.robot_command[i])
            self.last_robot_command[i] = self.robot_command[i]
        time.sleep(0.01)
        try:
            r = requests.get(url = URL, verify=False, timeout=1)
        except requests.exceptions.Timeout:
            self.logger.warning("request timeout")
        except Exception as e:
            self.logger.warning(e)

    def generate_single_command(self, number, command, parameter):
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
            return self.new_cmd() + "RAAAAAAAad"
        elif ( cmd == "LIGHT_OFF"):
            return self.new_cmd() + "RAAAAAAAac"

        elif ( cmd == "WHEEL_LEFT_FORWARD"):
            return self.new_cmd() + "F" + self.enc_spd(para)
        elif ( cmd == "WHEEL_RIGHT_FORWARD"):
            return self.new_cmd() + "E" + self.enc_spd(para)

        elif ( cmd == "ARM_UP"):
            return self.new_cmd() + "G" + self.enc_spd(para)
        elif ( cmd == "ARM_QUERY"):
            return "ARM=?"

        elif ( cmd == "WRIST_UD_UP"):
            return self.new_cmd() + "H" + self.enc_spd(para)
        elif ( cmd == "WRIST_UD_QUERY"):
            return "WRIST_UD=?"

        elif ( cmd == "WRIST_ROTATE_LEFT"):
            return self.new_cmd() + "I" + self.enc_spd(para)
        elif ( cmd == "WRIST_ROTATE_QUERY"):
            return "WRIST_ROTATE=?"

        elif ( cmd == "CLAW_POSITION"):
            return self.new_cmd() + "N" + self.enc_spd(para)
        elif ( cmd == "CLAW_QUERY"):
            return "CLAW=?"

        elif ( cmd == "CAL_ARM"):
            return self.new_cmd() + "DE"
        elif ( cmd == "CAL_WRIST_UD"):
            return self.new_cmd() + "DI"
        elif ( cmd == "CAL_WRIST_ROTATE"):
            return self.new_cmd() + "DQ"
        elif ( cmd == "CAL_CLAW"):
            return self.new_cmd() + "Dg"
        elif ( cmd == "CAL_ALL"):
            return self.new_cmd() + "D_"

        elif ( cmd == "VERSION_QUERY"):
            return "VER=?"
        elif ( cmd == "REBOOT_CMD"):
            return self.new_cmd() + "DE"

        elif ( cmd == "SET_REG"):
            return ""
        elif ( cmd == "QUERY_REG"):
            return "REG" + (para / 100 % 10) + (para / 10 % 10) + (para % 10) + "=?"
        elif ( cmd == "SAVE_REG"):
            return "REG=FLUSH"

        elif ( cmd == "WHEEL_LEFT_SPEED"):
            return self.new_cmd() + "F" + self.enc_spd(para)
        elif ( cmd == "WHEEL_RIGHT_SPEED"):
            return self.new_cmd() + "E" + self.enc_spd(para)

        elif ( cmd == "QUERY_EVENT"):
            return "*"
        else:
            return ""

    def new_cmd(self):
        result = "!" + self._to_base64(self.messageCount & 63)
        self.messageCount += 1
        return result

    def enc_spd(self, speed):
        return self._encode_base64(speed, 2)
    
    def _to_base64(self, val):
        str = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-_"
        return "" + str[val & 63]

    def _encode_base64(self, val, chars_count):
        result = ""
        for i in range(chars_count):
            result += self._to_base64(int(val) >> int(i * 6))
        return result
