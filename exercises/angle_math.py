import numpy as np


def calculate_angle(a, b, c) -> float:
    """
    Computes the interior 2D geometric joint angle (in degrees) formed by
    three coordinates (a, b, c), where 'b' is the vertex joint landmark.
    
    Mathematical Formulation:
        theta = |arctan2(c_y - b_y, c_x - b_x) - arctan2(a_y - b_y, a_x - b_x)|
        angle = |theta * 180 / pi|
        if angle > 180:
            angle = 360 - angle
            
    Parameters:
        a: Array-like [x, y] of first joint landmark
        b: Array-like [x, y] of vertex joint landmark
        c: Array-like [x, y] of third joint landmark

    Returns:
        float: Computed angle in degrees, constrained to [0.0, 180.0].
    """
    a = np.array(a, dtype=np.float64)
    b = np.array(b, dtype=np.float64)
    c = np.array(c, dtype=np.float64)

    radians = np.arctan2(c[1] - b[1], c[0] - b[0]) - np.arctan2(a[1] - b[1], a[0] - b[0])
    angle = np.abs(radians * 180.0 / np.pi)

    if angle > 180.0:
        angle = 360.0 - angle

    return float(angle)
