from config import VEHICLE_CLASSES, LIGHT_CLASS
from tracker import Det
from ultralytics import YOLO

class Detector:
    def __init__(self, weights, cfg):
        self.cfg = cfg
        self.coco = YOLO(weights)   
        names = self.coco.names
        wanted = set(VEHICLE_CLASSES)|{LIGHT_CLASS}
        self.coco_ids = [i for i, n in names.items() if n in wanted]
        self.light_model =  None
        self.device=None

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
        return dets
