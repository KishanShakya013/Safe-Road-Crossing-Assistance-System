from dataclasses import dataclass

VEHICLE_CLASSES = ("bicycle", "motorcycle", "car", "bus", "truck")
LIGHT_CLASS = "traffic light"

REAL_WIDTH_M = {"bicycle": 0.6, "motorcycle": 0.8, "car": 1.8, "bus": 2.5, "truck": 2.5} #metres

SAFE, CAUTION, WAIT, UNSAFE = "SAFE", "CAUTION", "WAIT", "UNSAFE"
SEVERITY = {SAFE: 0, CAUTION: 1, WAIT: 2, UNSAFE: 3}

SPEECH = {
    UNSAFE: "Do not cross.",
    WAIT: "Wait.",
    SAFE: "Safe to cross. Look both ways.",
    CAUTION: "Signal not clear. Be careful.",
}
              
@dataclass
class Config:

    hfov_deg: float = 70.0        # horizontal field of view (phone camera ~65-78)
    conf: float = 0.35
    imgsz: int = 640
    light_imgsz: int = 960

    moving_kmh: float = 5.0       # faster speed then moving
    danger_dist_m: float = 20.0   # any moving vehicle closer than this = threat
    ttc_limit_s: float = 6.0      # time-to-reach limit for approaching vehicles
    ttc_max_dist_m: float = 40.0  # only trust approach speed inside this range
    min_approach_mps: float = 4.0
    receding_mps: float = -1.0    # moving away faster than this = not a threat
    speed_window_s: float = 1.2 
    track_min_age_s: float = 0.8  # younger tracks: motion unknown -> be careful
    track_max_missed_s: float = 1.0
    # A vehicle on a settled red that is clearly braking and can stop in the
    # distance it has left is treated as stopping, not as a threat.
    stop_margin_m: float = 2.0
    min_decel_mps2: float = 1.0
    max_brake_mps2: float = 4.5

    # signal behaviour (Indian practice: amber means stop, but many riders
    # and drivers run it or the early red, so we wait before saying SAFE)
    light_vote_s: float = 0.6
    red_settle_s: float = 0.0     # red must be stable this long
    safe_confirm_s: float = 0.0   # SAFE must hold this long before announcin