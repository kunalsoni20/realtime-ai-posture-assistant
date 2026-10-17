import os
import time
import base64
import cv2
import numpy as np
from flask import Flask, render_template, Response, request, jsonify, send_file
from werkzeug.utils import secure_filename
from pose_detector import PoseDetector
from exercises import BicepCurlDetector, SquatDetector, PushupDetector
from hud_overlay import HUDOverlay
from video_source import VideoSourceManager
import session_logger

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = os.path.join(os.path.dirname(__file__), 'uploads')
app.config['MAX_CONTENT_LENGTH'] = 50 * 1024 * 1024  # 50MB max upload
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# Exercise detectors dictionary for live user workouts (Webcam & Uploads)
exercise_detectors = {
    "bicep_curls": BicepCurlDetector(),
    "squats": SquatDetector(),
    "pushups": PushupDetector()
}

# Separate demo detectors so simulated demo reps NEVER bleed into user workout
demo_detectors = {
    "bicep_curls": BicepCurlDetector(),
    "squats": SquatDetector(),
    "pushups": PushupDetector()
}

current_exercise_name = "bicep_curls"
active_detector = exercise_detectors[current_exercise_name]

# Global pose detector & smart video source manager (default to demo so landing page is never blank)
pose_detector = PoseDetector()
video_source_manager = VideoSourceManager(pose_detector, default_mode="demo")

# Workout session timing state
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
    "is_active": False,
    "source_mode": video_source_manager.mode
}

session_logger.init_logger()


