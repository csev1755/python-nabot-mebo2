import time
import numpy as np
import urllib
import cv2
import threading
from PIL import Image
from socket import timeout

class RobotImaging():
    def __init__(self):
        self.curr_image = None
        self.stop_threads = False
        self.update_image()

    def get_image(self):
        im = self.get_latest_image()
        while im is None:
            time.sleep(1)
            im = self.get_latest_image()
        return im
    
    def get_image_cv2(self):
        return cv2.imdecode(self.curr_image, cv2.IMREAD_COLOR)

    def get_latest_image(self):
        if self.curr_image is None:
            return None
        opencv_im = cv2.imdecode(self.curr_image, cv2.IMREAD_COLOR)
        return Image.fromarray(cv2.cvtColor(opencv_im, cv2.COLOR_BGR2RGB))

    def update_image(self):
        if self.stop_threads:
            return  # Stop updating if the flag is set

        try:
            resp = urllib.request.urlopen("http://192.168.99.1/ajax/snapshot.jpg", timeout=0.2)
            latest_image = np.asarray(bytearray(resp.read()), dtype="uint8")
            self.curr_image = np.copy(latest_image)

        except timeout:
            self.logger.debug("Updating camera frame request timed out ... skipping")
        except Exception as e:
            self.logger.error(f"Error updating image: {e}")

        # Restart the timer only if the flag is not set
        if not self.stop_threads:
            self.timer = threading.Timer(0.2, self.update_image)
            self.timer.start()

    def stop(self):
        """Stop the update loop and cleanup resources."""
        self.stop_threads = True
        if hasattr(self, "timer"):
            self.timer.cancel()
