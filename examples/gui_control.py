import numpy as np
import logging
import sys
import threading
import subprocess
import pyaudio
import tkinter.ttk as ttk
import tkinter as tk
from tkinter import Frame, RAISED, BOTH, Button, RIGHT, Canvas, Scale, HORIZONTAL, Label
import mebo2_nabot

class MicrophoneCapture:
    def __init__(self):
        self.running = False
        self.capture_thread = None
        self.logger = logging.getLogger('Microphone')

    def start_capture(self, callback, rate=8000, channels=1, chunk=128, format=pyaudio.paInt16, device_index=None):
        p = pyaudio.PyAudio()
        stream = p.open(format=format,
                        channels=channels,
                        rate=rate,
                        input=True,
                        input_device_index=device_index,
                        frames_per_buffer=chunk)
        
        self.logger.info("Capture started.")

        try:
            while self.running:
                raw_data = stream.read(chunk, exception_on_overflow=False)
                np_data = np.frombuffer(raw_data, dtype=np.int16)
                callback(np_data)
        except Exception as e:
            self.logger.error(f"Error during capture: {e}")
        finally:
            stream.stop_stream()
            stream.close()
            p.terminate()
            self.logger.info("Capture stopped.")

    def stop_capture(self):
        self.running = False
        if self.capture_thread:
            self.capture_thread.join()

