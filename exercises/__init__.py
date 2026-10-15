"""
Exercise detection modules for Real-Time AI Workout & Posture Correction Assistant.
"""
from .base import BaseExercise
from .angle_math import calculate_angle
from .bicep_curl import BicepCurlDetector
from .squat import SquatDetector
from .pushup import PushupDetector

__all__ = [
    "BaseExercise",
    "calculate_angle",
    "BicepCurlDetector",
    "SquatDetector",
    "PushupDetector",
]
