import argparse
import csv
import os
import time
import cv2
from config import Config, SPEECH, VEHICLE_CLASSES, LIGHT_CLASS
from engine import SafetyEngine
from lights import classify_light, padded_crop
from tts import Speaker
from viz import draw
from detector import Detector

def parse():
    p = argparse.ArgumentParser()
    p.add_argument("--source")
    p.add_argument("--weights", default="yolov8n.pt")
    p.add_argument("--output", default="output/annotated.mp4")
    p.add_argument("--show", action="store_true")
    p.add_argument("--conf", type=float, default=0.35)
    p.add_argument("--hfov", type=float, default=70.0)
    return p.parse_args()
    
def frames_from_video(src):
    
    cap = cv2.VideoCapture(src)
    if not cap.isOpened():
        raise SystemExit(f"Could not open video source: {src}")
    fps =  cap.get(cv2.CAP_PROP_FPS) or 30.0
    if fps > 240:
        fps = 30.0
    w, h = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH)), int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

    def gen():
        while True:
            ok, fr = cap.read()
            if not ok:
                break
            yield fr, None
        cap.release()
    return gen(), fps, w, h

def main():
    a = parse()
    cfg = Config(conf=a.conf, hfov_deg=a.hfov)
    demo = a.source
    detector = None
    
    source = int(a.source) if a.source.isdigit() else a.source
    frames, fps, W, H= frames_from_video(source)
    print(f"[INFO] Vehicle model: {a.weights} | Light model: HSV colour")
    detector = Detector(a.weights, cfg)
    out = cv2.VideoWriter(a.output, cv2.VideoWriter_fourcc(*"mp4v"), fps, (W, H))
    log_path = os.path.splitext(a.output)[0] + "_events.csv"
    logf = open(log_path, "w", newline="")
    log = csv.writer(logf)
    log.writerow(["time_s", "status", "signal", "reason"])
    speaker = Speaker()
    engine = SafetyEngine(cfg, W)
    
    t0, n = time.time(), 0
    for frame, gt in frames:
        t =  n / fps
        dets = gt if gt is not None else detector.detect(frame)
        vehicles = [d for d in dets if d.name in VEHICLE_CLASSES]
        lights = [d for d in dets if d.name == LIGHT_CLASS]
        for d in lights:
            if d.state is None:
                d.state, _ = classify_light(padded_crop(frame, d.box))
        dec = engine.update(t, vehicles, lights)
        if dec.changed:
            print(f"[{t:6.2f}s] {dec.status:8s} signal={dec.light:7s} {dec.reason}")
            log.writerow([f"{t:.2f}", dec.status, dec.light, dec.reason])
            speaker.say(SPEECH[dec.status])
        out.write(draw(frame, dec, demo))
        if a.show:
            cv2.imshow("Safe Crossing Assistant (q to quit)", frame)
            if cv2.waitKey(1) & 0xFF == ord("q"):
                break
        n += 1
       

    out.release()
    logf.close()
    speaker.close()
    cv2.destroyAllWindows()
    print(f"[INFO] {n} frames. Video: {a.output}  Events: {log_path}")


if __name__ == "__main__":
    main()