class GraphicalInterface():
    def __init__(self, **kwargs):
        threading.Thread.__init__(self)
        self.kwargs = kwargs
        if 'enable_joysticks' in self.kwargs:
            self.enable_joysticks = self.kwargs['enable_joysticks']

        logging.getLogger("requests").setLevel(logging.WARNING)
        
        self.stop_robot = False
        self.logger = logging.getLogger('GUI')
        self.robot_ctrl = mebo2_nabot.Robot()
        self.logger.info("Starting ffplay...")
        self.start_ffplay()
        self.robot_speaker = mebo2_nabot.Robot.Speaker(
            rate=8000,
            channels=1,
            input_format='s16le',
            channel_layout='mono'
        )
        self.robot_speaker.open()
        self.microphone_capture = MicrophoneCapture()
        self.is_streaming = False
        
        self.joint_states = []
        self.num_empty_commands = 0

        if 'robot_init_pos' in self.kwargs:
            self.logger.info('Sending robot to center.')
            self.robot_ctrl.set_joint_positions(goal=kwargs['robot_init_pos'])
            self.logger.info('Robot centered.')

        np.set_printoptions(precision=2)

    def callback(self):
        self.parent.quit()

    def run(self):
        self.parent = tk.Tk()
        self.main_frame = Frame(self.parent)
        self.main_frame.pack()

        if self.enable_joysticks:
            self.create_widgets()

        self.parent.protocol("WM_DELETE_WINDOW", self.on_closing)
        self.parent.mainloop()

    def on_closing(self):
        self.logger.info("Stopping Robot...")
        self.stop_robot = True
        self.robot_ctrl.claw_led_off()
        self.robot_ctrl.stop()
        self.stop_ffplay()
        self.robot_speaker.close()
        self.parent.quit()
        self.parent.destroy()
        sys.exit(0)

    # Using ffplay allows easy video + audio sync and low latency
    def start_ffplay(self):

        command = [
            'ffplay',
            '-fflags', 'nobuffer',
            '-flags', 'low_delay',
            '-framedrop',
            '-strict', 'experimental',
            '-rtsp_transport', 'udp',
            '-i', 'rtsp://192.168.99.1/media/stream2',
            '-loglevel', 'error',
            '-window_title', 'Video'
        ]

        self.ffplay_process = subprocess.Popen(command)

    def stop_ffplay(self):
        if hasattr(self, 'ffplay_process') and self.ffplay_process:
            self.ffplay_process.terminate()
            self.ffplay_process.wait()
            self.logger.info("ffplay process terminated.")

    def robot_controller(self):
        if self.stop_robot:
            return

        if self.enable_joysticks:
            x = -self.canvas.joystick_x
            y = -self.canvas.joystick_y
            v = (100 - abs(x)) * (y / 100) + y
            w = (100 - abs(y)) * (x / 100) + x 
            x = (v - w) // 2
            y = (v + w) // 2

            command_to_send = [x, y, self.scale1.get(), self.scale2.get(), self.scale4.get(), self.scale3.get()]
            self.robot_ctrl.send_joint_values(command_to_send)

        self.parent.after(10, self.robot_controller)

    def create_widgets(self):
        self.main_frame.style = ttk.Style()
        self.main_frame.winfo_toplevel().title("Controls")
        self.main_frame.style.theme_use('default')
        self.main_frame.configure(background='black')

        def create_canvas():
            class Joystick(tk.Canvas):
                pass

            self.canvas = Joystick(self.main_frame, width=400, height=400)
            self.canvas.joystick_x = 0
            self.canvas.joystick_y = 0
            self.canvas.is_moving = False

            def paint(event):
                reset_canvas()
                self.canvas.create_oval(0, 0, 400, 400, fill='black', outline='gray')
                x1, y1 = event.x - 75, event.y - 75
                x2, y2 = event.x + 75, event.y + 75
                self.canvas.create_oval(x1, y1, x2, y2, fill='blue')

                self.canvas.joystick_x = (event.x - 200) * 7 / 10
                self.canvas.joystick_y = (event.y - 200) * 7 / 10

                self.canvas.joystick_x = min(max(self.canvas.joystick_x, -100), 100)
                self.canvas.joystick_y = min(max(self.canvas.joystick_y, -100), 100)

            def reset(event):
                self.canvas.is_moving = False
                self.canvas.joystick_x = 0
                self.canvas.joystick_y = 0
                reset_canvas()

            def reset_canvas():
                self.canvas.create_rectangle(0, 0, 400, 400)
                self.canvas.create_oval(0, 0, 400, 400, fill='black', outline='gray')
                self.canvas.create_oval(125, 125, 275, 275, fill='gray')

            self.canvas.pack()

            self.canvas.bind('<B1-Motion>', paint)
            self.canvas.bind('<ButtonRelease-1>', reset)
            reset_canvas()

            self.controls_frame = Frame(self.main_frame)
            self.controls_frame.pack(fill='x', expand=True)

            def scale1_command(val):
                val = self.scale1.get()

            def scale1_stop(event):
                self.scale1.set(0)

            self.scale1 = Scale(self.controls_frame, from_=100, to=-100, label='Arm', command=scale1_command)
            self.scale1.bind('<ButtonRelease-1>', scale1_stop)
            self.scale1.pack(side='left')

            def scale2_command(val):
                val = self.scale2.get()

            def scale2_stop(event):
                self.scale2.set(0)

            self.scale2 = Scale(self.controls_frame, from_=100, to=-100, label='Elbow', command=scale2_command)
            self.scale2.bind('<ButtonRelease-1>', scale2_stop)
            self.scale2.pack(side='left')

            self.scale3 = Scale(self.controls_frame, from_=0, to=100, orient=HORIZONTAL, label='Claw')
            self.scale3.pack(side='top')

            def scale4_command(val):
                val = self.scale4.get()

            def scale4_stop(event):
                self.scale4.set(0)

            self.scale4 = Scale(self.controls_frame, from_=-100, to=100, orient=HORIZONTAL, command=scale4_command, label='Wrist')
            self.scale4.bind('<ButtonRelease-1>', scale4_stop)
            self.scale4.pack(side='top')

            def button1_command():
                self.robot_ctrl.toggle_claw_led()

            self.button1 = Button(self.controls_frame, text="Claw LED", command=button1_command)
            self.button1.pack(side='bottom')

            def button2_press(event):
                global is_streaming
                self.logger.info("Key pressed, starting audio capture.")
                self.microphone_capture.running = True
                self.microphone_capture.capture_thread = threading.Thread(
                    target=self.microphone_capture.start_capture,
                    args=(self.robot_speaker.write,)
                )
                self.microphone_capture.capture_thread.daemon = True
                self.microphone_capture.capture_thread.start()
                is_streaming = True   

            def button2_release(event):
                global is_streaming
                self.logger.info("Key released, stopping audio capture.")
                self.microphone_capture.stop_capture()
                is_streaming = False                   

            self.button2 = Button(self.controls_frame, text="Talk")
            self.button2.pack(side='bottom')
            self.button2.bind('<ButtonPress-1>', button2_press)
            self.button2.bind('<ButtonRelease-1>', button2_release)

            self.battery_var = tk.StringVar()
            self.battery_var.set("Battery: --%")

            self.battery_label = Label(self.controls_frame, textvariable=self.battery_var)
            self.battery_label.pack(side='bottom')

            def update_battery():
                battery_level = self.robot_ctrl.get_battery()
                self.battery_var.set(f"Battery: {battery_level}%")
                self.main_frame.after(1000, update_battery)
            
            update_battery()

        create_canvas()
        self.robot_controller()

if __name__ == "__main__":
    logging.basicConfig(format='%(asctime)s  %(name)s  %(levelname)s: %(message)s', level=logging.INFO)
    app = GraphicalInterface(enable_joysticks=True)
    app.run()
