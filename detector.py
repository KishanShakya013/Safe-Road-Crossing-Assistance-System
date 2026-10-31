from config import VEHICLE_CLASSES, LIGHT_CLASS
from lights import state_from_class_name
from tracker import Det
from ultralytics import YOLO

class Detector:
    def __init__(self, weights, light_weights, cfg, device=None):
        self.cfg, self.device = cfg, device
        self.coco = YOLO(weights)   
        names = self.coco.names
        wanted = set(VEHICLE_CLASSES) | ({LIGHT_CLASS} if not light_weights else set())
        self.coco_ids = [i for i, n in names.items() if n in wanted]
        self.light_model = YOLO(light_weights) if light_weights else None
        if self.light_model:
            mapped = {n: state_from_class_name(n) for n in self.light_model.names.values()}
            print(f"[INFO] Light model classes -> states: {mapped}")

    @staticmethod
    def _boxes(result, names, min_px=4):
        for b in result.boxes:
            x1, y1, x2, y2 = map(int, b.xyxy[0])
            if x2 - x1 >= min_px and y2 - y1 >= min_px:
                yield (x1, y1, x2, y2), names[int(b.cls[0])], float(b.conf[0])

    def detect(self, frame):
        c = self.cfg
        r = self.coco(frame, conf=c.conf, imgsz=c.imgsz, classes=self.coco_ids,
                      device=self.device, verbose=False)[0]
        dets = [Det(box, name, conf) for box, name, conf in self._boxes(r, self.coco.names)]
        if self.light_model:
            r = self.light_model(frame, conf=c.conf, imgsz=c.light_imgsz, device=self.device, verbose=False)[0]
            for box, name, conf in self._boxes(r, self.light_model.names):
                state = state_from_class_name(name)
                if state:                   
                    dets.append(Det(box, LIGHT_CLASS, conf, state))
        return dets
