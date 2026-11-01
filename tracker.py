import math
from collections import deque
from dataclasses import dataclass
from typing import Optional, Tuple
import numpy as np
from scipy.optimize import linear_sum_assignment
from config import REAL_WIDTH_M

@dataclass
class Det:
    box: Tuple[int, int, int, int]
    name: str
    conf: float = 1.0
    state: Optional[str] = None 

class Track:
    def __init__(self, tid, det, t, cfg, focal):
        self.id, self.name, self.box = tid, det.name, det.box
        self.cfg = cfg
        self.k = REAL_WIDTH_M.get(det.name, 1.8) * focal
        self.first_t = self.last_t = t
        self.hist = deque()         
        self.ws = None
        self.speed_kmh = 0.0
        self.approach_mps = 0.0       
        self.dist_m = float("inf")
        self._have_speed = False
        self.decel_mps2 = 0.0         
        self.app_hist = deque()       
        self.update(det, t)

    @property
    def age_s(self):
        return self.last_t - self.first_t

    @property
    def centre(self):
        x1, y1, x2, y2 = self.box
        return (x1 + x2) / 2.0, (y1 + y2) / 2.0

    def update(self, det, t):
        self.box, self.name, self.last_t = det.box, det.name, t
        x1, y1, x2, y2 = det.box
        w = max(1.0, float(x2 - x1))
        self.ws = w if self.ws is None else 0.7 * self.ws + 0.3 * w
        self.dist_m = self.k / self.ws
        self.hist.append((t, (x1 + x2) / 2.0, self.ws))
        win = self.cfg.speed_window_s
        while self.hist and t - self.hist[0][0] > win:
            self.hist.popleft()
        if len(self.hist) >= 5 and (t - self.hist[0][0]) >= 0.8 * win:
            ts = np.array([h[0] for h in self.hist])
            cx = np.array([h[1] for h in self.hist])
            ws = np.array([h[2] for h in self.hist])
            d = self.k / ws
            approach = -np.polyfit(ts, d, 1)[0]
            lat = np.polyfit(ts, cx, 1)[0] * (REAL_WIDTH_M.get(self.name, 1.8) / ws.mean())
            speed = math.hypot(lat, approach) * 3.6
            if self._have_speed:
                self.speed_kmh = 0.5 * self.speed_kmh + 0.5 * speed
                self.approach_mps = 0.5 * self.approach_mps + 0.5 * approach
            else:
                self.speed_kmh, self.approach_mps, self._have_speed = speed, approach, True
            self.app_hist.append((t, self.approach_mps))
            while self.app_hist and t - self.app_hist[0][0] > 1.0:
                self.app_hist.popleft()
            if len(self.app_hist) >= 5 and t - self.app_hist[0][0] >= 0.6:
                dec = (self.app_hist[0][1] - self.app_hist[-1][1]) / (t - self.app_hist[0][0])
                self.decel_mps2 = 0.5 * self.decel_mps2 + 0.5 * dec

class VehicleTracker:
    def __init__(self, cfg, focal_px):
        self.cfg, self.focal = cfg, focal_px
        self.tracks = []
        self._next = 0

    @staticmethod
    def _diag(b):
        return math.hypot(b[2] - b[0], b[3] - b[1])

    def update(self, dets, t):
        matched_d = set()
        if self.tracks and dets:
            C = np.zeros((len(self.tracks), len(dets)))
            for i, tr in enumerate(self.tracks):
                cx, cy = tr.centre
                for j, d in enumerate(dets):
                    dx, dy = (d.box[0] + d.box[2]) / 2.0, (d.box[1] + d.box[3]) / 2.0
                    scale = 0.5 * (self._diag(tr.box) + self._diag(d.box)) + 1e-6
                    wt, wd = max(1.0, tr.box[2] - tr.box[0]), max(1.0, d.box[2] - d.box[0])
                    C[i, j] = (math.hypot(cx - dx, cy - dy) / scale
                               + 2.0 * abs(math.log(wd / wt))        
                               + (0.3 if tr.name != d.name else 0.0))
            for i, j in zip(*linear_sum_assignment(C)):
                if C[i, j] <= 1.0:
                    self.tracks[i].update(dets[j], t)
                    matched_d.add(j)
        for j, d in enumerate(dets):
            if j not in matched_d:
                self.tracks.append(Track(self._next, d, t, self.cfg, self.focal))
                self._next += 1
        self.tracks = [tr for tr in self.tracks if t - tr.last_t <= self.cfg.track_max_missed_s]
        return self.tracks
