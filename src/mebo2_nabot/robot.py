import time
import logging
import requests
import os
import subprocess
import cv2
import numpy as np

class Robot():
    """Main robot control class implementing singleton pattern."""

    messageCount = 0
    battery_percent = -1
    # default speed
    speed = 50

    robot_joint_position_dict = {
    "ARM_UP": 0,
    "WRIST_UD_UP": 0,
    "WRIST_ROTATE_LEFT": 0,
    "CLAW_POSITION": 0
    }

    __instance = None

    @staticmethod
    def getInstance():
        """Get the singleton instance of the Robot class.
        
        Returns:
            Robot: The singleton instance
        """
        if Robot.__instance == None:
            Robot()
        return Robot.__instance
    
    def __init__(self):
        """Initialize the connection and send initialization commands.
        
        Raises:
            Exception: If trying to create multiple instances (singleton violation)
        """
        if Robot.__instance != None:
            raise RuntimeError("Robot is a singleton")
        else:
            Robot.__instance = self

        self.logger = logging.getLogger('Robot Commands')

        init_commands = ["ACEAA", "BCQAA", "CCIAA", "INIT_ALL"]

        for cmd in init_commands:
            if not self._send_single_cmd(cmd):
                raise Exception("Can't connect to robot")

        self.get_battery()

        self.logger.info('Connected to robot')

    def _new_cmd(self):
        """Generate a new command prefix with incrementing message count.
        
        Returns:
            str: Command prefix string
        """
        result = "!" + self._to_base64(self.messageCount & 63)
        self.messageCount += 1
        return result
    
    def _to_base64(self, val):
        """Convert a value to base64 character using custom alphabet.
        
        Args:
            val (int): Value to convert (0-63)
            
        Returns:
            str: Single base64 character
        """
        str = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-_"
        return "" + str[val & 63]

    def _enc_base64(self, val, chars_count):
        """Encode a value into multiple base64 characters.
        
        Args:
            val (int): Value to encode
            chars_count (int): Number of characters to use
            
        Returns:
            str: Encoded base64 string
        """
        result = ""
        for i in range(chars_count):
            result += self._to_base64(int(val) >> int(i * 6))
        return result            

    def _send_single_cmd(self, cmd, value=None, retries=5, delay=0.5):
        """Send a single command with retry logic.
        
        Args:
            cmd (str): Command name to send
            value (int, optional): Parameter value for the command
            retries (int, optional): Number of retry attempts. Defaults to 5
            delay (float, optional): Delay between retries in seconds. Defaults to 0.5
            
        Returns:
            dict: JSON response or None if all retries fail
        """
        URL = "http://192.168.99.1/ajax/command.json?" + self._gen_single_cmd(cmd, number=1, value=value)

        for attempt in range(retries):
            try:
                r = requests.get(url=URL, verify=False, timeout=1)
                return r.json()
            except requests.RequestException or r.json is None as e:
                self.logger.warning(f"Attempt {attempt + 1}/{retries} failed: {e}")
                # sometimes port 80 closes, poking 554 (RTSP) seems to open it back up
                try: requests.get("http://192.168.99.1:554") 
                except: pass          
                time.sleep(delay)

        self.logger.error(f"Failed to send {cmd} after multiple retries")
        return False
    
    def send_joint_values(self, joint_dict):
        """Send multiple joint/motor commands.
        
        Args:
            joint_dict (dict): Dictionary mapping joint/motor names to their command values
        """

        URL = "http://192.168.99.1/ajax/command.json?"

        for i, (name, value) in enumerate(joint_dict.items()):
            if i > 0:
                URL += "&"
            URL += self._gen_single_cmd(number=i + 1, command=name, value=value)

        time.sleep(0.01)
        try:
            r = requests.get(url=URL, verify=False, timeout=1)
        except requests.exceptions.Timeout:
            self.logger.warning("request timeout")
        except Exception as e:
            self.logger.warning(e)

    def _gen_single_cmd(self, command, number=None, value=None):
        """Generate URL suffix for a single command."""

        static_commands = {
            "EYE_LED_STATE": "eye_led_state()",
            "CLAW_LED_STATE": "claw_led_state()",
            "GET_SSID": "get_ssid()",
            "VIDEO_FLIP": "video_flip(0)",
            "VIDEO_MIRROR": "video_mirror(0)",
        }

        static_messages = {
            "BAT": "BAT=?",
            "ARM_QUERY": "ARM=?",
            "WRIST_UD_QUERY": "WRIST_UD=?",
            "WRIST_ROTATE_QUERY": "WRIST_ROTATE=?",
            "CLAW_QUERY": "CLAW=?",
            "VERSION_QUERY": "VER=?",
            "QUERY_EVENT": "*",
            "SAVE_REG": "REG=FLUSH",
            "ACEAA": "!ACEAA",
            "BCQAA": "!BCQAA",
            "CCIAA": "!CCIAA",
            "INIT_ALL": "!CVVDSAAAAAAAAAAAAAAAAAAAAAAAAYtBQfA4uAAAAAAAAAAQfAoPAcXAAAA",            
        }

        sequential_messages = {
            "REBOOT_CMD": "DE",
            "CAL_ARM": "DE",
            "CAL_WRIST_UD": "DI",
            "CAL_WRIST_ROTATE": "DQ",
            "CAL_CLAW": "Dg",
            "CAL_ALL": "D_",
            "LIGHT_ON": "RAAAAAAAad",
            "LIGHT_OFF": "RAAAAAAAac",
        }

        encoded_messages = {
            "WHEEL_LEFT_FORWARD": "F",
            "WHEEL_RIGHT_FORWARD": "E",
            "WHEEL_LEFT_SPEED": "F",
            "WHEEL_RIGHT_SPEED": "E",
            "ARM_UP": "G",
            "WRIST_UD_UP": "H",
            "WRIST_ROTATE_LEFT": "I",
            "CLAW_POSITION": "N",
        }

        if command in static_commands:
            return f"command{number}={static_commands[command]}"
        
        if command in static_messages:
            return f"command{number}=mebolink_message_send({static_messages[command]})"

        if command in sequential_messages:
            return f"command{number}=mebolink_message_send({self._new_cmd() + sequential_messages[command]})"

        if command in encoded_messages:
            return f"command{number}=mebolink_message_send({self._new_cmd() + encoded_messages[command] + self._enc_base64(value, 2)})"

        if command == "QUERY_REG":
            digits = f"{int(value/100)%10}{int(value/10)%10}{int(value)%10}"
            return f"command{number}=mebolink_message_send(REG{digits}=?)"

        if command == "SET_REG":
            return f"command{number}=mebolink_message_send()"
        
        return f"command{number}=mebolink_message_send()"

    def _apply_limits(self, command: dict[str, float]) -> dict[str, float] | None:
        """Apply safety limits to joint commands to prevent out-of-range movements.
        
        Args:
            command (dict): Desired joint commands (e.g. {"ARM_UP": 1.0})

        Returns:
            dict: Limited safe commands. Out-of-range values return 0.
        """
        limited_command = {}
        current_pos = self.get_joint_positions()

        for joint, cmd in command.items():
            pos = current_pos.get(joint, 0.0)

            if cmd == 0.0:
                limited_command[joint] = 0.0
                continue

            if joint == "ARM_UP":
                # ARM position is reversed
                if (cmd < 0 and pos >= 90) or (cmd > 0 and pos <= 10):
                    return 0
            elif joint in {"WRIST_UD_UP", "WRIST_ROTATE_LEFT"}:
                if (cmd > 0 and pos >= 90) or (cmd < 0 and pos <= 10):
                    return 0
            elif joint == "CLAW_POSITION":
                limited_command[joint] = max(0, min(100, cmd))
                continue

            limited_command[joint] = cmd

        return limited_command


    def _do_steps(self, command: dict[str, float], steps: int, sleep: float):
        """Execute a movement command over multiple steps.
        
        Args:
            command (dict): Joint commands to execute (e.g., {"ARM_UP": 1.0})
            steps (int): Number of steps to execute
            sleep (float): Time to sleep between steps
        """
        for i in range(steps):
            safe_command = self._apply_limits(command)
            if safe_command:
                self.send_joint_values(safe_command)
                time.sleep(sleep)
            else: break
       

    def get_joint_positions(self) -> dict[str, int]:
        """Query and return current joint positions.

        Returns:
            dict: Current positions of all joints
        """

        fallback_state = self.robot_joint_position_dict.copy()

        joint_queries = {
            "ARM_QUERY": "ARM_UP",
            "WRIST_UD_QUERY": "WRIST_UD_UP",
            "WRIST_ROTATE_QUERY": "WRIST_ROTATE_LEFT",
            "CLAW_QUERY": "CLAW_POSITION"
        }

        for query_name, joint_key in joint_queries.items():
            try:
                data = self._send_single_cmd(query_name, 0)
                response = data['response']

                if query_name == "ARM_QUERY" and "ARM" in response and len(response) >= 4:
                    self.robot_joint_position_dict[joint_key] = int(response[4:])
                elif query_name == "WRIST_UD_QUERY" and "WRIST_UD" in response and len(response) >= 9:
                    self.robot_joint_position_dict[joint_key] = int(response[9:])
                elif query_name == "WRIST_ROTATE_QUERY" and "WRIST_ROTATE" in response and len(response) >= 13:
                    self.robot_joint_position_dict[joint_key] = int(response[13:])
                elif query_name == "CLAW_QUERY" and "CLAW" in response and len(response) >= 5:
                    self.robot_joint_position_dict[joint_key] = int(response[5:])
            except Exception:
                self.logger.warning("Error parsing robot's states")
                return fallback_state

        return self.robot_joint_position_dict   
    
    def get_battery(self):
        """Query and return an estimated battery charge percentage 
        
        Returns:
            int: Percent estimated battery charge remaining
        """
        json = self._send_single_cmd("BAT")
        
        if json['response'].startswith("BAT="):
            response = json['response']
            value = int(response[4:])
            # battery value seems like a voltage
            # 415 seemed to be the lowest value before poweroff
            # max value at full speed on full battery for me seemed to be about 730 so we'll use that as a baseline
            # max value at idle was 800 so we'll start with that to estimate before movement
            # we'll always assume lowest value
            max_idle = 800
            max_load = 730
            min_load = 415

            if self.battery_percent == -1 or value > max_load:
                percent = max(0, min(100, round((value - min_load) / (max_idle - min_load) * 100)))
            if value <= max_load:
                percent = max(0, min(100, round((value - min_load) / (max_load - min_load) * 100)))
            if self.battery_percent == -1 or percent < self.battery_percent:
                self.battery_percent = percent

        return self.battery_percent

    def stop(self):
        """Stop all movement."""
        
        # claw stops on its own, dont need in stop command
        self.send_joint_values({
            "WHEEL_LEFT_FORWARD": 0,
            "WHEEL_RIGHT_FORWARD": 0,
            "ARM_UP": 0,
            "WRIST_UD_UP": 0,
            "WRIST_ROTATE_LEFT": 0
        })

    def left(self, steps, sleep=0.5):
        """Move left for specified number of steps.
        
        Args:
            steps (int): Number of movement steps
            sleep (float, optional): Time between steps (default 0.5)
        """
        self._do_steps({"WHEEL_LEFT_FORWARD": -self.speed, "WHEEL_RIGHT_FORWARD": self.speed}, steps, sleep)
        self.stop()

    def right(self, steps, sleep=0.5):
        """Move right for specified number of steps.
        
        Args:
            steps (int): Number of movement steps
            sleep (float, optional): Time between steps (default 0.5)
        """
        self._do_steps({"WHEEL_LEFT_FORWARD": self.speed, "WHEEL_RIGHT_FORWARD": -self.speed}, steps, sleep)
        self.stop()

    def forward(self, steps, sleep=0.5):
        """Move forward for specified number of steps.
        
        Args:
            steps (int): Number of movement steps
            sleep (float, optional): Time between steps (default 0.5)
        """
        self._do_steps({"WHEEL_LEFT_FORWARD": self.speed, "WHEEL_RIGHT_FORWARD": self.speed}, steps, sleep)
        self.stop()

    def backward(self, steps, sleep=0.5):
        """Move backward for specified number of steps.
        
        Args:
            steps (int): Number of movement steps
            sleep (float, optional): Time between steps (default 0.5)
        """
        self._do_steps({"WHEEL_LEFT_FORWARD": -self.speed, "WHEEL_RIGHT_FORWARD": -self.speed}, steps, sleep)
        self.stop()

    def arm_up(self, steps, sleep=0.1):
        """Raise arm for specified number of steps.
        
        Args:
            steps (int): Number of movement steps
            sleep (float, optional): Time between steps (default 0.1)
        """
        self._do_steps({"ARM_UP": self.speed}, steps, sleep)
        self.stop()

    def arm_down(self, steps, sleep=0.1):
        """Lower arm for specified number of steps.
        
        Args:
            steps (int): Number of movement steps
            sleep (float, optional): Time between steps (default 0.1)
        """
        self._do_steps({"ARM_UP": -self.speed}, steps, sleep)
        self.stop()

    def wrist_up(self, steps, sleep=0.1):
        """Move wrist up for specified number of steps.
        
        Args:
            steps (int): Number of movement steps
            sleep (float, optional): Time between steps (default 0.1)
        """
        self._do_steps({"WRIST_UD_UP": self.speed}, steps, sleep)
        self.stop()

    def wrist_down(self, steps, sleep=0.1):
        """Move wrist down for specified number of steps.
        
        Args:
            steps (int): Number of movement steps
            sleep (float, optional): Time between steps (default 0.1)
        """
        self._do_steps({"WRIST_UD_UP": -self.speed}, steps, sleep)
        self.stop()

    def wrist_left(self, steps, sleep=0.1):
        """Rotate wrist left for specified number of steps.
        
        Args:
            steps (int): Number of movement steps
            sleep (float, optional): Time between steps (default 0.1)
        """
        self._do_steps({"WRIST_ROTATE_LEFT": self.speed}, steps, sleep)
        self.stop()

    def wrist_right(self, steps, sleep=0.1):
        """Rotate wrist right for specified number of steps.
        
        Args:
            steps (int): Number of movement steps
            sleep (float, optional): Time between steps (default 0.1)
        """
        self._do_steps({"WRIST_ROTATE_LEFT": -self.speed}, steps, sleep)
        self.stop()

    def claw_open(self, steps):
        """Open claw by specified number of steps.
        
        Args:
            steps (int): Number of movement steps
        """
        current_pos = self.get_joint_positions()
        # claw steps unreliably if less than 3, cap to 3
        if steps < 3: steps = 3
        new_position = current_pos["CLAW_POSITION"] - steps
        safe_command = self._apply_limits({"CLAW_POSITION": new_position})
        self.send_joint_values(safe_command)

    def claw_close(self, steps):
        """Close claw by specified number of steps.
        
        Args:
            steps (int): Number of movement steps
        """
        current_pos = self.get_joint_positions()
        if steps < 3: steps = 3
        new_position = current_pos["CLAW_POSITION"] + steps
        safe_command = self._apply_limits({"CLAW_POSITION": new_position})
        self.send_joint_values(safe_command)

    def claw_led_on(self):
        """Turn on the claw LED."""
        self._send_single_cmd("LIGHT_ON")

    def claw_led_off(self):
        """Turn off the claw LED."""
        self._send_single_cmd("LIGHT_OFF")        
    
    def toggle_claw_led(self):
        """Toggle claw LED on and off."""
        response = self._send_single_cmd("CLAW_LED_STATE")
        if response['response'] == "ON":
            self._send_single_cmd("LIGHT_OFF")
        else:
            self._send_single_cmd("LIGHT_ON")

    def set_speed(self, speed):
        """Set default movement speed.
        
        Args:
            speed (int): Speed value (0-100)
        """
        self.speed = speed

    def set_joint_positions(
        self,
        goal: dict[str, float],
        max_loops=15,
        max_speed=20,
        stop_threshold=3,
        min_goal_threshold=5
    ):
        """Move joints to specified positions with smooth motion control.

        Args:
            goal (dict): Target joint positions (e.g., {"ARM_UP": 60, "CLAW_POSITION": 30})
            max_loops (int): Maximum control loop iterations
            max_speed (int): Maximum movement speed per loop
            stop_threshold (int): Difference threshold to stop motion
            min_goal_threshold (int): Ignore small goal differences
        """
        if not isinstance(goal, dict):
            raise ValueError("Goal must be a dictionary of joint names and target positions.")

        all_joints = ["ARM_UP", "WRIST_UD_UP", "WRIST_ROTATE_LEFT", "CLAW_POSITION"]
        current_states = self.get_joint_positions()

        adjusted_goal = {}
        for joint in all_joints:
            current_value = current_states.get(joint, 0)
            goal_value = goal.get(joint, None)
            if goal_value is not None and abs(goal_value - current_value) >= min_goal_threshold:
                adjusted_goal[joint] = goal_value
            else:
                adjusted_goal[joint] = current_value  # maintain current if not moving

        loop_counter = 0
        last_command_time = time.time()

        while True:
            if time.time() - last_command_time > 0.1:
                time.sleep(0.1)
                joint_states = self.get_joint_positions()
                diff_command = {}

                max_diff = 0

                for joint, target in adjusted_goal.items():
                    current = joint_states.get(joint, 0)
                    diff = (target - current) * 6

                    if joint == "ARM_UP":
                        diff /= 3

                    diff = max(-max_speed, min(max_speed, diff))

                    if joint == "ARM_UP":
                        diff = -diff

                    diff_command[joint] = diff
                    max_diff = max(max_diff, abs(diff))

                self.logger.debug(joint_states)
                self.logger.debug(diff_command)
                self.logger.debug(f"max diff: {max_diff}")

                if max_diff < stop_threshold or loop_counter > max_loops:
                    stop_command = {joint: 0.0 for joint in ["ARM_UP", "WRIST_UD_UP", "WRIST_ROTATE_LEFT"]}
                    stop_command["CLAW_POSITION"] = adjusted_goal.get("CLAW_POSITION", joint_states.get("CLAW_POSITION", 0))
                    self.send_joint_values(stop_command)
                    break

                self.send_joint_values(diff_command)
                last_command_time = time.time()
                loop_counter += 1

    class Speaker:
        """Class for handling audio output to the robot's speaker.
        
        Uses ffmpeg to stream audio to the robot over UDP.
        
        Optional args:
            rate (int): Audio sample rate
            channels (int): Number of audio channels
            input_format (str): Audio input format
            channel_layout (str): Audio channel layout
        """
        
        def __init__(self, **kwargs):
            self.rate = kwargs.get('rate')
            self.channels = kwargs.get('channels')
            self.input_format = kwargs.get('input_format')
            self.channel_layout = kwargs.get('channel_layout')

            # general ffmpeg flags
            self.ffmpeg_cmd = [
                'ffmpeg',
                '-loglevel', 'quiet',
                '-fflags', 'nobuffer',
                '-flags', 'low_delay',
                '-probesize', '32',
                '-analyzeduration', '0'
            ]

            # output format and destination
            self.stream_params = [
                '-f', 'alaw', 
                '-ar', '8000', 
                '-ac', '1', 
                'udp://192.168.99.1:8828?connect=1'
            ]

            # numpy specific params
            self.numpy_cmd = [
                '-f', self.input_format,
                '-ar', str(self.rate),
                '-ac', str(self.channels),
                '-channel_layout', self.channel_layout,
                '-i', 'pipe:0'
            ] + self.stream_params

        def send_file(self, file):
            """Stream an audio file to the robot's speaker.
            Audio format can usually be detected by ffmpeg.
            
            Args:
                file (str): Path of audio file
            """
            if file:
                if not (isinstance(file, str) and os.path.isfile(file)):
                    print(f"Can't read file: {file}")
                    return
                
                if self.input_format:
                    self.ffmpeg_cmd += ['-f', self.input_format]
                    
                self.ffmpeg_cmd += ['-i', file] + self.stream_params            
                subprocess.run(self.ffmpeg_cmd)
                return

        def send_array(self, array, buffer_size=128):
            """Stream audio data from numpy array to robot's speaker. 
            Requires audio format information passed to instance of class.
            
            Args:
                array (numpy.ndarray): Array to play
                buffer_size (int): Size of buffers to send in bytes (default is 128)
                
            Raises:
                ValueError: If required parameters are missing
            """
            if not all([self.rate, self.channels, self.input_format, self.channel_layout]):
                raise ValueError("Missing required parameters for numpy mode.")

            self.ffmpeg_cmd += self.numpy_cmd
            self.ffmpeg = subprocess.Popen(self.ffmpeg_cmd, stdin=subprocess.PIPE)

            for i in range(0, len(array), buffer_size):
                self.write(array[i:i + buffer_size].tobytes())
                time.sleep(buffer_size / self.rate)
            self.close_numpy_stream()

        def open(self):
            """Start ffmpeg and open audio stream for writing."""
            self.ffmpeg_cmd += self.numpy_cmd
            self.ffmpeg = subprocess.Popen(self.ffmpeg_cmd, stdin=subprocess.PIPE)            

        def write(self, data):
            """Write numpy data to open stream.
            Requires audio format information passed to instance of class.
            
            Args:
                data (bytes): Audio data to write
                
            Raises:
                ValueError: If required parameters are missing
            """
            if not all([self.rate, self.channels, self.input_format, self.channel_layout]):
                raise ValueError("Missing required parameters for numpy mode.")            
            
            if self.ffmpeg:
                self.ffmpeg.stdin.write(data)

        def close(self):
            """Stop ffmpeg and close audio stream."""
            if self.ffmpeg:
                self.ffmpeg.stdin.close()
                self.ffmpeg.wait()

    class Microphone():
        """Class for handling audio input from the microphone.
        
        Uses ffmpeg to capture the RTSP audio stream.
        
        Args:
            rate (int): Audio sample rate
            channels (int): Number of audio channels
            buffer_size (int): Size of audio buffers to read in bytes (default 4000)
        """
        
        def __init__(self, rate, buffer_size=4000):
            self.rate = rate
            self.buffer_size = buffer_size

        def open(self):
            """Open microphone stream."""
            ffmpeg_cmd = [
                'ffmpeg',
                '-loglevel', 'quiet',
                '-i', "rtsp://192.168.99.1/media/stream2",
                '-f', 's16le',
                '-acodec', 'pcm_s16le',
                '-ac', '1',
                '-ar', str(self.rate),
                '-'
            ]
            self.process = subprocess.Popen(ffmpeg_cmd, stdout=subprocess.PIPE, bufsize=10**8)

        def read(self):
            """Generator that yields audio buffers from microphone.
            
            Yields:
                numpy.ndarray: Buffers of audio data
            """
            while True:
                raw = self.process.stdout.read(self.buffer_size * 2)
                if not raw:
                    break
                audio_np = np.frombuffer(raw, dtype=np.int16)
                yield audio_np

        def close(self):
            """Close microphone stream."""
            self.process.terminate() 

    class Camera():
        """Class for capturing video from the camera.
        
        Uses OpenCV to capture the RTSP video stream from robot.
        """
        
        def open(self):
            """Open camera connection."""
            self.cap = cv2.VideoCapture("rtsp://192.168.99.1/media/stream2")
            self.cap.isOpened()

        def read(self):
            """Read a frame from camera.
            
            Returns:
                numpy.ndarray: Video frame or None if capture fails
            """
            if not self.cap:
                return None

            while True:
                ret, frame = self.cap.read()
                if not ret:
                    return None
                return frame

        def close(self):
            """Close camera connection."""
            self.cap.release()