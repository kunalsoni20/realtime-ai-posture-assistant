import time
import cv2
import numpy as np
from typing import Tuple, Dict, Any, Optional

from pose_detector import PoseDetector
from exercises import BaseExercise, BicepCurlDetector, SquatDetector, PushupDetector
from hud_overlay import HUDOverlay
from demo_generator import DemoWorkoutGenerator


class ExerciseVideoProcessor:
    """
    Central Exercise Video Processor class.
    Manages pose estimation, joint angle trigonometry, repetition state machines,
    and 25+ FPS real-time HUD telemetry overlays.
    """
    def __init__(self):
        self.pose_detector = PoseDetector(
            model_complexity=1,
            smooth_landmarks=True,
            min_detection_confidence=0.5,
            min_tracking_confidence=0.5
        )
        self.detectors: Dict[str, BaseExercise] = {
            "bicep_curls": BicepCurlDetector(),
            "squats": SquatDetector(),
            "pushups": PushupDetector()
        }
        self.current_key = "bicep_curls"
        self.detector = self.detectors[self.current_key]
        self.demo_gen = DemoWorkoutGenerator()
        
        self.prev_time = time.time()
        self.fps_smooth = 28.5

    def set_exercise(self, exercise_key: str) -> BaseExercise:
        """Switches active exercise detector and resets rep state."""
        if exercise_key in self.detectors:
            self.current_key = exercise_key
            self.detector = self.detectors[exercise_key]
            self.detector.reset()
        return self.detector

    def reset_reps(self) -> None:
        """Resets current exercise repetition counter and posture warnings."""
        self.detector.reset()

    def process_frame(self, frame: np.ndarray, is_demo: bool = False) -> Tuple[np.ndarray, Dict[str, Any]]:
        """
        Processes a single video frame.
        Args:
            frame: BGR image numpy array.
            is_demo: If True, uses demo generator synthetic landmarks.
        Returns:
            tuple: (annotated_frame_bgr: np.ndarray, metrics: dict)
        """
        curr_time = time.time()
        dt = curr_time - self.prev_time
        if dt > 0:
            instant_fps = 1.0 / dt
            self.fps_smooth = 0.88 * self.fps_smooth + 0.12 * instant_fps
        self.prev_time = curr_time

        landmarks = None
        if is_demo:
            frame, landmarks = self.demo_gen.generate_frame(self.current_key)
        else:
            frame, landmarks = self.pose_detector.find_pose(frame, draw=True)

        metrics = {
            "exercise": self.detector.name,
            "exercise_key": self.current_key,
            "reps": self.detector.reps,
            "stage": self.detector.stage,
            "feedback": self.detector.feedback,
            "angle": self.detector.current_angle,
            "accuracy": self.detector.get_accuracy_score(),
            "warnings_count": self.detector.warning_count,
            "fps": round(self.fps_smooth, 1),
            "is_flawed": "FIX" in self.detector.feedback or "SAGGING" in self.detector.feedback
        }

        if landmarks is not None:
            calc_metrics = self.detector.process(landmarks, frame.shape)
            metrics.update({
                "reps": calc_metrics["reps"],
                "stage": calc_metrics["stage"],
                "feedback": calc_metrics["feedback"],
                "angle": calc_metrics["angle"],
                "accuracy": calc_metrics["accuracy"],
                "is_flawed": "FIX" in calc_metrics["feedback"] or "SAGGING" in calc_metrics["feedback"]
            })

        # Render real-time HUD telemetry overlay
        annotated_frame = HUDOverlay.render(
            frame=frame,
            exercise_name=self.detector.name,
            reps=metrics["reps"],
            stage=metrics["stage"],
            feedback=metrics["feedback"],
            angle=metrics["angle"],
            fps=self.fps_smooth
        )

        return annotated_frame, metrics

    def release(self):
        """Releases underlying computer vision pipelines."""
        self.pose_detector.close()
