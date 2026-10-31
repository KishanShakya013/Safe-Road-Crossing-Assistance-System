from collections import deque
from dataclasses import dataclass, field
from math import tan, radians
from typing import List
from config import SAFE, CAUTION, WAIT, UNSAFE, SEVERITY
from lights import RED, YELLOW, GREEN, UNKNOWN
from tracker import VehicleTracker, Det

@dataclass
class Decision:
    status: str
    reason: str
    light: str
    tracks: list = field(default_factory=list)
    threat_ids: set = field(default_factory=set)
    lights: List[Det] = field(default_factory=list)
    changed: bool = False
    t: float = 0.0


class StateMachine:

    def __init__(self, confirm_s):
        self.confirm_s, self.state, self._cand, self._since = confirm_s, None, None, None

    def update(self, raw, t):
        if self.state is None:
            self.state = CAUTION if raw == SAFE else raw
            return True
        if raw == self.state:
            self._cand = None
            return False
        if SEVERITY[raw] > SEVERITY[self.state]:
            self.state, self._cand = raw, None
            return True
        if self._cand != raw:
            self._cand, self._since = raw, t
        elif t - self._since >= self.confirm_s:
            self.state, self._cand = raw, None
            return True
        return False


class SafetyEngine:
    def __init__(self, cfg, frame_w):
        self.cfg = cfg
        focal = frame_w / (2.0 * tan(radians(cfg.hfov_deg) / 2.0))
        self.tracker = VehicleTracker(cfg, focal)
        self.votes = deque()
        self.red_since = None
        self.sm = StateMachine(cfg.safe_confirm_s)

    def _light_state(self, t, lights):
        weights = {}
        for d in lights:
            if d.state in (RED, YELLOW, GREEN):
                area = max(1, (d.box[2] - d.box[0]) * (d.box[3] - d.box[1]))
                weights[d.state] = weights.get(d.state, 0) + area
        frame_state = UNKNOWN
        if weights:
            total = sum(weights.values())
            for s in (GREEN, YELLOW, RED):          # most dangerous first
                if weights.get(s, 0) >= 0.3 * total:
                    frame_state = s
                    break
        self.votes.append((t, frame_state))
        while self.votes and t - self.votes[0][0] > self.cfg.light_vote_s:
            self.votes.popleft()
        known = [s for _, s in self.votes if s != UNKNOWN]
        if len(known) < 0.4 * len(self.votes):
            return UNKNOWN
        counts = {s: known.count(s) for s in (GREEN, YELLOW, RED)}
        # Asymmetric: switching TO green/amber is recognised quickly (a third of
        # the recent votes is enough); RED needs to win the vote.
        if counts[GREEN] + counts[YELLOW] >= 0.35 * len(known):
            return GREEN if counts[GREEN] >= counts[YELLOW] else YELLOW
        return RED if counts[RED] else UNKNOWN

    # ---- vehicles -------------------------------------------------------
    def _is_stopping(self, tr):
        c = self.cfg
        v = max(tr.approach_mps, 0.1)
        a_req = v * v / (2.0 * max(tr.dist_m - c.stop_margin_m, 1.0))
        return tr.decel_mps2 >= c.min_decel_mps2 and a_req <= c.max_brake_mps2

    def is_threat(self, tr, red_settled=False):
        c = self.cfg
        if tr.age_s < c.track_min_age_s:
            return tr.dist_m < c.danger_dist_m      # motion unknown: be careful
        if tr.speed_kmh <= c.moving_kmh:
            return False
        if tr.approach_mps < c.receding_mps:
            return False                              # driving away
        if red_settled and self._is_stopping(tr):
            return False                              # braking for the red
        if tr.dist_m < c.danger_dist_m:
            return True
        if tr.dist_m <= c.ttc_max_dist_m and tr.approach_mps >= c.min_approach_mps:
            return tr.dist_m / tr.approach_mps < c.ttc_limit_s
        return False

    # ---- main -----------------------------------------------------------
    def update(self, t, vehicles, lights):
        tracks = self.tracker.update(vehicles, t)
        light = self._light_state(t, lights)
        self.red_since = (self.red_since if self.red_since is not None else t) if light == RED else None

        red_settled = light == RED and t - self.red_since >= self.cfg.red_settle_s
        threats = {tr.id for tr in tracks if self.is_threat(tr, red_settled)}
        if threats:
            raw, why = UNSAFE, f"{len(threats)} vehicle(s) moving / approaching"
        elif light == GREEN:
            raw, why = UNSAFE, "Green signal: traffic can move"
        elif light == YELLOW:
            raw, why = UNSAFE, "Amber signal: vehicles still clearing"
        elif light == RED:
            if t - self.red_since < self.cfg.red_settle_s:
                raw, why = WAIT, "Red just came on: wait for vehicles to stop"
            else:
                raw, why = SAFE, "Red signal and vehicles stopped"
        else:
            raw, why = CAUTION, "Signal not visible: check traffic yourself"

        changed = self.sm.update(raw, t)
        return Decision(self.sm.state, why if raw == self.sm.state else f"{why} (confirming)",
                        light, tracks, threats, list(lights), changed, t)
