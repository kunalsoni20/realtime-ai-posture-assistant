import cv2
import numpy as np


class HUDOverlay:
    """
    Renders a high-performance, real-time 25+ FPS heads-up display (HUD)
    over OpenCV video frames displaying exercise metrics, reps, stage,
    angle gauge, and live posture correction badges.
    """
    FONT = cv2.FONT_HERSHEY_SIMPLEX

    COLOR_BG = (15, 23, 42)          # Deep Slate
    COLOR_CYAN = (212, 182, 6)       # Neon Cyan (BGR)
    COLOR_EMERALD = (80, 200, 30)    # Neon Emerald (BGR)
    COLOR_WARNING = (35, 45, 235)    # Alert Red/Orange (BGR)
    COLOR_TEXT = (248, 250, 252)     # Clean White
    COLOR_MUTED = (148, 163, 184)    # Slate Muted

    @classmethod
    def render(cls,
               frame: np.ndarray,
               exercise_name: str,
               reps: int,
               stage: str,
               feedback: str,
               angle: float,
               fps: float) -> np.ndarray:
        """
        Draws the telemetry HUD overlay directly onto the frame.
        """
        h, w = frame.shape[:2]

        # 1. Top HUD Bar Background (Semi-transparent dark glass)
        overlay = frame.copy()
        cv2.rectangle(overlay, (0, 0), (w, 85), cls.COLOR_BG, -1)
        cv2.rectangle(overlay, (0, h - 55), (w, h), cls.COLOR_BG, -1)
        cv2.addWeighted(overlay, 0.78, frame, 0.22, 0, frame)

        # 2. Exercise Title & Rep Counter (Top-Left)
        cv2.putText(frame, f"AI GYM COACH | {exercise_name.upper()}", (20, 30),
                    cls.FONT, 0.65, cls.COLOR_CYAN, 2, cv2.LINE_AA)
        
        cv2.putText(frame, f"REPS: {reps}", (20, 68),
                    cls.FONT, 1.0, cls.COLOR_TEXT, 3, cv2.LINE_AA)
        cv2.putText(frame, f"STAGE: {stage.upper() if stage else '--'}", (210, 68),
                    cls.FONT, 0.75, cls.COLOR_MUTED, 2, cv2.LINE_AA)

        # 3. Angle Display (Top-Center / Right)
        angle_text = f"ANGLE: {int(angle)} deg"
        cv2.putText(frame, angle_text, (w - 380, 32),
                    cls.FONT, 0.65, cls.COLOR_TEXT, 2, cv2.LINE_AA)

        # Draw Angle Mini Progress Bar
        bar_x, bar_y, bar_w, bar_h = w - 380, 48, 160, 16
        pct = min(max(angle / 180.0, 0.0), 1.0)
        cv2.rectangle(frame, (bar_x, bar_y), (bar_x + bar_w, bar_y + bar_h), (50, 60, 80), -1)
        cv2.rectangle(frame, (bar_x, bar_y), (bar_x + int(bar_w * pct), bar_y + bar_h), cls.COLOR_CYAN, -1)
        cv2.rectangle(frame, (bar_x, bar_y), (bar_x + bar_w, bar_y + bar_h), cls.COLOR_MUTED, 1)

        # 4. FPS Telemetry (Top-Right)
        fps_color = cls.COLOR_EMERALD if fps >= 24 else cls.COLOR_WARNING
        cv2.putText(frame, f"FPS: {fps:.1f}", (w - 140, 45),
                    cls.FONT, 0.8, fps_color, 2, cv2.LINE_AA)

        # 5. Bottom Feedback Badge (Full Width Footer Status)
        is_warning = "FIX" in feedback.upper() or "SAGGING" in feedback.upper() or "SWING" in feedback.upper()
        badge_bg = cls.COLOR_WARNING if is_warning else cls.COLOR_EMERALD
        
        status_prefix = "ALERT" if is_warning else "STATUS"
        feedback_display = f"[{status_prefix}] {feedback}"

        # Pill box for feedback
        (text_w, text_h), _ = cv2.getTextSize(feedback_display, cls.FONT, 0.7, 2)
        pill_x1 = 20
        pill_y1 = h - 45
        pill_x2 = min(w - 20, pill_x1 + text_w + 30)
        pill_y2 = h - 12

        cv2.rectangle(frame, (pill_x1, pill_y1), (pill_x2, pill_y2), badge_bg, -1)
        cv2.putText(frame, feedback_display, (pill_x1 + 12, pill_y2 - 9),
                    cls.FONT, 0.65, (255, 255, 255), 2, cv2.LINE_AA)

        return frame
