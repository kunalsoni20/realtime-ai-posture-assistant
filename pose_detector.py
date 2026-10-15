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
        self.mp_drawing = mp.solutions.drawing_utils
        self.mp_drawing_styles = mp.solutions.drawing_styles
        self.mp_pose = mp.solutions.pose
        self.pose = self.mp_pose.Pose(
            static_image_mode=static_image_mode,
            model_complexity=model_complexity,
            smooth_landmarks=smooth_landmarks,
            min_detection_confidence=min_detection_confidence,
            min_tracking_confidence=min_tracking_confidence
        )

    def find_pose(self, image: np.ndarray, draw: bool = True):
        """
        Processes BGR image through MediaPipe Pose pipeline.
        Returns processed image and pose landmarks list.
        """
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
