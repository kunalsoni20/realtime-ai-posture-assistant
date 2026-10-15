import cv2
import time
import os
from flask import Flask, render_template, Response, request, jsonify, send_file
from pose_detector import PoseDetector
from exercises import BicepCurlDetector, SquatDetector, PushupDetector
from hud_overlay import HUDOverlay
import session_logger

app = Flask(__name__)

# Initialize exercise detectors
exercise_detectors = {
    "bicep_curls": BicepCurlDetector(),
    "squats": SquatDetector(),
    "pushups": PushupDetector()
}

current_exercise_name = "bicep_curls"
active_detector = exercise_detectors[current_exercise_name]

# Active session tracking
session_state = {
    "is_active": False,
    "start_time": time.time(),
    "fps_history": []
}

current_stats = {
    "exercise": "Bicep Curls",
    "exercise_key": "bicep_curls",
    "reps": 0,
    "stage": "up",
    "feedback": "READY",
    "angle": 0.0,
    "accuracy": 100.0,
    "fps": 0.0,
    "is_active": False
}

pose_detector = PoseDetector()
session_logger.init_logger()


def generate_frames():
    """Generates MJPEG video stream with MediaPipe pose tracking and 25+ FPS HUD overlay."""
    global current_stats, active_detector, session_state
    cap = cv2.VideoCapture(0)
    
    prev_time = time.time()
    fps_smooth = 28.0

    while True:
        success, frame = cap.read()
        if not success:
            import numpy as np
            frame = np.zeros((480, 640, 3), dtype=np.uint8)
            cv2.putText(frame, "Waiting for Camera Feed...", (120, 240),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 200), 2)
            time.sleep(0.04)
        else:
            frame, landmarks = pose_detector.find_pose(frame, draw=True)
            if landmarks:
                metrics = active_detector.process(landmarks, frame.shape)
                current_stats["reps"] = metrics["reps"]
                current_stats["stage"] = metrics["stage"]
                current_stats["feedback"] = metrics["feedback"]
                current_stats["angle"] = metrics["angle"]
                current_stats["accuracy"] = metrics["accuracy"]

        # Real-time FPS calculation
        curr_time = time.time()
        instant_fps = 1.0 / (curr_time - prev_time) if (curr_time - prev_time) > 0 else 30.0
        prev_time = curr_time
        fps_smooth = 0.85 * fps_smooth + 0.15 * instant_fps
        current_stats["fps"] = round(fps_smooth, 1)

        if session_state["is_active"]:
            session_state["fps_history"].append(fps_smooth)

        # Render 25+ FPS HUD Overlay on frame
        frame = HUDOverlay.render(
            frame=frame,
            exercise_name=active_detector.name,
            reps=current_stats["reps"],
            stage=current_stats["stage"],
            feedback=current_stats["feedback"],
            angle=current_stats["angle"],
            fps=fps_smooth
        )

        # Encode frame as JPEG
        ret, buffer = cv2.imencode('.jpg', frame, [int(cv2.IMWRITE_JPEG_QUALITY), 85])
        if not ret:
            continue
            
        frame_bytes = buffer.tobytes()
        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + frame_bytes + b'\r\n')


@app.route('/')
def index():
    """Render main real-time posture assistant dashboard."""
    return render_template('index.html')


@app.route('/analytics')
def analytics():
    """Render Pandas workout session analytics page."""
    metrics = session_logger.get_summary_metrics()
    sessions = session_logger.get_recent_sessions(limit=50)
    return render_template('analytics.html', metrics=metrics, sessions=sessions)


@app.route('/video_feed')
def video_feed():
    """Video streaming route for MJPEG feed."""
    return Response(generate_frames(),
                    mimetype='multipart/x-mixed-replace; boundary=frame')


@app.route('/api/select_exercise', methods=['POST'])
def select_exercise():
    """Switch active exercise and reset counters."""
    global current_exercise_name, active_detector, current_stats
    data = request.get_json() or {}
    exercise_key = data.get('exercise', 'bicep_curls')

    if exercise_key in exercise_detectors:
        current_exercise_name = exercise_key
        active_detector = exercise_detectors[exercise_key]
        active_detector.reset()

        current_stats["exercise"] = active_detector.name
        current_stats["exercise_key"] = exercise_key
        current_stats["reps"] = 0
        current_stats["stage"] = "up"
        current_stats["feedback"] = "READY"
        current_stats["angle"] = 0.0
        current_stats["accuracy"] = 100.0

    return jsonify({"status": "success", "exercise": current_stats["exercise"]})


@app.route('/api/session/start', methods=['POST'])
def start_session():
    """Start timing and recording a new workout session."""
    global session_state
    session_state["is_active"] = True
    session_state["start_time"] = time.time()
    session_state["fps_history"] = []
    current_stats["is_active"] = True
    active_detector.reset()
    return jsonify({"status": "started", "exercise": active_detector.name})


@app.route('/api/session/end', methods=['POST'])
def end_session():
    """End current workout session and persist record via Pandas."""
    global session_state
    duration = int(time.time() - session_state["start_time"])
    session_state["is_active"] = False
    current_stats["is_active"] = False

    fps_list = session_state["fps_history"]
    avg_fps = sum(fps_list) / len(fps_list) if fps_list else current_stats["fps"]

    log_entry = session_logger.log_workout_session(
        exercise=active_detector.name,
        reps_completed=active_detector.reps,
        accuracy_score=active_detector.get_accuracy_score(),
        posture_warnings=active_detector.warning_count,
        avg_fps=avg_fps,
        duration_seconds=duration
    )

    return jsonify({"status": "logged", "session": log_entry})


@app.route('/api/session/reset', methods=['POST'])
def reset_session():
    """Reset current counter."""
    active_detector.reset()
    current_stats["reps"] = 0
    current_stats["stage"] = "up"
    current_stats["feedback"] = "READY"
    current_stats["angle"] = 0.0
    current_stats["accuracy"] = 100.0
    return jsonify({"status": "reset"})


@app.route('/api/stats')
def get_stats():
    """Return live metrics in JSON for frontend HUD."""
    return jsonify(current_stats)


@app.route('/api/export-logs')
def export_logs():
    """Export workout session logs as CSV attachment."""
    return send_file(
        session_logger.CSV_FILE_PATH,
        mimetype='text/csv',
        as_attachment=True,
        download_name='workout_logs.csv'
    )


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=False)