def generate_frames():
    """Generates real-time MJPEG stream with MediaPipe pose processing and 25+ FPS HUD overlay."""
    global current_stats, active_detector, demo_detectors, session_state, video_source_manager
    
    prev_time = time.time()
    fps_smooth = 28.5

    while True:
        # Pause background generator during webcam mode to prevent ghost rep counting
        if video_source_manager.mode == "webcam":
            time.sleep(0.15)
            continue

        # Retrieve frame from active video source (Upload or Cloud Demo Mode)
        frame, landmarks = video_source_manager.get_frame(current_exercise_name)
        if frame is None:
            time.sleep(0.15)
            continue

        if video_source_manager.mode == "demo":
            detector = demo_detectors[current_exercise_name]
        else:
            detector = active_detector

        metrics = {"reps": 0, "stage": "up", "feedback": "READY", "angle": 0.0, "accuracy": 100.0}
        if landmarks is not None:
            metrics = detector.process(landmarks, frame.shape)
            # Only update current_stats if source is not webcam
            if video_source_manager.mode != "webcam":
                current_stats["reps"] = metrics["reps"]
                current_stats["stage"] = metrics["stage"]
                current_stats["feedback"] = metrics["feedback"]
                current_stats["angle"] = metrics["angle"]
                current_stats["accuracy"] = metrics["accuracy"]

        # Real-time FPS calculation & EMA smoothing
        curr_time = time.time()
        instant_fps = 1.0 / (curr_time - prev_time) if (curr_time - prev_time) > 0 else 30.0
        prev_time = curr_time
        fps_smooth = 0.88 * fps_smooth + 0.12 * instant_fps
        current_stats["fps"] = round(fps_smooth, 1)
        current_stats["source_mode"] = video_source_manager.mode

        if session_state["is_active"]:
            session_state["fps_history"].append(fps_smooth)

        # Draw real-time 25+ FPS HUD Overlay
        frame = HUDOverlay.render(
            frame=frame,
            exercise_name=detector.name,
            reps=metrics["reps"],
            stage=metrics["stage"],
            feedback=metrics["feedback"],
            angle=metrics["angle"],
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
    """Render main dark-themed AI Workout Assistant dashboard."""
    return render_template('index.html', source_mode=video_source_manager.mode)


@app.route('/analytics')
def analytics():
    """Render Pandas workout session analytics page."""
    metrics = session_logger.get_summary_metrics()
    sessions = session_logger.get_recent_sessions(limit=50)
    return render_template('analytics.html', metrics=metrics, sessions=sessions)


@app.route('/video_feed')
def video_feed():
    """Video streaming route for OpenCV MJPEG feed."""
    return Response(generate_frames(),
                    mimetype='multipart/x-mixed-replace; boundary=frame')


@app.route('/api/process_frame', methods=['POST'])
def process_frame():
    """Processes browser client-side webcam frame through MediaPipe and returns annotated image and metrics."""
    global current_stats, active_detector, session_state

    try:
        if request.content_type and 'application/json' in request.content_type:
            data = request.get_json() or {}
            img_b64 = data.get('image', '')
            if ',' in img_b64:
                img_b64 = img_b64.split(',', 1)[1]
            img_bytes = base64.b64decode(img_b64)
        else:
            img_bytes = request.data

        nparr = np.frombuffer(img_bytes, np.uint8)
        frame = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        if frame is None:
            return jsonify({"status": "error", "message": "Failed to decode frame"}), 400

        # Run MediaPipe Pose Detection
        landmarks_data = []
        frame, landmarks = pose_detector.find_pose(frame, draw=False)
        if landmarks:
            metrics = active_detector.process(landmarks, frame.shape)
            current_stats["reps"] = metrics["reps"]
            current_stats["stage"] = metrics["stage"]
            current_stats["feedback"] = metrics["feedback"]
            current_stats["angle"] = metrics["angle"]
            current_stats["accuracy"] = metrics["accuracy"]

            for lm in landmarks:
                landmarks_data.append([round(float(lm.x), 3), round(float(lm.y), 3), round(float(lm.visibility), 2)])

        # Real-time FPS computation
        curr_time = time.time()
        fps_smooth = current_stats.get("fps", 28.0)
        if not hasattr(process_frame, "prev_time"):
            process_frame.prev_time = curr_time
        dt = curr_time - process_frame.prev_time
        if dt > 0:
            instant_fps = 1.0 / dt
            fps_smooth = 0.85 * fps_smooth + 0.15 * instant_fps
        process_frame.prev_time = curr_time
        current_stats["fps"] = round(fps_smooth, 1)
        current_stats["source_mode"] = "webcam"

        if session_state["is_active"]:
            session_state["fps_history"].append(fps_smooth)

        return jsonify({
            "status": "success",
            "metrics": current_stats,
            "landmarks": landmarks_data
        })
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


@app.route('/api/select_exercise', methods=['POST'])
def select_exercise():
    """Switch active exercise (Bicep Curls, Squats, Push-ups)."""
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

    return jsonify({
        "status": "success",
        "exercise": current_stats["exercise"],
        "exercise_key": current_exercise_name
    })


@app.route('/api/set_source', methods=['POST'])
def set_source():
    """Switch video source between 'webcam', 'demo', and 'upload'."""
    data = request.get_json() or {}
    mode = data.get('mode', 'webcam')
    actual_mode = video_source_manager.set_source(mode)
    current_stats["source_mode"] = actual_mode

    if actual_mode == "webcam":
        active_detector.reset()
        current_stats["reps"] = 0
        current_stats["stage"] = "up"
        current_stats["feedback"] = "READY"
        current_stats["angle"] = 0.0
        current_stats["accuracy"] = 100.0

    return jsonify({"status": "success", "mode": actual_mode})


@app.route('/api/upload_video', methods=['POST'])
def upload_video():
    """Handle custom video upload for pose analysis."""
    if 'video' not in request.files:
        return jsonify({"status": "error", "message": "No file uploaded"}), 400
        
    file = request.files['video']
    if file.filename == '':
        return jsonify({"status": "error", "message": "Empty filename"}), 400

    filename = secure_filename(file.filename)
    save_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    file.save(save_path)

    actual_mode = video_source_manager.set_source("upload", upload_path=save_path)
    current_stats["source_mode"] = actual_mode
    return jsonify({"status": "success", "mode": actual_mode, "filename": filename})


@app.route('/api/session/start', methods=['POST'])
def start_session():
    """Start recording a live workout session."""
    global session_state
    session_state["is_active"] = True
    session_state["start_time"] = time.time()
    session_state["fps_history"] = []
    current_stats["is_active"] = True
    active_detector.reset()
    return jsonify({"status": "started", "exercise": active_detector.name})


@app.route('/api/session/end', methods=['POST'])
def end_session():
    """End workout session and log summary to Pandas workout_logs.csv."""
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
    """Reset the current rep counter and metrics."""
    active_detector.reset()
    current_stats["reps"] = 0
    current_stats["stage"] = "up"
    current_stats["feedback"] = "READY"
    current_stats["angle"] = 0.0
    current_stats["accuracy"] = 100.0
    return jsonify({"status": "reset"})


@app.route('/api/stats')
def get_stats():
    """Return live JSON metrics for real-time frontend UI updates."""
    return jsonify(current_stats)


@app.route('/api/export-logs')
def export_logs():
    """Download workout session history as a CSV file."""
    return send_file(
        session_logger.CSV_FILE_PATH,
        mimetype='text/csv',
        as_attachment=True,
        download_name='workout_logs.csv'
    )


if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5050))
    print(f" * AI Workout Assistant running on http://127.0.0.1:{port}")
    app.run(host='0.0.0.0', port=port, debug=False)
