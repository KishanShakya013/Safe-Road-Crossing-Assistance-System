"""Drawing helpers."""
import cv2
from config import SAFE, CAUTION, WAIT, UNSAFE

STATUS_COLOUR = {SAFE: (0, 150, 0), CAUTION: (0, 190, 230), WAIT: (0, 140, 255), UNSAFE: (0, 0, 200)}
LIGHT_COLOUR = {"RED": (0, 0, 255), "YELLOW": (0, 200, 255), "GREEN": (0, 255, 0), "UNKNOWN": (255, 255, 255)}

def _label(frame, text, org, col, scale):
    (tw, th), _ = cv2.getTextSize(text, cv2.FONT_HERSHEY_SIMPLEX, scale, 1)
    x, y = org
    y = max(th + 4, y)
    cv2.rectangle(frame, (x, y - th - 4), (x + tw + 4, y + 3), col, -1)
    cv2.putText(frame, text, (x + 2, y - 1), cv2.FONT_HERSHEY_SIMPLEX, scale, (255, 255, 255), 1, cv2.LINE_AA)

def draw(frame, dec, demo=False):
    H, W = frame.shape[:2]
    s = max(0.5, W / 960.0)
    for d in dec.lights:
        col = LIGHT_COLOUR.get(d.state or "UNKNOWN", (255, 255, 255))
        cv2.rectangle(frame, d.box[:2], d.box[2:], col, 2)
        _label(frame, f"Light: {d.state or '?'}", (d.box[0], d.box[3] + int(18 * s)), (60, 60, 60), 0.5 * s)
    for tr in dec.tracks:
        if abs(tr.last_t - dec.t) > 1e-9:
            continue 
        threat = tr.id in dec.threat_ids
        col = (0, 0, 255) if threat else (0, 200, 0)
        x1, y1, x2, y2 = tr.box
        cv2.rectangle(frame, (x1, y1), (x2, y2), col, 2)
        _label(frame, f"#{tr.id} {tr.name} {tr.speed_kmh:.0f}km/h {tr.dist_m:.0f}m",
               (x1, max(y1 - 6, int(100 * s))), col, 0.45 * s)
    bh = int(78 * s)
    ov = frame.copy()
    cv2.rectangle(ov, (0, 0), (W, bh), STATUS_COLOUR[dec.status], -1)
    cv2.addWeighted(ov, 0.8, frame, 0.2, 0, frame)
    cv2.putText(frame, dec.status, (int(16 * s), int(40 * s)), cv2.FONT_HERSHEY_SIMPLEX, 1.2 * s, (255, 255, 255), 3)
    cv2.putText(frame, f"{dec.reason}   [signal: {dec.light}]", (int(16 * s), int(66 * s)),
                cv2.FONT_HERSHEY_SIMPLEX, 0.55 * s, (255, 255, 255), 1)
    if demo:
        cv2.putText(frame, "DEMO - simulated scene", (int(16 * s), H - int(14 * s)),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6 * s, (255, 255, 255), 2)
    return frame
