"""
ArtCV Pro Enhancer Engine - OpenCV Image Adjustments & Color Grading
Adjusts Brightness, Contrast, Saturation, Sharpness, Temperature, Warmth, Vignette, and Gamma.
"""
import cv2
import numpy as np

class ArtCVEnhancer:
    @staticmethod
    def enhance(
        img: np.ndarray,
        brightness: float = 0.0,    # -100 to 100
        contrast: float = 0.0,      # -100 to 100
        saturation: float = 0.0,    # -100 to 100
        sharpness: float = 0.0,     # 0 to 100
        warmth: float = 0.0,        # -100 to 100
        gamma: float = 1.0          # 0.2 to 3.0
    ) -> np.ndarray:
        res = img.astype(np.float32)

        # 1. Brightness & Contrast adjustment
        if contrast != 0.0:
            alpha = (contrast + 100.0) / 100.0 if contrast >= 0 else (contrast + 100.0) / 100.0
            res = (res - 128.0) * alpha + 128.0

        if brightness != 0.0:
            res = res + (brightness * 1.5)

        res = np.clip(res, 0, 255)

        # 2. Saturation (HSV space)
        if saturation != 0.0:
            hsv = cv2.cvtColor(res.astype(np.uint8), cv2.COLOR_BGR2HSV).astype(np.float32)
            sat_scale = (saturation + 100.0) / 100.0
            hsv[:, :, 1] = np.clip(hsv[:, :, 1] * sat_scale, 0, 255)
            res = cv2.cvtColor(hsv.astype(np.uint8), cv2.COLOR_HSV2BGR).astype(np.float32)

        # 3. Warmth / Temperature
        if warmth != 0.0:
            b_shift = -warmth * 0.5
            r_shift = warmth * 0.5
            res[:, :, 0] = np.clip(res[:, :, 0] + b_shift, 0, 255)
            res[:, :, 2] = np.clip(res[:, :, 2] + r_shift, 0, 255)

        # 4. Gamma Correction
        if gamma != 1.0 and gamma > 0:
            inv_gamma = 1.0 / float(gamma)
            res = np.clip(((res / 255.0) ** inv_gamma) * 255.0, 0, 255)

        # 5. Sharpness (Unsharp Masking)
        if sharpness > 0:
            sharpen_factor = (sharpness / 100.0) * 1.5
            blurred = cv2.GaussianBlur(res, (0, 0), 3)
            res = cv2.addWeighted(res, 1.0 + sharpen_factor, blurred, -sharpen_factor, 0)

        return np.clip(res, 0, 255).astype(np.uint8)
