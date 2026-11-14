"""
This estimates the angle between the tangent at the fibre tip in the reference
frame and in the current frame. It is NOT the integrated curvature, an absolute
3-D pose, or a signed bending angle.

The first time a vlid frame is recieved (reset in window by pressing r) this is treated as the reference angle and then the future angles are calculated
via the change in pos from the baseline ref point and the new point in which the fibre is updated limited by the frame rate
for example: our base ref is 180degrees, each new angle/change in angle will be a +ve or -ve change data is added to the csv generated 
at the end of the run and also plotted in real time as change in the angle 

"""
from collections import deque
import math
import threading
import time

import numpy as np


class BendingAngle:
    def __init__(self, tip_points=10, history_seconds=60.0) -> None:
        if tip_points < 2:
            raise ValueError("tip_points must be at least 2")
        self.tip_points = int(tip_points)
        self.history_seconds = float(history_seconds)
        self._lock = threading.Lock()
        self._reference_direction = None
        self._latest_points = None
        self._start_time = None
        self._times = deque()
        self._angles = deque()
        self._signed_angles = deque()
        self._reference_points = None
        self.latest_angle = float("nan")
        # Signed angle and angular velocity
        self.rotation_axis = np.array([0.0, 0.0, 1.0])
        self.latest_signed_angle = float("nan")
        self.latest_delta_angle = float("nan")
        self.latest_angular_velocity = float("nan")
        self._previous_signed_angle = None
        self._previous_timestamp = None
        

    def _tip_direction(self, points: np.ndarray) -> np.ndarray:
            """Estimate an oriented tangent using a least-squares fit at the tip."""
            xyz = np.asarray(points, dtype=np.float64)
            if xyz.ndim != 2 or xyz.shape[1] != 3 or len(xyz) < self.tip_points:
                raise ValueError("Shape must have at least tip_points rows of XYZ")
            if not np.isfinite(xyz).all():
                raise ValueError("Non-finite shape coordinates")

            segment = xyz[-self.tip_points:]
            distance = np.linalg.norm(np.diff(segment, axis=0), axis=1)
            s = np.concatenate(([0.0], np.cumsum(distance)))
            if s[-1] <= 1e-9:
                raise ValueError("Degenerate tip segment")

            centered_s = s - s.mean()
            denominator = np.dot(centered_s, centered_s)
            direction = (centered_s @ segment) / denominator
            norm = np.linalg.norm(direction)
            if not np.isfinite(norm) or norm <= 1e-12:
                raise ValueError("Cannot determine tip direction")
            return direction / norm

    def record_frame(self, points, timestamp: float | None = None) -> float:
        """Process each valid incoming frame; returns angle in degrees.
        this wilkl assume that the  points are ordered from the fibre base to its tip and that
        orientations are expressed in a consistent 3-D coordinate system.
        """
        direction = self._tip_direction(points)
        now = time.time() if timestamp is None else float(timestamp)
        if not math.isfinite(now):
            raise ValueError("Invalid timestamp")

        with self._lock:
            self._latest_points = np.array(points, copy=True)
            if self._reference_direction is None:
                self._reference_direction = direction.copy()
                self._reference_points = np.array(points, copy=True)
                self._start_time = now
            cosine = float(np.clip(np.dot(self._reference_direction, direction), -1.0, 1.0))
            angle = math.degrees(math.acos(cosine))
            elapsed = max(0.0, now - self._start_time)
            self.latest_angle = angle
            # Calculate signed angle relative to reference
            signed_angle = self._signed_angle(self._reference_direction,direction)
            # Calculate change since the previous frame
            delta_angle = 0.0
            angular_velocity = 0.0

            if np.isfinite(signed_angle):
                if self._previous_signed_angle is not None:
                    # Wrap difference to [-180, 180] to avoid boundary jumps
                    difference = signed_angle - self._previous_signed_angle
                    delta_angle = (difference + 180.0) % 360.0 - 180.0
                    dt = now - self._previous_timestamp
                    if dt > 0:
                        angular_velocity = delta_angle / dt
                    else:
                        angular_velocity = float("nan")
                self._previous_signed_angle = signed_angle
                self._previous_timestamp = now
            else:
                delta_angle = float("nan")
                angular_velocity = float("nan")
                self._previous_signed_angle = None
                self._previous_timestamp = None
            self.latest_signed_angle = signed_angle
            self.latest_delta_angle = delta_angle
            self.latest_angular_velocity = angular_velocity
            self._times.append(elapsed)
            self._angles.append(angle)
            self._signed_angles.append(signed_angle)

            # Keep only a sliding window in memory; save ALL frames to CSV.
            while self._times and elapsed - self._times[0] > self.history_seconds:
                self._times.popleft()
                self._angles.popleft()
                self._signed_angles.popleft()


        return angle
    def get_latest_metrics(self) -> dict[str, bool]:
        """Return a thread-safe snap of the latest measurements."""
        with self._lock:
            return {"signed_angle": self.latest_signed_angle, "delta_angle": self.latest_delta_angle,"angular_velocity": self.latest_angular_velocity,}
    
    def get_visual_snapshot(self) -> dict:
        """Return a consistent snapshot for the GUI."""
        with self._lock:
            return {
                "times": list(self._times),
                "angles": list(self._angles),
                "signed_angles": list(self._signed_angles),
                "latest_angle": self.latest_angle,
                "signed_angle": self.latest_signed_angle,
                "delta_angle": self.latest_delta_angle,
                "angular_velocity": self.latest_angular_velocity,
                "reference_points": (
                    None if self._reference_points is None
                    else self._reference_points.copy()
                ),
                "history_seconds": self.history_seconds
            }
    def reset_reference(self) -> bool:
        """Use the most recently received valid shape as the zero-angle baseline."""
        with self._lock:
            if self._latest_points is None:
                return False
            self._reference_direction = self._tip_direction(self._latest_points)
            self._reference_points = self._latest_points.copy()
            self._start_time = time.time()
            self._times.clear()
            self._angles.clear()
            self._signed_angles.clear()
            self.latest_angle = 0.0
            self.latest_signed_angle = 0.0
            self.latest_delta_angle = 0.0
            self.latest_angular_velocity = 0.0
            self._previous_signed_angle = None
            self._previous_timestamp = None
        return True

    def _signed_angle(self, reference: np.ndarray, current: np.ndarray) -> float:
        """function for the signed angle between directions relative to a fixed rotation axis."""

        axis = self.rotation_axis

        # Project both directions onto the bending plane
        ref = reference - np.dot(reference, axis) * axis
        cur = current - np.dot(current, axis) * axis

        ref_norm = np.linalg.norm(ref)
        cur_norm = np.linalg.norm(cur)

        if ref_norm < 1e-9 or cur_norm < 1e-9:
            return float("nan")

        ref = ref / ref_norm
        cur = cur / cur_norm

        sin_angle = np.dot(axis, np.cross(ref, cur))
        cos_angle = np.clip(np.dot(ref, cur), -1.0, 1.0)

        return float(np.degrees(np.arctan2(sin_angle, cos_angle)))

    def close(self) -> None:
        """No file resources to close; angle is logged by the visualiser."""
        pass
