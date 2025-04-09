import numpy as np
import logging
import sys
import threading
import tkinter.ttk as ttk
import tkinter as tk
from tkinter import Frame, RAISED, BOTH, Button, RIGHT, Canvas, Scale, HORIZONTAL
import subprocess
import mebo2_nabot

class GraphicalInterface():
    def __init__(self, **kwargs):
        threading.Thread.__init__(self)
        self.kwargs = kwargs
        if 'enable_joysticks' in self.kwargs:
            self.enable_joysticks = self.kwargs['enable_joysticks']

        logging.getLogger("requests").setLevel(logging.WARNING)
        
        self.stop_robot = False
        self.logger = logging.getLogger('GUI')
        self.logger.info("Starting ffplay...")
        self.start_ffplay()
        self.robot_ctrl = mebo2_nabot.Robot()

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
        self.robot_ctrl.set_values([0, 0, 0, 0, 0, 0])

        self.stop_ffplay()
        self.parent.quit()
        self.parent.destroy()

        sys.exit(0)

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
            self.robot_ctrl.set_values(command_to_send)

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
                self.canvas.create_rectangle(0, 0, 400, 400, fill='black')
                self.canvas.create_oval(0, 0, 400, 400, fill='black', outline='gray')
                self.canvas.create_oval(125, 125, 275, 275, fill='gray')

            self.canvas.pack(side='left')

            self.canvas.bind('<B1-Motion>', paint)
            self.canvas.bind('<ButtonRelease-1>', reset)
            reset_canvas()

            def scale1_command(val):
                val = self.scale1.get()

            def scale1_stop(event):
                self.scale1.set(0)

            self.scale1 = Scale(from_=100, to=-100, label='Arm', command=scale1_command)
            self.scale1.bind('<ButtonRelease-1>', scale1_stop)
            self.scale1.pack(side='left')

            def scale2_command(val):
                val = self.scale2.get()

            def scale2_stop(event):
                self.scale2.set(0)

            self.scale2 = Scale(from_=100, to=-100, label='Elbow', command=scale2_command)
            self.scale2.bind('<ButtonRelease-1>', scale2_stop)
            self.scale2.pack(side='left')

            self.scale3 = Scale(from_=0, to=100, orient=HORIZONTAL, label='Claw')
            self.scale3.pack(side='top')

            def scale4_command(val):
                val = self.scale4.get()

            def scale4_stop(event):
                self.scale4.set(0)

            self.scale4 = Scale(from_=-100, to=100, orient=HORIZONTAL, command=scale4_command, label='Wrist')
            self.scale4.bind('<ButtonRelease-1>', scale4_stop)
            self.scale4.pack(side='top')

            def button1_command():
                self.robot_ctrl.toggle_claw_led()

            self.button1 = Button(text="Claw LED", command=button1_command)
            self.button1.pack(side='top')

        create_canvas()
        self.robot_controller()

if __name__ == "__main__":
    logging.basicConfig(format='%(asctime)s  %(name)s  %(levelname)s: %(message)s', level=logging.INFO)
    app = GraphicalInterface(enable_joysticks=True, robot_init_pos=[100, 75, 50, 0])
    app.run()
