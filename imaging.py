import time
import numpy as np
import urllib.request
import cv2
import logging
import threading
from PIL import Image
from socket import timeout

class RobotImaging():
    def __init__(self):
        self.logger = logging.getLogger("Robot Imaging")
        self.curr_image = None
        self.stop_threads = False
        self.stream_url = "http://192.168.99.1/ajax/snapshot.jpg"
        self.thread = threading.Thread(target=self.update_image, daemon=True)
        self.thread.start()

    def get_image(self):
        while self.curr_image is None:
            time.sleep(0.01)
        return self.get_latest_image()

    def get_image_cv2(self):
        if self.curr_image is None:
            return None
        return cv2.imdecode(self.curr_image, cv2.IMREAD_COLOR)

    def get_latest_image(self):
        if self.curr_image is None:
            return None
        opencv_im = cv2.imdecode(self.curr_image, cv2.IMREAD_COLOR)
        return Image.fromarray(cv2.cvtColor(opencv_im, cv2.COLOR_BGR2RGB))

    def update_image(self):
        while not self.stop_threads:
            try:
                with urllib.request.urlopen(self.stream_url, timeout=0.2) as resp:
                    latest_image = np.asarray(bytearray(resp.read()), dtype="uint8")
                    self.curr_image = np.copy(latest_image)
            except timeout:
                self.logger.debug("Updating camera frame request timed out ... skipping")
            except Exception as e:
                self.logger.error(f"Error updating image: {e}")

    def stop(self):
        self.stop_threads = True
        self.thread.join()  # Ensure the background thread stops safely
