import queue
import subprocess
import sys
import threading
import time

_PYTTSX3_CODE = (
    "import sys, pyttsx3\n"
    "e = pyttsx3.init()\n"
    "e.setProperty('rate', 165)\n"
    "e.say(sys.argv[1])\n"
    "e.runAndWait()\n"
)

class Speaker:
    def __init__(self):
        self.q = queue.Queue()
        self.backend = "off"
        self._run = True
        self._proc = None
        self.backend = "pyttsx3"
        print(f"[INFO] Speech backend: {self.backend}")
        threading.Thread(target=self._worker, daemon=True).start()

    def _stop_current(self):
        if self._proc and self._proc.poll() is None:
            self._proc.terminate()
     
    def _worker(self):
        while self._run:
            try:
                text = self.q.get(timeout=0.2)
            except queue.Empty:
                continue
            try:
                self._stop_current()                      
                self._proc = subprocess.Popen([sys.executable, "-c", _PYTTSX3_CODE, text])
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
        if self._proc and self._proc.poll() is None:
            try:
                self._proc.wait(timeout=3)                
            except Exception:
                self._proc.terminate()
        self._run = False