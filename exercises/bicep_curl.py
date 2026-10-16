import time
import numpy as np
from .base import BaseExercise


class BicepCurlDetector(BaseExercise):
    """
    Real-time Bicep Curl pose tracker and form validator.
    Tracks Shoulder, Elbow, and Wrist angles using NumPy vector geometry.
    Monitors elbow drift and torso swinging to ensure strict lifting mechanics.
    """
    UP_THRESHOLD = 45.0      # Arm curled up
    DOWN_THRESHOLD = 155.0   # Arm fully extended down
    ELBOW_DRIFT_MAX = 0.09   # Maximum allowed normalized horizontal elbow drift

    def __init__(self):
        super().__init__(name="Bicep Curls")

    def process(self, landmarks, frame_shape: tuple) -> dict:
        self.total_frames += 1

        # Determine arm with best visibility
        left_arm_vis = min(landmarks[self.LEFT_SHOULDER].visibility,
                           landmarks[self.LEFT_ELBOW].visibility,
                           landmarks[self.LEFT_WRIST].visibility)
        right_arm_vis = min(landmarks[self.RIGHT_SHOULDER].visibility,
                            landmarks[self.RIGHT_ELBOW].visibility,
                            landmarks[self.RIGHT_WRIST].visibility)

        l_shoulder = self.get_landmark_coord(landmarks, self.LEFT_SHOULDER)
        l_elbow = self.get_landmark_coord(landmarks, self.LEFT_ELBOW)
        l_wrist = self.get_landmark_coord(landmarks, self.LEFT_WRIST)
        l_hip = self.get_landmark_coord(landmarks, self.LEFT_HIP)

        r_shoulder = self.get_landmark_coord(landmarks, self.RIGHT_SHOULDER)
        r_elbow = self.get_landmark_coord(landmarks, self.RIGHT_ELBOW)
        r_wrist = self.get_landmark_coord(landmarks, self.RIGHT_WRIST)
        r_hip = self.get_landmark_coord(landmarks, self.RIGHT_HIP)

        l_angle = self.calculate_angle(l_shoulder, l_elbow, l_wrist)
        r_angle = self.calculate_angle(r_shoulder, r_elbow, r_wrist)

        # Track whichever arm has better visibility, or whichever is actively flexing
        if abs(left_arm_vis - right_arm_vis) > 0.15:
            use_left = (left_arm_vis > right_arm_vis)
        else:
            use_left = (l_angle <= r_angle)

        if use_left:
            shoulder, elbow, wrist, hip = l_shoulder, l_elbow, l_wrist, l_hip
            elbow_angle = l_angle
            arm_side = "Left"
        else:
            shoulder, elbow, wrist, hip = r_shoulder, r_elbow, r_wrist, r_hip
            elbow_angle = r_angle
            arm_side = "Right"

        self.current_angle = round(elbow_angle, 1)

        # 2. Form Issue Checks: Elbow Swinging and Torso Cheating
        elbow_drift = abs(elbow[0] - shoulder[0])
        torso_drift = abs(shoulder[0] - hip[0])

        is_posture_flawed = False
        warning_msg = None

        if elbow_drift > self.ELBOW_DRIFT_MAX:
            is_posture_flawed = True
            warning_msg = "FIX POSTURE: KEEP ELBOW TUCKED"
        elif torso_drift > 0.12:
            is_posture_flawed = True
            warning_msg = "FIX POSTURE: DO NOT SWING TORSO"

        # 3. State Machine & Repetition Counting with Time Debounce
        curr_time = time.time()
        if elbow_angle > self.DOWN_THRESHOLD:
            self.stage = "down"

        if elbow_angle < self.UP_THRESHOLD and self.stage == "down":
            if (curr_time - self.last_rep_time) > 1.2:
                self.reps += 1
                self.last_rep_time = curr_time
            self.stage = "up"

        # 4. Form Feedback Evaluation
        if is_posture_flawed:
            self.warning_count += 1
            self.feedback = warning_msg
        else:
            self.correct_frames += 1
            if self.stage == "down" and elbow_angle > 140:
                self.feedback = "GOOD FORM"
            elif self.stage == "up" and elbow_angle < 60:
                self.feedback = "GOOD FORM"
            else:
                self.feedback = "GOOD FORM"

        return {
            "exercise": self.name,
            "reps": self.reps,
            "stage": self.stage,
            "feedback": self.feedback,
            "angle": self.current_angle,
            "arm_side": arm_side,
            "accuracy": self.get_accuracy_score(),
            "keypoints": {
                "shoulder": shoulder,
                "elbow": elbow,
                "wrist": wrist
            }
        }
