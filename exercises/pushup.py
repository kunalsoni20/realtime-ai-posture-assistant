import numpy as np
from .base import BaseExercise


class PushupDetector(BaseExercise):
    """
    Real-time Push-up pose tracker and spine alignment validator.
    Tracks Shoulder, Elbow, Wrist angles for arm flexion and
    Shoulder, Hip, Ankle angles for full body plank alignment.
    Flags sagging hips, piking, and insufficient chest depth.
    """
    ELBOW_EXTENDED_ANGLE = 155.0  # Top plank position
    ELBOW_FLEXED_ANGLE = 90.0     # Bottom chest-to-ground position
    MIN_BODY_ALIGNMENT = 155.0    # Sagging hips threshold
    MAX_BODY_ALIGNMENT = 195.0    # Piking/high hips threshold

    def __init__(self):
        super().__init__(name="Push-ups")
        self._deepest_elbow_angle = 180.0

    def reset(self) -> None:
        super().reset()
        self._deepest_elbow_angle = 180.0

    def process(self, landmarks, frame_shape: tuple) -> dict:
        self.total_frames += 1

        # Determine side with highest visibility
        left_vis = min(landmarks[self.LEFT_SHOULDER].visibility,
                       landmarks[self.LEFT_ELBOW].visibility,
                       landmarks[self.LEFT_WRIST].visibility,
                       landmarks[self.LEFT_HIP].visibility,
                       landmarks[self.LEFT_ANKLE].visibility)
        right_vis = min(landmarks[self.RIGHT_SHOULDER].visibility,
                        landmarks[self.RIGHT_ELBOW].visibility,
                        landmarks[self.RIGHT_WRIST].visibility,
                        landmarks[self.RIGHT_HIP].visibility,
                        landmarks[self.RIGHT_ANKLE].visibility)

        if left_vis >= right_vis:
            shoulder_idx = self.LEFT_SHOULDER
            elbow_idx = self.LEFT_ELBOW
            wrist_idx = self.LEFT_WRIST
            hip_idx = self.LEFT_HIP
            ankle_idx = self.LEFT_ANKLE
            side = "Left"
        else:
            shoulder_idx = self.RIGHT_SHOULDER
            elbow_idx = self.RIGHT_ELBOW
            wrist_idx = self.RIGHT_WRIST
            hip_idx = self.RIGHT_HIP
            ankle_idx = self.RIGHT_ANKLE
            side = "Right"

        shoulder = self.get_landmark_coord(landmarks, shoulder_idx)
        elbow = self.get_landmark_coord(landmarks, elbow_idx)
        wrist = self.get_landmark_coord(landmarks, wrist_idx)
        hip = self.get_landmark_coord(landmarks, hip_idx)
        ankle = self.get_landmark_coord(landmarks, ankle_idx)

        # 1. Compute Elbow Angle (Shoulder-Elbow-Wrist)
        elbow_angle = self.calculate_angle(shoulder, elbow, wrist)
        self.current_angle = round(elbow_angle, 1)

        # 2. Compute Full Body Alignment (Shoulder-Hip-Ankle)
        body_alignment = self.calculate_angle(shoulder, hip, ankle)

        # 3. Posture Checks: Sagging Hips & Piking
        is_posture_flawed = False
        warning_msg = None

        if body_alignment < self.MIN_BODY_ALIGNMENT:
            is_posture_flawed = True
            warning_msg = "FIX POSTURE: SAGGING HIPS (ENGAGE CORE)"
        elif body_alignment > self.MAX_BODY_ALIGNMENT:
            is_posture_flawed = True
            warning_msg = "FIX POSTURE: HIPS TOO HIGH"

        # 4. State Machine & Repetition Counting
        if elbow_angle < self.ELBOW_FLEXED_ANGLE:
            self.stage = "down"

        if self.stage == "down":
            self._deepest_elbow_angle = min(self._deepest_elbow_angle, elbow_angle)

        if elbow_angle > self.ELBOW_EXTENDED_ANGLE:
            if self.stage == "down":
                if self._deepest_elbow_angle <= self.ELBOW_FLEXED_ANGLE + 10.0:
                    self.reps += 1
                else:
                    is_posture_flawed = True
                    warning_msg = "FIX POSTURE: LOWER CHEST FULLY"
                self.stage = "up"
                self._deepest_elbow_angle = 180.0

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
            "body_alignment": round(body_alignment, 1),
            "side": side,
            "accuracy": self.get_accuracy_score(),
            "keypoints": {
                "shoulder": shoulder,
                "elbow": elbow,
                "wrist": wrist,
                "hip": hip,
                "ankle": ankle
            }
        }
