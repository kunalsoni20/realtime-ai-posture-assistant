from abc import ABC, abstractmethod
import numpy as np


class BaseExercise(ABC):
    """
    Abstract base class for exercise posture and rep tracking.
    """
    # MediaPipe Landmark Index Mapping
    NOSE = 0
    LEFT_EYE_INNER = 1
    LEFT_EYE = 2
    LEFT_EYE_OUTER = 3
    RIGHT_EYE_INNER = 4
    RIGHT_EYE = 5
    RIGHT_EYE_OUTER = 6
    LEFT_EAR = 7
    RIGHT_EAR = 8
    MOUTH_LEFT = 9
    MOUTH_RIGHT = 10
    LEFT_SHOULDER = 11
    RIGHT_SHOULDER = 12
    LEFT_ELBOW = 13
    RIGHT_ELBOW = 14
    LEFT_WRIST = 15
    RIGHT_WRIST = 16
    LEFT_PINKY = 17
    RIGHT_PINKY = 18
    LEFT_INDEX = 19
    RIGHT_INDEX = 20
    LEFT_THUMB = 21
    RIGHT_THUMB = 22
    LEFT_HIP = 23
    RIGHT_HIP = 24
    LEFT_KNEE = 25
    RIGHT_KNEE = 26
    LEFT_ANKLE = 27
    RIGHT_ANKLE = 28
    LEFT_HEEL = 29
    RIGHT_HEEL = 30
    LEFT_FOOT_INDEX = 31
    RIGHT_FOOT_INDEX = 32

    def __init__(self, name: str = "Base Exercise"):
        self.name = name
        self.reps = 0
        self.stage = "up"
        self.feedback = "READY"
        self.current_angle = 0.0
        self.warning_count = 0
        self.correct_frames = 0
        self.total_frames = 0

    def get_landmark_coord(self, landmarks, idx: int):
        """Extracts (x, y) 2D normalized coordinates for a given landmark index."""
        lm = landmarks[idx]
        return [lm.x, lm.y]

    @abstractmethod
    def process(self, landmarks, frame_shape: tuple) -> dict:
        """Process landmarks for the current frame, update state, and return metrics."""
        pass

    def reset(self) -> None:
        """Reset exercise counters and state."""
        self.reps = 0
        self.stage = "up"
        self.feedback = "READY"
        self.current_angle = 0.0
        self.warning_count = 0
        self.correct_frames = 0
        self.total_frames = 0
