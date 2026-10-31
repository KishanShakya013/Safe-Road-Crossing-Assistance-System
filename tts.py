"""Non-blocking speech: pyttsx3 (offline) -> gTTS+pygame (online) -> silent."""
import os
import queue
import tempfile
import threading
import time
import pyttsx3
import pygame
from gtts import gTTS 

class Speaker:
    def __init__(self, enabled=True):
        self.q = queue.Queue()
        self.backend = "off"
        self._run = enabled
        if enabled:
            threading.Thread(target=self._worker, daemon=True).start()
            time.sleep(0.3)  

    def _init_backend(self):
        try:
            eng = pyttsx3.init()
            eng.setProperty("rate", 165)
            self.backend = "pyttsx3"
            return eng
        except Exception:
            pass
        try:
            pygame.mixer.init()
            self.backend = "gtts"
            return None
        except Exception:
            self.backend = "off"
            return None

    def _worker(self):
        eng = self._init_backend()
        print(f"[INFO] Speech backend: {self.backend}")
        tmp = tempfile.mkdtemp()
        while self._run:
            try:
                text = self.q.get(timeout=0.2)
            except queue.Empty:
                continue
            try:
                if self.backend == "pyttsx3":
                    eng.say(text)
                    eng.runAndWait()
                elif self.backend == "gtts":
                    path = os.path.join(tmp, f"{abs(hash(text))}.mp3")
                    if not os.path.exists(path):
                        gTTS(text=text, lang="en", tld="co.in").save(path)  # Indian English voice
                    pygame.mixer.music.load(path)
                    pygame.mixer.music.play()
                    while pygame.mixer.music.get_busy():
                        time.sleep(0.05)
            except Exception as e:
                print(f"[WARN] speech failed: {e}")

    def say(self, text):
        while not self.q.empty():
            try:
                self.q.get_nowait()
            except queue.Empty:
                break
        self.q.put(text)

    def close(self):
        time.sleep(0.5)
        self._run = False
