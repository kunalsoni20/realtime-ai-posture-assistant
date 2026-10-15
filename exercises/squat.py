import numpy as np
from .base import BaseExercise


class SquatDetector(BaseExercise):
    """
    Real-time Squat pose tracker and posture depth validator.
    Tracks Hip, Knee, and Ankle angles using NumPy vector geometry.
    Monitors squat depth, forward torso collapse, and knee alignment.
    """
    STANDING_KNEE_ANGLE = 160.0  # Upright standing position
    SQUAT_DEPTH_KNEE_ANGLE = 95.0 # Parallel/deep squat depth
    MIN_CHEST_HIP_ANGLE = 65.0    # Chest uprightness threshold

    def __init__(self):
        super().__init__(name="Squats")
        self._deepest_angle_in_rep = 180.0

    def reset(self) -> None:
        super().reset()
        self._deepest_angle_in_rep = 180.0

    def process(self, landmarks, frame_shape: tuple) -> dict:
        self.total_frames += 1

        # Determine leg with best visibility
        left_leg_vis = min(landmarks[self.LEFT_HIP].visibility,
                           landmarks[self.LEFT_KNEE].visibility,
                           landmarks[self.LEFT_ANKLE].visibility)
        right_leg_vis = min(landmarks[self.RIGHT_HIP].visibility,
                            landmarks[self.RIGHT_KNEE].visibility,
                            landmarks[self.RIGHT_ANKLE].visibility)

        if left_leg_vis >= right_leg_vis:
            shoulder_idx = self.LEFT_SHOULDER
            hip_idx = self.LEFT_HIP
            knee_idx = self.LEFT_KNEE
            ankle_idx = self.LEFT_ANKLE
            side = "Left"
        else:
            shoulder_idx = self.RIGHT_SHOULDER
            hip_idx = self.RIGHT_HIP
            knee_idx = self.RIGHT_KNEE
            ankle_idx = self.RIGHT_ANKLE
            side = "Right"

        shoulder = self.get_landmark_coord(landmarks, shoulder_idx)
        hip = self.get_landmark_coord(landmarks, hip_idx)
        knee = self.get_landmark_coord(landmarks, knee_idx)
        ankle = self.get_landmark_coord(landmarks, ankle_idx)

        # 1. Compute Knee Angle (Hip-Knee-Ankle)
        knee_angle = self.calculate_angle(hip, knee, ankle)
        self.current_angle = round(knee_angle, 1)

        # 2. Compute Torso/Hip Angle (Shoulder-Hip-Knee)
        hip_angle = self.calculate_angle(shoulder, hip, knee)

        # 3. Posture Checks: Depth, Torso Lean, and Knee Forward Alignment
        is_posture_flawed = False
        warning_msg = None

        if hip_angle < self.MIN_CHEST_HIP_ANGLE:
            is_posture_flawed = True
            warning_msg = "FIX POSTURE: KEEP CHEST UP"

        # Check knee forward travel relative to ankle
        knee_travel = abs(knee[0] - ankle[0])
        if knee_travel > 0.16 and knee_angle < 120:
            is_posture_flawed = True
            warning_msg = "FIX POSTURE: KNEES TOO FORWARD"

        # 4. State Machine & Repetition Counting
        if knee_angle < self.SQUAT_DEPTH_KNEE_ANGLE:
            self.stage = "down"

        if self.stage == "down":
            self._deepest_angle_in_rep = min(self._deepest_angle_in_rep, knee_angle)

        if knee_angle > self.STANDING_KNEE_ANGLE:
            if self.stage == "down":
                if self._deepest_angle_in_rep <= self.SQUAT_DEPTH_KNEE_ANGLE + 5.0:
                    self.reps += 1
                else:
                    is_posture_flawed = True
                    warning_msg = "FIX POSTURE: SQUAT DEEPER"
                self.stage = "up"
                self._deepest_angle_in_rep = 180.0

        # In intermediate descent, check for shallow squats
        if 100 < knee_angle < 140 and self.stage == "down" and not is_posture_flawed:
            warning_msg = "SQUAT DEEPER (HIT 90°)"

        # 5. Form Feedback Evaluation
        if is_posture_flawed:
            self.warning_count += 1
            self.feedback = warning_msg
        else:
            self.correct_frames += 1
            self.feedback = "GOOD FORM"

        return {
            "exercise": self.name,
            "reps": self.reps,
            "stage": self.stage,
            "feedback": self.feedback,
            "angle": self.current_angle,
            "side": side,
            "accuracy": self.get_accuracy_score(),
            "keypoints": {
                "hip": hip,
                "knee": knee,
                "ankle": ankle
            }
        }
