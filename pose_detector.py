import cv2
import mediapipe as mp
import numpy as np


class PoseDetector:
    """
    MediaPipe Pose estimation wrapper for real-time skeletal tracking.
    """
    def __init__(self,
                 static_image_mode: bool = False,
                 model_complexity: int = 1,
                 smooth_landmarks: bool = True,
                 min_detection_confidence: float = 0.5,
                 min_tracking_confidence: float = 0.5):
        try:
            from mediapipe.python.solutions import drawing_utils as mp_drawing
            from mediapipe.python.solutions import drawing_styles as mp_drawing_styles
            from mediapipe.python.solutions import pose as mp_pose
            self.mp_drawing = mp_drawing
            self.mp_drawing_styles = mp_drawing_styles
            self.mp_pose = mp_pose
        except (ImportError, AttributeError):
            if hasattr(mp, 'solutions'):
                self.mp_drawing = mp.solutions.drawing_utils
                self.mp_drawing_styles = mp.solutions.drawing_styles
                self.mp_pose = mp.solutions.pose
            else:
                self.mp_drawing = None
                self.mp_drawing_styles = None
                self.mp_pose = None

        if self.mp_pose is not None:
            self.pose = self.mp_pose.Pose(
                static_image_mode=static_image_mode,
                model_complexity=model_complexity,
                smooth_landmarks=smooth_landmarks,
                min_detection_confidence=min_detection_confidence,
                min_tracking_confidence=min_tracking_confidence
            )
        else:
            self.pose = None

    def find_pose(self, image: np.ndarray, draw: bool = True):
        """
        Processes BGR image through MediaPipe Pose pipeline.
        Returns processed image and pose landmarks list.
        """
        if self.pose is None:
            return image, None

        img_rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
        img_rgb.flags.writeable = False
        results = self.pose.process(img_rgb)
        img_rgb.flags.writeable = True

        landmarks = None
        if results.pose_landmarks:
            landmarks = results.pose_landmarks.landmark
            if draw:
                self.mp_drawing.draw_landmarks(
                    image,
                    results.pose_landmarks,
                    self.mp_pose.POSE_CONNECTIONS,
                    landmark_drawing_spec=self.mp_drawing_styles.get_default_pose_landmarks_style()
                )

        return image, landmarks

    def close(self):
        """Releases MediaPipe pose resources."""
        if hasattr(self, 'pose') and self.pose:
            self.pose.close()
