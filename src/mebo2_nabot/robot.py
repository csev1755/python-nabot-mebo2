import time
import logging
import requests
import os
import subprocess
import cv2
import numpy as np

class Robot():
    """Main robot control class implementing singleton pattern."""
    
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
            raise Exception("Robot is a singleton!")
        else:
            Robot.__instance = self

        self.logger = logging.getLogger('Robot Commands')

        for cmd in self.init_commands:
            self._send_single_cmd(cmd, 0)

        self.get_joint_positions()

        self.logger.info('Initialized robot')

    def _new_cmd(self):
        """Generate a new command prefix with incrementing message count.
        
        Returns:
            str: Command prefix string
        """
        result = "!" + self._to_base64(self.messageCount & 63)
        self.messageCount += 1
        return result

    def _enc_spd(self, speed):
        """Encode speed value into base64 format.
        
        Args:
            speed (int): Speed value to encode (0-100)
            
        Returns:
            str: Encoded speed string or empty string if speed is None
        """
        if speed:
            return self._enc_base64(speed, 2)
        else: return ""
    
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
        URL = "http://192.168.99.1/ajax/command.json?" + self._gen_single_cmd(1, cmd, value)

        for attempt in range(retries):
            try:
                r = requests.get(url=URL, verify=False, timeout=1)
                return r.json()
            except requests.RequestException or r is none as e:
                self.logger.warning(f"Attempt {attempt + 1}/{retries} failed: {e}")
                time.sleep(delay)

        self.logger.error(f"Failed to send {cmd} after multiple retries")
    
    def send_joint_values(self, jointValues):
        """Send multiple joint/motor commands.
        
        Args:
            jointValues (list): List of command values for each joint/motor
        """
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
        """Generate URL suffix for a single command.
        
        Args:
            number (int): Command sequence number
            command (str): Command name
            parameter: Command parameter value
            
        Returns:
            str: Command suffix
        """
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
        """Generate a command string.
        
        Args:
            cmd (str): Command name
            para: Command parameter
            
        Returns:
            str: Encoded command string
        """
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
        """Apply safety limits to joint commands to prevent out-of-range movements.
        
        Args:
            command (list): Desired joint commands
            current_pos (list): Current joint positions
            
        Returns:
            list: Limited safe commands. Out-of-range values return 0.
        """
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

        # different logic for claw
        if len(command) > 5:
            target_claw = command[5]
            limited_command.append(max(0, min(100, target_claw)))

        return limited_command


    def _do_steps(self, command: list[float], steps, sleep):
        """Execute a movement command over multiple steps.
        
        Args:
            command (list): Joint commands to execute
            steps (int): Number of steps to execute
            sleep (float): Time to sleep between steps
        """
        for i in range(steps):
            current_pos = self.get_joint_positions()
            safe_command = self._apply_limits(command, current_pos)
            if safe_command:
                self.send_joint_values(safe_command)
                time.sleep(sleep)
            else: break        

    def get_joint_positions(self):
        """Query and return current joint positions.
        
        Returns:
            list: Current positions of all joints
        """
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

    def stop(self):
        """Stop all movement."""
        
        self.send_joint_values(self.stop_command)

    def left(self, steps, sleep=0.5):
        """Move left for specified number of steps.
        
        Args:
            steps (int): Number of movement steps
            sleep (float, optional): Time between steps (default 0.5)
        """
        self._do_steps([-self.speed, self.speed], steps, sleep)
        self.stop()

    def right(self, steps, sleep=0.5):
        """Move right for specified number of steps.
        
        Args:
            steps (int): Number of movement steps
            sleep (float, optional): Time between steps (default 0.5)
        """
        self._do_steps([self.speed, -self.speed], steps, sleep)
        self.stop()

    def forward(self, steps, sleep=0.5):
        """Move forward for specified number of steps.
        
        Args:
            steps (int): Number of movement steps
            sleep (float, optional): Time between steps (default 0.5)
        """
        self._do_steps([self.speed, self.speed], steps, sleep)
        self.stop()

    def backward(self, steps, sleep=0.5):
        """Move backward for specified number of steps.
        
        Args:
            steps (int): Number of movement steps
            sleep (float, optional): Time between steps (default 0.5)
        """
        self._do_steps([-self.speed, -self.speed], steps, sleep)            
        self.stop()

    def arm_up(self, steps, sleep=0.1):
        """Raise arm for specified number of steps.
        
        Args:
            steps (int): Number of movement steps
            sleep (float, optional): Time between steps (default 0.1)
        """
        self._do_steps([0, 0, self.speed], steps, sleep) 
        self.stop()

    def arm_down(self, steps, sleep=0.1):
        """Lower arm for specified number of steps.
        
        Args:
            steps (int): Number of movement steps
            sleep (float, optional): Time between steps (default 0.1)
        """
        self._do_steps([0, 0, -self.speed], steps, sleep)           
        self.stop()

    def wrist_up(self, steps, sleep=0.1):
        """Move wrist up for specified number of steps.
        
        Args:
            steps (int): Number of movement steps
            sleep (float, optional): Time between steps (default 0.1)
        """
        self._do_steps([0, 0, 0, self.speed], steps, sleep)
        self.stop()

    def wrist_down(self, steps, sleep=0.1):
        """Move wrist down for specified number of steps.
        
        Args:
            steps (int): Number of movement steps
            sleep (float, optional): Time between steps (default 0.1)
        """
        self._do_steps([0, 0, 0, -self.speed], steps, sleep)
        self.stop()

    def wrist_left(self, steps, sleep=0.1):
        """Rotate wrist left for specified number of steps.
        
        Args:
            steps (int): Number of movement steps
            sleep (float, optional): Time between steps (default 0.1)
        """
        self._do_steps([0, 0, 0, 0, self.speed], steps, sleep)
        self.stop()

    def wrist_right(self, steps, sleep=0.1):
        """Rotate wrist right for specified number of steps.
        
        Args:
            steps (int): Number of movement steps
            sleep (float, optional): Time between steps (default 0.1)
        """
        self._do_steps([0, 0, 0, 0, -self.speed], steps, sleep)  
        self.stop()

    def claw_open(self, steps):
        """Open claw by specified number of steps.
        
        Args:
            steps (int): Number of movement steps
        """
        current_pos = self.get_joint_positions()
        # arm steps unreliably if less than 3, cap to 3
        if steps < 3: steps = 3
        new_position = current_pos[3] - steps
        safe_command = self._apply_limits([0, 0, 0, 0, 0, new_position], current_pos)
        self.send_joint_values(safe_command)

    def claw_close(self, steps):
        """Close claw by specified number of steps.
        
        Args:
            steps (int): Number of movement steps
        """
        current_pos = self.get_joint_positions()
        if steps < 3: steps = 3
        new_position = current_pos[3] + steps
        safe_command = self._apply_limits([0, 0, 0, 0, 0, new_position], current_pos)
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

    def set_joint_positions(self, goal, max_loops=15, max_speed=20, stop_threshold=3, min_goal_threshold=5):
        """Move joints to specified positions with smooth motion control.
        
        Args:
            goal (list): Target positions for each joint (use None for joints that shouldn't move)
            max_loops (int): Maximum control loop iterations
            max_speed (int): Maximum movement speed
            stop_threshold (int): Position difference threshold to stop
            min_goal_threshold (int): Minimum position change to execute movement
            
        Raises:
            ValueError: If goal is not a list of 4 elements
        """
        if goal is None or len(goal) != 4:
            raise ValueError("Goal must be a list of 4 elements (use None for joints that should remain unchanged).")

        command = [0, 0, 0, 0, 0, 0]
        current_states = np.asarray(self.get_joint_positions()).astype(np.float32)
        adjusted_goal = []

        for goal_value, current_value in zip(goal, current_states):
            if goal_value is not None and abs(goal_value - current_value) < min_goal_threshold:
                goal_value = None
            if goal_value is None:
                adjusted_goal.append(current_value)
            else:
                adjusted_goal.append(goal_value)

        goal = np.array(adjusted_goal, dtype=np.float32)
        loop_counter = 0
        last_command_time = time.time()

        while True:
            if time.time() - last_command_time > 0.1:
                time.sleep(0.1)
                joint_states = np.asarray(self.get_joint_positions()).astype(np.float32)
                self.logger.debug(joint_states)

                diff = (goal - joint_states) * 6
                # make arm go a bit slower
                diff[2] /= 3 

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