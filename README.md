pip install -r requirements.txt

python main.py                          # NO video / NO weights needed -> built-in demo
python main.py --source road.mp4        # your video (yolov8n.pt downloads automatically)
python main.py --source road.mp4 --show # with a preview window (q to quit)
python main.py --source 0 --show        # live webcam

