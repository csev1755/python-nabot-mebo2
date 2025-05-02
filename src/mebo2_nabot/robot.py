import time
import logging
import requests
import os
import subprocess
import cv2
import numpy as np
from enum import Enum, auto

class Robot():
    """Main robot control class implementing singleton pattern."""

    class Command(Enum):
        """Enum of available commands and their strings."""
        EYE_LED_STATE = "eye_led_state()"
        CLAW_LED_STATE = "claw_led_state()"
        GET_SSID = "get_ssid()"
        VIDEO_FLIP = "video_flip(0)"
        VIDEO_MIRROR = "video_mirror(0)"
        BAT = "BAT=?"
        ARM_QUERY = "ARM=?"
        WRIST_UD_QUERY = "WRIST_UD=?"
        WRIST_ROTATE_QUERY = "WRIST_ROTATE=?"
        CLAW_QUERY = "CLAW=?"
        VERSION_QUERY = "VER=?"
        ACEAA = "!ACEAA"
        BCQAA = "!BCQAA"
        CCIAA = "!CCIAA"
        INIT_ALL = "!CVVDSAAAAAAAAAAAAAAAAAAAAAAAAYtBQfA4uAAAAAAAAAAQfAoPAcXAAAA"
        REBOOT_CMD = "DE"
        LIGHT_ON = "RAAAAAAAad"
        LIGHT_OFF = "RAAAAAAAac"
        WHEEL_LEFT_FORWARD = "F"
        WHEEL_RIGHT_FORWARD = "E"
        WHEEL_LEFT_SPEED = "F"
        WHEEL_RIGHT_SPEED = "E"
        ARM_UP = "G"
        WRIST_UD_UP = "H"
        WRIST_ROTATE_LEFT = "I"
        CLAW_POSITION = "N"
        CAL_ARM = "DE"
        CAL_WRIST_UD = "DI"
        CAL_WRIST_ROTATE = "DQ"
        CAL_CLAW = "Dg"
        CAL_ALL = "D_"
        QUERY_REG = auto()
        SET_REG = auto()
        SAVE_REG = "REG=FLUSH"
        QUERY_EVENT = "*"

    class Position(Enum):
        """Enum representing joint positions with their associated commands."""
        ARM = (auto(), 'ARM_QUERY', 'ARM_UP')
        WRIST_UD = (auto(), 'WRIST_UD_QUERY', 'WRIST_UD_UP')
        WRIST_ROTATE = (auto(), 'WRIST_ROTATE_QUERY', 'WRIST_ROTATE_LEFT')
        CLAW = (auto(), 'CLAW_QUERY', 'CLAW_POSITION')

        def __init__(self, value, query_command_name, control_command_name):
            self._value_ = value
            self.query_command_name = query_command_name
            self.control_command_name = control_command_name

        @property
        def query_command(self):
            return Robot.Command[self.query_command_name]

        @property
        def control_command(self):
            return Robot.Command[self.control_command_name]

    messageCount = 0
    battery_percent = -1
    # default speed
    speed = 50

    robot_joint_position_dict = {
        Position.ARM: 0,
        Position.WRIST_UD: 0,
        Position.WRIST_ROTATE: 0,
        Position.CLAW: 0
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

        init_commands = [
            self.Command.ACEAA, 
            self.Command.BCQAA, 
            self.Command.CCIAA, 
            self.Command.INIT_ALL
        ]

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

    def _send_request(self, url, retries=5, delay=0.5):
        """Send a single request.
        
        Args:
            url (str): URL to request
            retries (int, optional): Number of retry attempts. Defaults to 5
            delay (float, optional): Delay between retries in seconds. Defaults to 0.5
            
        Returns:
            request.Response: Request response or False if all retries fail
        """        
        for attempt in range(retries):
            try:
                return requests.get(url=url, verify=False, timeout=1)
            except requests.RequestException as e:
                self.logger.warning(f"Attempt {attempt + 1}/{retries} failed: {e}")
                # sometimes port 80 closes, poking 554 (RTSP) seems to open it back up
                try: requests.get("http://192.168.99.1:554") 
                except: pass          
                time.sleep(delay)

        self.logger.error(f"Failed to reach {url} after multiple retries")
        return False

    def _send_single_cmd(self, cmd: Command, value=None):
        """Send a single command and parses the response.
        
        Args:
            cmd (str): Command name to send
            value (int, optional): Parameter value for the command
            
        Returns:
            dict: JSON response or False
        """
        URL = "http://192.168.99.1/ajax/command.json?" + self._gen_single_cmd(cmd, number=1, value=value)
        try:
            return self._send_request(URL).json()
        except:
            self.logger.warning(f"Couldn't parse JSON in {cmd} response")
            return False

    def _gen_single_cmd(self, command: Command, number=None, value=None):
        """Generate URL suffix for a single command."""
        if command in [
            self.Command.EYE_LED_STATE, 
            self.Command.CLAW_LED_STATE, 
            self.Command.GET_SSID, 
            self.Command.VIDEO_FLIP, 
            self.Command.VIDEO_MIRROR
        ]:
            return f"command{number}={command.value}"
        
        if command in [
            self.Command.BAT, 
            self.Command.ARM_QUERY, 
            self.Command.WRIST_UD_QUERY,
            self.Command.WRIST_ROTATE_QUERY, 
            self.Command.CLAW_QUERY,
            self.Command.VERSION_QUERY, 
            self.Command.QUERY_EVENT,
            self.Command.SAVE_REG, 
            self.Command.ACEAA, 
            self.Command.BCQAA,
            self.Command.CCIAA, 
            self.Command.INIT_ALL
        ]:
            return f"command{number}=mebolink_message_send({command.value})"
        
        if command in [
            self.Command.REBOOT_CMD, 
            self.Command.CAL_ARM,
            self.Command.CAL_WRIST_UD, 
            self.Command.CAL_WRIST_ROTATE,
            self.Command.CAL_CLAW, 
            self.Command.CAL_ALL,
            self.Command.LIGHT_ON, 
            self.Command.LIGHT_OFF
        ]:
            return f"command{number}=mebolink_message_send({self._new_cmd() + command.value})"
        
        if command in [
            self.Command.WHEEL_LEFT_FORWARD, 
            self.Command.WHEEL_RIGHT_FORWARD,
            self.Command.WHEEL_LEFT_SPEED, 
            self.Command.WHEEL_RIGHT_SPEED,
            self.Command.ARM_UP, 
            self.Command.WRIST_UD_UP,
            self.Command.WRIST_ROTATE_LEFT, 
            self.Command.CLAW_POSITION
        ]:
            return f"command{number}=mebolink_message_send({self._new_cmd() + command.value + self._enc_base64(value, 2)})"
        
        if command == self.Command.QUERY_REG:
            digits = f"{int(value/100)%10}{int(value/10)%10}{int(value)%10}"
            return f"command{number}=mebolink_message_send(REG{digits}=?)"
        
        if command == self.Command.SET_REG:
            return f"command{number}=mebolink_message_send()"
        
        return f"command{number}=mebolink_message_send()"

    def _apply_limits(self, command: dict[Command, float]) -> dict[Command, float] | None:
        """Apply safety limits to joint commands to prevent out-of-range movements.
        
        Args:
            command (dict): Desired joint commands (e.g. {robot.Commands.ARM_UP: 1.0})

        Returns:
            dict: Limited safe commands. Out-of-range values return 0.
        """
        limited_command = {}
        current_pos = self.get_joint_positions()

        for cmd, value in command.items():
            if cmd == self.Command.ARM_UP:
                position = self.Position.ARM
                pos = current_pos.get(position, 0.0)
                if (value < 0 and pos >= 90) or (value > 0 and pos <= 10):
                    return None
            elif cmd == self.Command.WRIST_UD_UP:
                position = self.Position.WRIST_UD
                pos = current_pos.get(position, 0.0)
                if (value > 0 and pos >= 90) or (value < 0 and pos <= 10):
                    return None
            elif cmd == self.Command.WRIST_ROTATE_LEFT:
                position = self.Position.WRIST_ROTATE
                pos = current_pos.get(position, 0.0)
                if (value > 0 and pos >= 90) or (value < 0 and pos <= 10):
                    return None
            elif cmd == self.Command.CLAW_POSITION:
                limited_command[cmd] = max(0, min(100, value))
                continue

            limited_command[cmd] = value

        return limited_command


    def _do_steps(self, command: dict[Command, float], steps: int, sleep: float):
        """Execute a movement command over multiple steps.
        
        Args:
            command (dict): Joint commands to execute (e.g., {robot.Commands.ARM_UP: 1.0})
            steps (int): Number of steps to execute
            sleep (float): Time to sleep between steps
        """
        for i in range(steps):
            safe_command = self._apply_limits(command)
            if safe_command:
                self.send_joint_values(safe_command)
                time.sleep(sleep)
            else: break 

    def send_joint_values(self, joint_dict: dict[Command, int]):
        """Send multiple joint/motor commands.
        
        Args:
            joint_dict (dict): Dictionary mapping joint/motor names to their command values
        """
        URL = "http://192.168.99.1/ajax/command.json?"

        for i, (name, value) in enumerate(joint_dict.items()):
            if i > 0:
                URL += "&"
            URL += self._gen_single_cmd(number=i + 1, command=name, value=value)
        return self._send_request(URL)
    
    def stop(self):
        """Stop all movement."""
        
        # claw stops on its own, dont need in stop command
        self.send_joint_values({
            self.Command.WHEEL_LEFT_FORWARD: 0,
            self.Command.WHEEL_RIGHT_FORWARD: 0,
            self.Command.ARM_UP: 0,
            self.Command.WRIST_UD_UP: 0,
            self.Command.WRIST_ROTATE_LEFT: 0
        })

    def left(self, steps, sleep=0.5):
        """Move left for specified number of steps.
        
        Args:
            steps (int): Number of movement steps
            sleep (float, optional): Time between steps (default 0.5)
        """
        self._do_steps({
            self.Command.WHEEL_LEFT_FORWARD: -self.speed, 
            self.Command.WHEEL_RIGHT_FORWARD: self.speed
        }, steps, sleep)
        self.stop()

    def right(self, steps, sleep=0.5):
        """Move right for specified number of steps.
        
        Args:
            steps (int): Number of movement steps
            sleep (float, optional): Time between steps (default 0.5)
        """
        self._do_steps({
            self.Command.WHEEL_LEFT_FORWARD: self.speed, 
            self.Command.WHEEL_RIGHT_FORWARD: -self.speed
        }, steps, sleep)
        self.stop()

    def forward(self, steps, sleep=0.5):
        """Move forward for specified number of steps.
        
        Args:
            steps (int): Number of movement steps
            sleep (float, optional): Time between steps (default 0.5)
        """
        self._do_steps({
            self.Command.WHEEL_LEFT_FORWARD: self.speed, 
            self.Command.WHEEL_RIGHT_FORWARD: self.speed
        }, steps, sleep)
        self.stop()

    def backward(self, steps, sleep=0.5):
        """Move backward for specified number of steps.
        
        Args:
            steps (int): Number of movement steps
            sleep (float, optional): Time between steps (default 0.5)
        """
        self._do_steps({
            self.Command.WHEEL_LEFT_FORWARD: -self.speed, 
            self.Command.WHEEL_RIGHT_FORWARD: -self.speed
        }, steps, sleep)
        self.stop()

    def arm_up(self, steps, sleep=0.1):
        """Raise arm for specified number of steps.
        
        Args:
            steps (int): Number of movement steps
            sleep (float, optional): Time between steps (default 0.1)
        """
        self._do_steps({self.Command.ARM_UP: self.speed}, steps, sleep)
        self.stop()

    def arm_down(self, steps, sleep=0.1):
        """Lower arm for specified number of steps.
        
        Args:
            steps (int): Number of movement steps
            sleep (float, optional): Time between steps (default 0.1)
        """
        self._do_steps({self.Command.ARM_UP: -self.speed}, steps, sleep)
        self.stop()

    def wrist_up(self, steps, sleep=0.1):
        """Move wrist up for specified number of steps.
        
        Args:
            steps (int): Number of movement steps
            sleep (float, optional): Time between steps (default 0.1)
        """
        self._do_steps({self.Command.WRIST_UD_UP: self.speed}, steps, sleep)
        self.stop()

    def wrist_down(self, steps, sleep=0.1):
        """Move wrist down for specified number of steps.
        
        Args:
            steps (int): Number of movement steps
            sleep (float, optional): Time between steps (default 0.1)
        """
        self._do_steps({self.Command.WRIST_UD_UP: -self.speed}, steps, sleep)
        self.stop()

    def wrist_left(self, steps, sleep=0.1):
        """Rotate wrist left for specified number of steps.
        
        Args:
            steps (int): Number of movement steps
            sleep (float, optional): Time between steps (default 0.1)
        """
        self._do_steps({self.Command.WRIST_ROTATE_LEFT: self.speed}, steps, sleep)
        self.stop()

    def wrist_right(self, steps, sleep=0.1):
        """Rotate wrist right for specified number of steps.
        
        Args:
            steps (int): Number of movement steps
            sleep (float, optional): Time between steps (default 0.1)
        """
        self._do_steps({self.Command.WRIST_ROTATE_LEFT: -self.speed}, steps, sleep)
        self.stop()

    def claw_open(self, steps):
        """Open claw by specified number of steps.
        
        Args:
            steps (int): Number of movement steps
        """
        current_pos = self.get_joint_positions()
        if steps < 3: steps = 3
        new_position = current_pos[self.Position.CLAW] - steps
        safe_command = self._apply_limits({
            self.Command.CLAW_POSITION: new_position
        })
        self.send_joint_values(safe_command)

    def claw_close(self, steps):
        """Close claw by specified number of steps.
        
        Args:
            steps (int): Number of movement steps
        """
        current_pos = self.get_joint_positions()
        if steps < 3: steps = 3
        new_position = current_pos[self.Position.CLAW] + steps
        safe_command = self._apply_limits({
            self.Command.CLAW_POSITION: new_position
        })
        self.send_joint_values(safe_command)

    def claw_led_on(self):
        """Turn on the claw LED."""
        self._send_single_cmd(self.Command.LIGHT_ON)

    def claw_led_off(self):
        """Turn off the claw LED."""
        self._send_single_cmd(self.Command.LIGHT_OFF)        
    
    def toggle_claw_led(self):
        """Toggle claw LED on and off."""
        response = self._send_single_cmd(self.Command.CLAW_LED_STATE)
        if response['response'] == "ON":
            self._send_single_cmd(self.Command.LIGHT_OFF)
        else:
            self._send_single_cmd(self.Command.LIGHT_ON)

    def set_speed(self, speed):
        """Set default movement speed.
        
        Args:
            speed (int): Speed value (0-100)
        """
        self.speed = speed

    def get_battery(self):
        """Query and return an estimated battery charge percentage 
        
        Returns:
            int: Percent estimated battery charge remaining
        """
        json = self._send_single_cmd(self.Command.BAT)
        
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

    def get_joint_positions(self) -> dict[Position, int]:
        """Query and return current joint positions.

        Returns:
            dict: Current positions of all joints
        """
        fallback_state = {position: self.robot_joint_position_dict[position] 
                        for position in self.Position}

        for position in self.Position:
            try:
                data = self._send_single_cmd(position.query_command, 0)
                response = data['response']
                
                if f"{position.query_command.value.split('=')[0]}=" in response:
                    value_str = response.split('=')[1]
                    self.robot_joint_position_dict[position] = int(value_str)
                    
            except Exception as e:
                self.logger.warning(f"Error parsing {position.name}: {str(e)}")
                return fallback_state

        return self.robot_joint_position_dict.copy()

    def set_joint_positions(
        self,
        goal: dict[Position, float],
        max_loops=15,
        max_speed=20,
        stop_threshold=3,
        min_goal_threshold=5
    ):
        """Move joints to specified positions with smooth motion control.

        Args:
            goal (dict): Target joint positions (e.g., {robot.Position.ARM: 60, robot.Position.CLAW: 30})
            max_loops (int): Maximum control loop iterations
            max_speed (int): Maximum movement speed per loop
            stop_threshold (int): Difference threshold to stop motion
            min_goal_threshold (int): Ignore small goal differences
        """
        if not isinstance(goal, dict):
            raise ValueError("Goal must be a dictionary of Position to target values.")

        current_states = self.get_joint_positions()
        adjusted_goal = {}

        for position, target in goal.items():
            current = current_states.get(position, 0)
            if abs(target - current) >= min_goal_threshold:
                adjusted_goal[position.control_command] = target
            else:
                adjusted_goal[position.control_command] = current

        loop_counter = 0
        last_command_time = time.time()

        # set claw first, takes exact position
        self._send_single_cmd(self.Command.CLAW_POSITION, adjusted_goal[self.Command.CLAW_POSITION])

        while True:
            if time.time() - last_command_time > 0.1:
                time.sleep(0.1)
                joint_states = self.get_joint_positions()
                diff_command = {}
                max_diff = 0

                for cmd, target in adjusted_goal.items():
                    if cmd is not self.Command.CLAW_POSITION:
                        if cmd == self.Command.ARM_UP:
                            position = self.Position.ARM
                            current = joint_states[position]
                            diff = (target - current) * 6 / 3 * -1
                        elif cmd == self.Command.WRIST_UD_UP:
                            position = self.Position.WRIST_UD
                            current = joint_states[position]
                            diff = (target - current) * 6
                        elif cmd == self.Command.WRIST_ROTATE_LEFT:
                            position = self.Position.WRIST_ROTATE
                            current = joint_states[position]
                            diff = (target - current) * 6
                    else:
                        continue

                    diff = max(-max_speed, min(max_speed, diff))
                    diff_command[cmd] = diff
                    max_diff = max(max_diff, abs(diff))

                self.logger.debug(f"States: {joint_states}")
                self.logger.debug(f"Diffs: {diff_command}")

                if max_diff < stop_threshold or loop_counter > max_loops:
                    stop_command = {
                        self.Command.ARM_UP: 0.0,
                        self.Command.WRIST_UD_UP: 0.0,
                        self.Command.WRIST_ROTATE_LEFT: 0.0,
                    }
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