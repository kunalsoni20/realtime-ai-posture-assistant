import cv2
import time
from flask import Flask, render_template, Response, request, jsonify
from pose_detector import PoseDetector

app = Flask(__name__)

# Global states
current_exercise_name = "bicep_curls"
current_stats = {
    "exercise": "bicep_curls",
    "reps": 0,
    "stage": "up",
    "feedback": "READY",
    "angle": 0.0,
    "fps": 0.0
}

pose_detector = PoseDetector()


def generate_frames():
    """Generates MJPEG video stream with MediaPipe pose landmark estimation."""
    global current_stats
    cap = cv2.VideoCapture(0)
    
    prev_time = time.time()

    while True:
        success, frame = cap.read()
        if not success:
            # Fallback frame if no webcam is detected
            frame = cv2.imread("static/img/fallback_banner.jpg")
            if frame is None:
                import numpy as np
                frame = np.zeros((480, 640, 3), dtype=np.uint8)
                cv2.putText(frame, "Waiting for Camera Feed...", (120, 240),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 200), 2)
            time.sleep(0.04)
        else:
            frame, landmarks = pose_detector.find_pose(frame, draw=True)

        # FPS calculation
        curr_time = time.time()
        fps = 1.0 / (curr_time - prev_time) if (curr_time - prev_time) > 0 else 30.0
        prev_time = curr_time
        current_stats["fps"] = round(fps, 1)

        # Encode to JPEG
        ret, buffer = cv2.imencode('.jpg', frame)
        if not ret:
            continue
            
        frame_bytes = buffer.tobytes()
        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + frame_bytes + b'\r\n')


@app.route('/')
def index():
    """Render main real-time posture assistant dashboard."""
    return render_template('index.html')


@app.route('/video_feed')
def video_feed():
    """Video streaming route for MJPEG feed."""
    return Response(generate_frames(),
                    mimetype='multipart/x-mixed-replace; boundary=frame')


@app.route('/api/select_exercise', methods=['POST'])
def select_exercise():
    """Select active exercise."""
    global current_exercise_name
    data = request.get_json() or {}
    exercise = data.get('exercise', 'bicep_curls')
    current_exercise_name = exercise
    current_stats["exercise"] = exercise
    current_stats["reps"] = 0
    current_stats["feedback"] = "READY"
    return jsonify({"status": "success", "exercise": exercise})


@app.route('/api/stats')
def get_stats():
    """Return live metrics in JSON for frontend HUD."""
    return jsonify(current_stats)


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=False)
