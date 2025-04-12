import cv2
import mebo2_nabot
from ultralytics import YOLO    

if __name__ == "__main__":
    video = mebo2_nabot.Robot.Camera()
    model = YOLO("yolo11n.pt")

    while True:
        frame = video.read()

        results = model(frame)
        annotated_frame = results[0].plot()

        cv2.imshow("Object Detection", annotated_frame)

        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

    video.stop()
    cv2.destroyAllWindows()
