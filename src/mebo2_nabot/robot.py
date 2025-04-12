import time
import logging
import requests
import os
import subprocess
import numpy as np

class Robot():
    robot_command = [0, 0, 0, 0, 0, 0]
    last_robot_command = [0, 0, 0, 0, 0, 0]
    # claw stops on its own, dont need in stop command
    stop_command = [0, 0, 0, 0, 0]
    robot_command_names = ["WHEEL_LEFT_FORWARD", "WHEEL_RIGHT_FORWARD", "ARM_UP", "WRIST_UD_UP", "WRIST_ROTATE_LEFT", "CLAW_POSITION"]
    robot_joint_position = [0, 0, 0, 0]
    robot_joint_position_names = ["ARM_QUERY", "WRIST_UD_QUERY", "WRIST_ROTATE_QUERY", "CLAW_QUERY"]
    init_commands = ["BAT", "GET_SSID", "VIDEO_FLIP", "VIDEO_MIRROR", "ACEAA", "BCQAA", "CCIAA", "INIT_ALL"]
    messageCount = 0
    # default speed
    speed = 50
    
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

        self.get_joint_positions()

        self.logger.info('Initialized robot')

    def _new_cmd(self):
        result = "!" + self._to_base64(self.messageCount & 63)
        self.messageCount += 1
        return result

    def _enc_spd(self, speed):
        if speed:
            return self._enc_base64(speed, 2)
        # allow _send_single_command to have a value parameter of None
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
    
    def send_joint_values(self, jointValues):
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

        elif ( cmd == "VERSION_QUERY"):
            return "VER=?"
        elif ( cmd == "REBOOT_CMD"):
            return self._new_cmd() + "DE"

        elif ( cmd == "WHEEL_LEFT_SPEED"):
            return self._new_cmd() + "F" + self._enc_spd(para)
        elif ( cmd == "WHEEL_RIGHT_SPEED"):
            return self._new_cmd() + "E" + self._enc_spd(para)

        # not entirely sure what these remaining commands do and how we can implement them
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
        
        elif ( cmd == "SET_REG"):
            return ""
        elif ( cmd == "QUERY_REG"):
            return "REG" + (para / 100 % 10) + (para / 10 % 10) + (para % 10) + "=?"
        elif ( cmd == "SAVE_REG"):
            return "REG=FLUSH"

        elif ( cmd == "QUERY_EVENT"):
            return "*"
        else:
            return ""
        
    def _apply_limits(self, command: list[float], current_pos: list[float]) -> list[float] | None:
        limited_command = []
        limited_command.extend(command[:2])

        for idx, (cmd, pos) in enumerate(zip(command[2:5], current_pos[:3]), start=2):
            
            if cmd == 0.0:
                limited_command.append(0.0)
                continue
            if idx == 2:
                # arm position is reversed
                if (cmd < 0 and pos >= 90) or (cmd > 0 and pos <= 10):
                    return None
            else:
                if (cmd > 0 and pos >= 90) or (cmd < 0 and pos <= 10):
                    return None

            limited_command.append(cmd)

        if len(command) > 5:
            target_claw = command[5]
            limited_command.append(max(0, min(100, target_claw)))

        return limited_command


    def _do_steps(self, command: list[float], steps, sleep):
        for i in range(steps):
            current_pos = self.get_joint_positions()
            safe_command = self._apply_limits(command, current_pos)
            if safe_command:
                self.send_joint_values(safe_command)
                time.sleep(sleep)
            else: break        

    def get_joint_positions(self):
        fallback_state = self.robot_joint_position
        for cmd in self.robot_joint_position_names:
            try:
                data = self._send_single_cmd(cmd, 0)
                aJsonString = data['response']
                if ("ARM" in aJsonString) and (len(aJsonString) >= 4):
                    self.robot_joint_position[0] = int(aJsonString[4:])
                elif ("WRIST_UD" in aJsonString) and len(aJsonString) >= 9:
                    self.robot_joint_position[1] = int(aJsonString[9:])
                elif ("WRIST_ROTATE" in aJsonString) and len(aJsonString) >= 13:
                    self.robot_joint_position[2] = int(aJsonString[13:])
                elif ("CLAW" in aJsonString and len(aJsonString) >= 5):
                    self.robot_joint_position[3] = int(aJsonString[5:])
            except:
                self.logger.warning("Error parsing robot's states")
                return fallback_state

        return self.robot_joint_position    

    def stop(self, milliseconds:float = 0):
        if milliseconds > 0:
            time.sleep(milliseconds/1000)
        
        self.send_joint_values(self.stop_command)

    def left(self, steps, sleep=0.5):
        self._do_steps([-self.speed, self.speed], steps, sleep)
        self.stop()

    def right(self, steps, sleep=0.5):
        self._do_steps([self.speed, -self.speed], steps, sleep)
        self.stop()

    def forward(self, steps, sleep=0.5):
        self._do_steps([self.speed, self.speed], steps, sleep)
        self.stop()

    def backward(self, steps, sleep=0.5):
        self._do_steps([-self.speed, -self.speed], steps, sleep)            
        self.stop()

    def arm_up(self, steps, sleep=0.1):
        self._do_steps([0, 0, self.speed], steps, sleep) 
        self.stop()

    def arm_down(self, steps, sleep=0.1):
        self._do_steps([0, 0, -self.speed], steps, sleep)           
        self.stop()

    def wrist_up(self, steps, sleep=0.1):
        self._do_steps([0, 0, 0, self.speed], steps, sleep)
        self.stop()

    def wrist_down(self, steps, sleep=0.1):
        self._do_steps([0, 0, 0, -self.speed], steps, sleep)
        self.stop()

    def wrist_left(self, steps, sleep=0.1):
        self._do_steps([0, 0, 0, 0, self.speed], steps, sleep)
        self.stop()

    def wrist_right(self, steps, sleep=0.1):
        self._do_steps([0, 0, 0, 0, -self.speed], steps, sleep)  
        self.stop()

    def claw_open(self, steps):
        current_pos = self.get_joint_positions()
        # arm steps unreliably if less than 3, cap to 3
        if steps < 3: steps = 3
        new_position = current_pos[3] - steps
        safe_command = self._apply_limits([0, 0, 0, 0, 0, new_position], current_pos)
        self.send_joint_values(safe_command)

    def claw_close(self, steps):
        current_pos = self.get_joint_positions()
        if steps < 3: steps = 3
        new_position = current_pos[3] + steps
        safe_command = self._apply_limits([0, 0, 0, 0, 0, new_position], current_pos)
        self.send_joint_values(safe_command)    

    def claw_led_on(self):
        self._send_single_cmd("LIGHT_ON")

    def claw_led_off(self):
        self._send_single_cmd("LIGHT_OFF")        
    
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

    def set_speed(self, speed):
        self.speed = speed

    def set_joint_positions(self, goal, max_loops=15, max_speed=20, stop_threshold=3):
        if goal is None or len(goal) != 4:
            raise ValueError("Goal must be a list of 4 elements (use None for joints that should remain unchanged).")

        command = [0, 0, 0, 0, 0, 0]
        
        # allow None values, replace with current position
        current_states = np.asarray(self.get_joint_positions()).astype(np.float32)
        goal = np.array([g if g is not None else c for g, c in zip(goal, current_states)], dtype=np.float32)

        loop_counter = 0
        last_command_time = time.time()

        while True:
            if time.time() - last_command_time > 0.1:
                time.sleep(0.1)
                joint_states = np.asarray(self.get_joint_positions()).astype(np.float32)
                self.logger.debug(joint_states)

                diff = (goal - joint_states) * 6
                # make arm go a bit slower
                diff[2] /= 4 

                for i, d in enumerate(diff[:-1]):
                    diff[i] = min(max_speed, max(diff[i], -max_speed))

                diff[0] = -diff[0]
                self.logger.debug(diff)
                self.logger.debug(np.max(np.abs(diff[:-1])))

                if np.max(np.abs(diff[:-1])) < stop_threshold or loop_counter > max_loops:
                    self.send_joint_values([0, 0, 0, 0, 0, goal[-1]])
                    break

                command[2:5] = diff[:-1]
                command[5] = goal[3]
                self.send_joint_values(command)

                last_command_time = time.time()
                loop_counter += 1

    def send_audio(self, **kwargs):
        file = kwargs.get('file')
        numpy_stream = kwargs.get('numpy_stream')
        numpy_array = kwargs.get('numpy_array')
        rate = kwargs.get('rate')
        channels = kwargs.get('channels')
        input_format = kwargs.get('input_format')
        channel_layout = kwargs.get('channel_layout')

        # general ffmpeg flags
        ffmpeg_cmd = [
            'ffmpeg',
            '-loglevel', 'quiet',
            '-fflags', 'nobuffer',
            '-flags', 'low_delay',
            '-probesize', '32',
            '-analyzeduration', '0'
        ]

        # output format and destination
        stream_params = [
            '-f', 'alaw', 
            '-ar', '8000', 
            '-ac', '1', 
            "udp://192.168.99.1:8828?connect=1"
        ]

        if file:
            if isinstance(file, str) and os.path.isfile(file):
                if input_format:
                    ffmpeg_cmd += ['-f', input_format]

                ffmpeg_cmd += ['-i', file] + stream_params
                subprocess.run(ffmpeg_cmd)
                return
            else:
                print(f"Can't read file: {file}")
                return

        if not all([rate, channels, input_format, channel_layout]):
            raise ValueError("Missing required parameters for numpy mode.")

        ffmpeg_cmd += [
            '-f', input_format,
            '-ar', str(rate),
            '-ac', str(channels),
            '-channel_layout', channel_layout,
            '-i', 'pipe:0'
        ] + stream_params

        ffmpeg = subprocess.Popen(ffmpeg_cmd, stdin=subprocess.PIPE)

        def write(data):
            ffmpeg.stdin.write(data)

        def close():
            ffmpeg.stdin.close()
            ffmpeg.wait()
    
        if numpy_array is not None:
            chunk_size = 128
            for i in range(0, len(numpy_array), chunk_size):
                chunk = numpy_array[i:i + chunk_size]
                write(chunk.tobytes())
                time.sleep(chunk_size / rate)
            close()

        elif numpy_stream is not None:
            return write, close    

        else: 
            print("Please specify either a file or numpy array/stream.") 
            return None, None

class Microphone():
    def __init__(self, rtsp_url, rate=16000, channels=1, chunk_size=4000):
        self.rtsp_url = rtsp_url
        self.rate = rate
        self.channels = channels
        self.chunk_size = chunk_size

    def start(self):
        ffmpeg_cmd = [
            'ffmpeg',
            '-loglevel', 'quiet',
            '-i', self.rtsp_url,
            '-f', 's16le',
            '-acodec', 'pcm_s16le',
            '-ac', str(self.channels),
            '-ar', str(self.rate),
            '-'
        ]
        self.process = subprocess.Popen(ffmpeg_cmd, stdout=subprocess.PIPE, bufsize=10**8)
    
    def stop(self):
        self.process.terminate()

    def read_chunks(self):
        while True:
            raw = self.process.stdout.read(self.chunk_size * 2)
            if not raw:
                break
            audio_np = np.frombuffer(raw, dtype=np.int16)
            yield audio_np        