import os
import cv2
from demo_generator import DemoWorkoutGenerator


class VideoSourceManager:
    """
    Smart Video Source Handler for Real-Time AI Workout Assistant.
    Supports Live Webcam (0), Custom Video Uploads, and Cloud Fallback Demo Mode.
    Automatically detects headless/server environments and activates Demo Mode.
    """
    MODE_WEBCAM = "webcam"
    MODE_DEMO = "demo"
    MODE_UPLOAD = "upload"

    def __init__(self, pose_detector, default_mode: str = "webcam"):
        self.pose_detector = pose_detector
        self.mode = default_mode
        self.cap = None
        self.upload_path = None
        self.demo_gen = DemoWorkoutGenerator()
        self._init_source()

    def _init_source(self):
        """Initializes video capture or falls back to demo mode."""
        if self.cap is not None:
            self.cap.release()
            self.cap = None

        if self.mode == self.MODE_WEBCAM:
            self.cap = cv2.VideoCapture(0)
            # Test if webcam can actually read a valid frame
            if not self.cap.isOpened():
                print("[VideoSourceManager] Hardware webcam not found. Switching to Demo Mode.")
                self.mode = self.MODE_DEMO
                self.cap = None
            else:
                success, test_frame = self.cap.read()
                if not success or test_frame is None:
                    print("[VideoSourceManager] Hardware webcam cannot read frames. Switching to Demo Mode.")
                    self.mode = self.MODE_DEMO
                    self.cap.release()
                    self.cap = None

        elif self.mode == self.MODE_UPLOAD and self.upload_path and os.path.exists(self.upload_path):
            self.cap = cv2.VideoCapture(self.upload_path)
            if not self.cap.isOpened():
                self.mode = self.MODE_DEMO
                self.cap = None
        else:
            self.mode = self.MODE_DEMO

    def set_source(self, mode: str, upload_path: str = None) -> str:
        """Switch video source mode."""
        self.mode = mode
        if upload_path:
            self.upload_path = upload_path
        self._init_source()
        return self.mode

    def get_frame(self, exercise_name: str):
        """
        Retrieves next frame and pose landmarks.
        Returns:
            tuple: (frame: np.ndarray, landmarks: list or None)
        """
        if self.mode == self.MODE_DEMO or self.cap is None:
            frame, landmarks = self.demo_gen.generate_frame(exercise_name)
            return frame, landmarks

        success, frame = self.cap.read()
        if not success or frame is None:
            if self.mode == self.MODE_UPLOAD:
                # Loop video file
                self.cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
                success, frame = self.cap.read()
            if not success or frame is None:
                # Fallback to demo mode if capture drops
                return self.demo_gen.generate_frame(exercise_name)

        frame, landmarks = self.pose_detector.find_pose(frame, draw=True)
        return frame, landmarks

    def release(self):
        if self.cap is not None:
            self.cap.release()
