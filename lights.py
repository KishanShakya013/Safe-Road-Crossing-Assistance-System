import cv2
import numpy as np
RED, YELLOW, GREEN, UNKNOWN = "RED", "YELLOW", "GREEN", "UNKNOWN"

# Expected position (fraction along the lamp axis) of each lit lamp.
_EXPECTED = {RED: (0.0, 0.6), YELLOW: (0.15, 0.85), GREEN: (0.4, 1.0)}

def padded_crop(frame, box, pad=0.10):
    h, w = frame.shape[:2]
    x1, y1, x2, y2 = box
    px, py = int((x2 - x1) * pad), int((y2 - y1) * pad)
    x1, y1 = max(0, x1 - px), max(0, y1 - py)
    x2, y2 = min(w, x2 + px), min(h, y2 + py)
    return frame[y1:y2, x1:x2]

def classify_light(crop):
    if crop is None or crop.size == 0:
        return UNKNOWN, 0.0
    h, w = crop.shape[:2]
    if h < 8 or w < 4:
        return UNKNOWN, 0.0

    hsv = cv2.cvtColor(crop, cv2.COLOR_BGR2HSV)
    H, S, V = cv2.split(hsv)
    lit = (S >= 70) & (V >= 140)
    masks = {
        RED: lit & ((H <= 12) | (H >= 165)),
        YELLOW: lit & (H >= 11) & (H <= 34),
        GREEN: lit & (H >= 40) & (H <= 100),
    }
    horizontal = w > 1.3 * h
    scores, counts = {}, {}
    for state, m in masks.items():
        ys, xs = np.nonzero(m)
        n = len(ys)
        counts[state] = n
        if n == 0:
            scores[state] = 0.0
            continue
        frac = (xs.mean() / w) if horizontal else (ys.mean() / h)
        lo, hi = _EXPECTED[state]
        ok = lo <= frac <= hi
        scores[state] = (n / float(h * w)) * (1.0 if ok else 0.5)

    best = max(scores, key=scores.get)
    total = sum(scores.values())
    if counts[best] < 6 or total <= 0:
        return UNKNOWN, 0.0
    purity = scores[best] / total
    if purity < 0.55:
        return UNKNOWN, 0.0
    return best, float(purity * min(1.0, scores[best] / 0.05))

