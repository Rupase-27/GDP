# This code uses a background-subtraction approach to isolate the guidewire and catheter in a backlit phantom image. 
# It assumes that the guidewire and catheter are darker than the background. 
# The code uses morphological operations to separate the guidewire from the catheter, and then finds the distal tips of both.
# The code is designed to be used in a real-time video processing pipeline, where the background is captured first, and then each subsequent frame is processed to detect the guidewire and catheter.
#
#
# The background imahe is first captured with no guidewire or catheter present. 
# The background is then subtracted from each subsequent frame to isolate the guidewire and catheter.
# The code uses morphological operations to separate the guidewire from the catheter, and then finds the distal tips of both, from the colour, with the catheter being darker than the guidewire
# the thickness of the structures are separated by morphological opening with a larger kernel for the catheter and a smaller kernel for the guidewire.
# An estimate of the distal tip of each device is found
#
######################################################################################################################################################################################################################

import cv2
import numpy as np

#initialise the class with the parameters for background subtraction and morphological operations
class GuidewireCatheterTracker:
    def __init__(self, diff_thresh=35, catheter_kernel_size=9, entry_side="left"):
        self.bg_gray = None
        # intensity threshold for detecting new darker objects (larger values = less sensitive)
        self.diff_thresh = diff_thresh
        # entry side of the catheter/guidewire in the image. Can be "left", "right", "top", or "bottom"
        self.entry_side = entry_side
        # Controls thickness of catheter mask. Larger values = thicker mask, smaller values = thinner mask
        self.cath_kernel = cv2.getStructuringElement(
            cv2.MORPH_ELLIPSE, (catheter_kernel_size, catheter_kernel_size)
        )
        # Cleans noise from both masks
        self.clean_kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3))

    # Converts the first image into a grayscale reference
    def capture_background(self, frame):
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        self.bg_gray = cv2.GaussianBlur(gray, (5, 5), 0)

    # Process a new frame to detect the guidewire and catheter, returning an annotated image and the distal tip coordinates
    def process(self, frame):
        if self.bg_gray is None:
            self.capture_background(frame)
            return frame, {"gw_tip": None, "cath_tip": None}

        # Convert the current frame to grayscale and apply Gaussian blur
        gray = cv2.GaussianBlur(cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY), (5, 5), 0)

        # Isolate dark catheter + guidewire against backlit phantom
        diff = cv2.subtract(self.bg_gray, gray)
        _, combined_mask = cv2.threshold(diff, self.diff_thresh, 255, cv2.THRESH_BINARY)
        combined_mask = cv2.morphologyEx(combined_mask, cv2.MORPH_OPEN, self.clean_kernel)

        # Extract catheter and dilate (making it slightly larger)
        catheter_mask = cv2.morphologyEx(combined_mask, cv2.MORPH_OPEN, self.cath_kernel)
        catheter_dilated = cv2.dilate(catheter_mask, self.clean_kernel, iterations=2)

        # Extract guidewire 
        guidewire_mask = cv2.subtract(combined_mask, catheter_dilated)
        guidewire_mask = cv2.morphologyEx(guidewire_mask, cv2.MORPH_OPEN, self.clean_kernel)

    # Find the distal tips (endpoint furthest from the insertion side) 
        cath_tip = self._find_distal_tip(catheter_mask)
        gw_tip = self._find_distal_tip(guidewire_mask)

        # Visualisation: overlay the masks on the original frame and mark the distal tips
        overlay = frame.copy()
        overlay[catheter_mask > 0] = (255, 140, 0)   # Blue: Catheter
        overlay[guidewire_mask > 0] = (0, 255, 100)  # Green: Guidewire
        annotated = cv2.addWeighted(frame, 0.65, overlay, 0.35, 0)

        # Draw Tip markers and labels
        if cath_tip:
            cv2.circle(annotated, cath_tip, 6, (255, 140, 0), -1)
            cv2.putText(annotated, f"CATH {cath_tip}", (cath_tip[0] + 8, cath_tip[1]),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 140, 0), 2)
        if gw_tip:
            cv2.circle(annotated, gw_tip, 6, (0, 255, 100), -1)
            cv2.putText(annotated, f"GW {gw_tip}", (gw_tip[0] + 8, gw_tip[1]),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 100), 2)

        return annotated, {"gw_tip": gw_tip, "cath_tip": cath_tip}

    def _find_distal_tip(self, mask):
        ys, xs = np.where(mask > 0)
        if len(xs) < 15:
            return None
        if self.entry_side == "left":
            idx = np.argmax(xs)
        elif self.entry_side == "right":
            idx = np.argmin(xs)
        elif self.entry_side == "bottom":
            idx = np.argmin(ys)
        else:
            idx = np.argmax(ys)
        return (int(xs[idx]), int(ys[idx]))
