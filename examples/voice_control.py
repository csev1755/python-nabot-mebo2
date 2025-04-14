import threading
from vosk import Model, KaldiRecognizer
import json
import time
import mebo2_nabot

class VoskSpeechRecognizer:
    def __init__(self, model_path='downloads/vosk-model-small-en-us-0.15', rate=16000):
        print("Loading Vosk model...")
        self.model = Model(model_path)
        self.recognizer = KaldiRecognizer(self.model, rate)
        self.robot = mebo2_nabot.Robot()

    def process_stream(self, audio_stream):
        print("Listening for speech...")
        for chunk in audio_stream:
            if self.recognizer.AcceptWaveform(chunk.tobytes()):
                result = json.loads(self.recognizer.Result())
                text = result.get("text", "")
                if text:
                    print("Detected speech:", text)
                    self.translate_text_to_command(text)

    def translate_text_to_command(self, text):
        text = text.lower()
        if "move forward" in text:
            self.robot.forward(1)
        elif "move backward" in text:
            self.robot.backward(1)
        elif "turn left" in text:
            self.robot.left(1)
        elif "turn right" in text:
            self.robot.right(1)
        elif "arm up" in text:
            self.robot.arm_up(2)        
        elif "close" in text:
            self.robot.claw_close(100)    
        elif "open" in text:
            self.robot.claw_open(100)   

def start_speech_recognition():
    audio_input = mebo2_nabot.Robot.Microphone(rate=16000)
    audio_input.open()

    recognizer = VoskSpeechRecognizer(rate=16000)

    recognition_thread = threading.Thread(target=recognizer.process_stream, args=(audio_input.read(),))
    recognition_thread.daemon = True
    recognition_thread.start()

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("Stopping audio capture...")
    finally:
        audio_input.close()

if __name__ == "__main__":
    rtsp_url = "rtsp://192.168.99.1/media/stream2"
    start_speech_recognition()
