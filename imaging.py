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
        # download the image, convert it to a NumPy array, and then read
        # it into OpenCV format
        try:
            resp = urllib.request.urlopen("http://192.168.99.1/ajax/snapshot.jpg", timeout=0.2)
            latest_image = np.asarray(bytearray(resp.read()), dtype="uint8")
            self.curr_image = np.copy(latest_image)

            threading.Timer(0.2, self.update_image).start()
            # return Image.fromarray(self.latest_image)
        
        except timeout:
            self.logger.debug("updating camera frame request timed out ... skipping")
            threading.Timer(0.2, self.update_image).start()
        except Exception as e:
            threading.Timer(0.2, self.update_image).start()  
