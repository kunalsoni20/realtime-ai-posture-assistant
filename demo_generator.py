import math
import time
import cv2
import numpy as np


class SyntheticLandmark:
    """Mock MediaPipe NormalizedLandmark for simulated demo mode."""
    def __init__(self, x: float, y: float, z: float = 0.0, visibility: float = 0.99):
        self.x = x
        self.y = y
        self.z = z
        self.visibility = visibility


class DemoWorkoutGenerator:
    """
    Generates synthetic real-time workout video frames and landmark streams
    for Cloud Deployment Fallback (Render, Hugging Face Spaces, etc.) where
    no physical hardware webcam is connected.
    """
    WIDTH = 640
    HEIGHT = 480

    def __init__(self):
        self.start_time = time.time()
        self.rep_count = 0
        self.prev_phase = 0.0

    def generate_frame(self, exercise_name: str):
        """
        Returns (frame, landmarks_list) simulating the given exercise.
        """
        t = time.time() - self.start_time
        frame = np.zeros((self.HEIGHT, self.WIDTH, 3), dtype=np.uint8)

        # 1. Render Modern Gym Studio Environment Background
        # Vertical gradient
        for y in range(self.HEIGHT):
            ratio = y / self.HEIGHT
            b = int(22 + 10 * ratio)
            g = int(18 + 8 * ratio)
            r = int(15 + 5 * ratio)
            frame[y, :] = (b, g, r)

        # Draw studio gym floor grid & neon accent line
        cv2.line(frame, (0, 390), (self.WIDTH, 390), (60, 80, 100), 2)
        cv2.line(frame, (0, 392), (self.WIDTH, 392), (212, 182, 6), 1) # Cyan neon floor reflection
        for gx in range(40, self.WIDTH, 60):
            cv2.line(frame, (gx, 390), (int(gx * 1.2) - 50, self.HEIGHT), (35, 45, 60), 1)

        # Studio lighting glow circles in background
        cv2.circle(frame, (120, 100), 60, (30, 45, 35), -1) # Emerald subtle ambient
        cv2.circle(frame, (520, 120), 70, (45, 40, 25), -1) # Cyan subtle ambient

        # 33 landmarks initialized to neutral off-screen points
        landmarks = [SyntheticLandmark(0.5, 0.5, 0.0, 0.1) for _ in range(33)]

        if exercise_name == "bicep_curls":
            frame, landmarks = self._render_bicep_curls(frame, landmarks, t)
        elif exercise_name == "squats":
            frame, landmarks = self._render_squats(frame, landmarks, t)
        elif exercise_name == "pushups":
            frame, landmarks = self._render_pushups(frame, landmarks, t)
        else:
            frame, landmarks = self._render_bicep_curls(frame, landmarks, t)

        return frame, landmarks

    def _render_bicep_curls(self, frame, landmarks, t):
        """Simulates standing athlete performing bicep curls."""
        cycle_time = 3.6
        phase = (t % cycle_time) / cycle_time
        sin_val = (1.0 - math.cos(phase * 2.0 * math.pi)) / 2.0  # 0.0 (down) to 1.0 (curled up)

        # Occasional slight elbow swing on every 4th rep to demonstrate posture correction
        rep_idx = int(t / cycle_time)
        has_swing = (rep_idx % 4 == 3) and (0.3 < phase < 0.7)

        # Baseline body coordinates
        head_c = (320, 120)
        shoulder_l = (280, 180)
        shoulder_r = (360, 180)
        hip_l = (290, 300)
        hip_r = (350, 300)
        knee_l = (290, 390)
        knee_r = (350, 390)
        ankle_l = (290, 450)
        ankle_r = (350, 450)

        # Right arm curl animation
        drift_x = 28 if has_swing else 0
        elbow_r = (365 + drift_x, 255)
        # Wrist swings from extended (365, 335) to curled up (360, 195)
        wrist_r_x = int(365 - sin_val * 15 + drift_x)
        wrist_r_y = int(335 - sin_val * 135)
        wrist_r = (wrist_r_x, wrist_r_y)

        # Left arm rests straight
        elbow_l = (275, 255)
        wrist_l = (275, 335)

        # Draw athlete skeleton & joints
        self._draw_humanoid(frame, head_c, shoulder_l, shoulder_r, elbow_l, elbow_r,
                            wrist_l, wrist_r, hip_l, hip_r, knee_l, knee_r, ankle_l, ankle_r)

        # Draw dumbbell in hand
        cv2.circle(frame, (wrist_r[0] - 12, wrist_r[1]), 8, (120, 140, 160), -1)
        cv2.circle(frame, (wrist_r[0] + 12, wrist_r[1]), 8, (120, 140, 160), -1)
        cv2.line(frame, (wrist_r[0] - 12, wrist_r[1]), (wrist_r[0] + 12, wrist_r[1]), (200, 210, 220), 4)

        # Populate normalized landmarks
        self._set_lm(landmarks, 0, head_c)
        self._set_lm(landmarks, 11, shoulder_l)
        self._set_lm(landmarks, 12, shoulder_r)
        self._set_lm(landmarks, 13, elbow_l)
        self._set_lm(landmarks, 14, elbow_r)
        self._set_lm(landmarks, 15, wrist_l)
        self._set_lm(landmarks, 16, wrist_r)
        self._set_lm(landmarks, 23, hip_l)
        self._set_lm(landmarks, 24, hip_r)
        self._set_lm(landmarks, 25, knee_l)
        self._set_lm(landmarks, 26, knee_r)
        self._set_lm(landmarks, 27, ankle_l)
        self._set_lm(landmarks, 28, ankle_r)

        return frame, landmarks

    def _render_squats(self, frame, landmarks, t):
        """Simulates profile athlete performing squats."""
        cycle_time = 4.0
        phase = (t % cycle_time) / cycle_time
        sin_val = (1.0 - math.cos(phase * 2.0 * math.pi)) / 2.0 # 0.0 (standing) to 1.0 (deep squat)

        # Rep warning check: 3rd rep is shallow
        rep_idx = int(t / cycle_time)
        is_shallow = (rep_idx % 3 == 2)
        depth_multiplier = 0.55 if is_shallow else 1.0

        # Squat descent offsets
        y_drop = int(sin_val * 95 * depth_multiplier)
        hip_back = int(sin_val * 45 * depth_multiplier)
        chest_lean = int(sin_val * 25 * depth_multiplier)

        # Side view coordinates
        ankle = (320, 440)
        knee = (335 - int(sin_val * 15), 350 + int(y_drop * 0.4))
        hip = (280 - hip_back, 260 + y_drop)
        shoulder = (275 - hip_back + chest_lean, 160 + y_drop)
        head = (290 - hip_back + chest_lean, 110 + y_drop)
        elbow = (320 - hip_back, 185 + y_drop)
        wrist = (350 - hip_back, 180 + y_drop)

        # Draw side silhouette
        color_body = (60, 200, 120)
        cv2.circle(frame, head, 22, color_body, -1)
        cv2.line(frame, head, shoulder, color_body, 6)
        cv2.line(frame, shoulder, hip, color_body, 8)
        cv2.line(frame, hip, knee, color_body, 8)
        cv2.line(frame, knee, ankle, color_body, 8)
        cv2.line(frame, shoulder, elbow, color_body, 6)
        cv2.line(frame, elbow, wrist, color_body, 5)

        # Draw joint nodes
        for pt in [shoulder, elbow, wrist, hip, knee, ankle]:
            cv2.circle(frame, pt, 6, (240, 240, 240), -1)
            cv2.circle(frame, pt, 3, (212, 182, 6), -1)

        # Populate landmarks
        self._set_lm(landmarks, 0, head)
        self._set_lm(landmarks, 11, shoulder)
        self._set_lm(landmarks, 12, shoulder)
        self._set_lm(landmarks, 13, elbow)
        self._set_lm(landmarks, 14, elbow)
        self._set_lm(landmarks, 15, wrist)
        self._set_lm(landmarks, 16, wrist)
        self._set_lm(landmarks, 23, hip)
        self._set_lm(landmarks, 24, hip)
        self._set_lm(landmarks, 25, knee)
        self._set_lm(landmarks, 26, knee)
        self._set_lm(landmarks, 27, ankle)
        self._set_lm(landmarks, 28, ankle)

        return frame, landmarks

    def _render_pushups(self, frame, landmarks, t):
        """Simulates horizontal athlete performing push-ups."""
        cycle_time = 3.8
        phase = (t % cycle_time) / cycle_time
        sin_val = (1.0 - math.cos(phase * 2.0 * math.pi)) / 2.0 # 0.0 (top plank) to 1.0 (bottom chest)

        # 3rd rep simulates hip sag
        rep_idx = int(t / cycle_time)
        has_sag = (rep_idx % 3 == 2) and (0.25 < phase < 0.75)
        hip_sag_offset = 32 if has_sag else 0

        # Push-up descent
        chest_drop = int(sin_val * 60)

        wrist = (220, 385)
        elbow = (190, 340 + int(chest_drop * 0.7))
        shoulder = (235, 290 + chest_drop)
        head = (200, 275 + chest_drop)
        hip = (370, 305 + int(chest_drop * 0.8) + hip_sag_offset)
        knee = (470, 335 + int(chest_drop * 0.4))
        ankle = (540, 375)

        # Draw pushup body
        color_body = (16, 185, 129)
        cv2.circle(frame, head, 18, color_body, -1)
        cv2.line(frame, head, shoulder, color_body, 6)
        cv2.line(frame, shoulder, elbow, color_body, 6)
        cv2.line(frame, elbow, wrist, color_body, 6)
        cv2.line(frame, shoulder, hip, color_body, 8)
        cv2.line(frame, hip, knee, color_body, 7)
        cv2.line(frame, knee, ankle, color_body, 7)

        # Joints
        for pt in [shoulder, elbow, wrist, hip, knee, ankle]:
            cv2.circle(frame, pt, 6, (240, 240, 240), -1)
            cv2.circle(frame, pt, 3, (6, 182, 212), -1)

        # Populate landmarks
        self._set_lm(landmarks, 0, head)
        self._set_lm(landmarks, 11, shoulder)
        self._set_lm(landmarks, 12, shoulder)
        self._set_lm(landmarks, 13, elbow)
        self._set_lm(landmarks, 14, elbow)
        self._set_lm(landmarks, 15, wrist)
        self._set_lm(landmarks, 16, wrist)
        self._set_lm(landmarks, 23, hip)
        self._set_lm(landmarks, 24, hip)
        self._set_lm(landmarks, 25, knee)
        self._set_lm(landmarks, 26, knee)
        self._set_lm(landmarks, 27, ankle)
        self._set_lm(landmarks, 28, ankle)

        return frame, landmarks

    def _draw_humanoid(self, frame, head, sl, sr, el, er, wl, wr, hl, hr, kl, kr, al, ar):
        """Draws human athletic stick-figure onto frame."""
        color = (16, 185, 129)
        # Head
        cv2.circle(frame, head, 24, color, -1)
        # Torso
        mid_shoulder = ((sl[0] + sr[0]) // 2, (sl[1] + sr[1]) // 2)
        mid_hip = ((hl[0] + hr[0]) // 2, (hl[1] + hr[1]) // 2)
        cv2.line(frame, head, mid_shoulder, color, 6)
        cv2.line(frame, sl, sr, color, 7)
        cv2.line(frame, mid_shoulder, mid_hip, color, 8)
        cv2.line(frame, hl, hr, color, 7)
        # Arms
        cv2.line(frame, sl, el, color, 6)
        cv2.line(frame, el, wl, color, 5)
        cv2.line(frame, sr, er, color, 6)
        cv2.line(frame, er, wr, color, 5)
        # Legs
        cv2.line(frame, hl, kl, color, 7)
        cv2.line(frame, kl, al, color, 6)
        cv2.line(frame, hr, kr, color, 7)
        cv2.line(frame, kr, ar, color, 6)
        # Keypoint circles
        for pt in [head, sl, sr, el, er, wl, wr, hl, hr, kl, kr, al, ar]:
            cv2.circle(frame, pt, 5, (255, 255, 255), -1)
            cv2.circle(frame, pt, 2, (6, 182, 212), -1)

    def _set_lm(self, landmarks, idx: int, pt: tuple):
        """Converts pixel coordinate (px, py) to normalized [0.0, 1.0] landmark."""
        norm_x = pt[0] / self.WIDTH
        norm_y = pt[1] / self.HEIGHT
        landmarks[idx] = SyntheticLandmark(norm_x, norm_y, 0.0, 0.99)
