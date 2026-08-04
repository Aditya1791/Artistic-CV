"""
ArtCV Decorative Frames & Custom Image Pattern Border Module
Supports Polaroid, Vintage Film, Cyberpunk Neon, Minimal Slate, Gilded Gold, Comic Vignette, Matrix HUD, Art Deco, and Custom Repeated Image Pattern Borders.
"""
import cv2
import numpy as np

class ArtCVFrameOverlay:
    @staticmethod
    def apply_frame(img: np.ndarray, frame_type: str = "polaroid") -> np.ndarray:
        h, w = img.shape[:2]

        if frame_type == "polaroid":
            top_pad = int(h * 0.08)
            side_pad = int(w * 0.08)
            bottom_pad = int(h * 0.25)
            
            canvas = cv2.copyMakeBorder(
                img, top_pad, bottom_pad, side_pad, side_pad,
                cv2.BORDER_CONSTANT, value=[250, 248, 245]
            )
            cv2.rectangle(canvas, (side_pad, top_pad), (w + side_pad, h + top_pad), (210, 205, 200), 1)
            return canvas

        elif frame_type == "film":
            pad = int(w * 0.12)
            canvas = cv2.copyMakeBorder(
                img, 0, 0, pad, pad,
                cv2.BORDER_CONSTANT, value=[15, 15, 15]
            )
            h_c, w_c = canvas.shape[:2]
            
            hole_w = int(pad * 0.5)
            hole_h = int(pad * 0.4)
            spacing = int(hole_h * 1.8)
            
            for y in range(spacing // 2, h_c, spacing):
                cv2.rectangle(canvas, (pad // 4, y), (pad // 4 + hole_w, y + hole_h), (240, 240, 240), -1)
                cv2.rectangle(canvas, (w_c - pad + pad // 4, y), (w_c - pad + pad // 4 + hole_w, y + hole_h), (240, 240, 240), -1)
                
            return canvas

        elif frame_type == "neon":
            canvas = cv2.copyMakeBorder(
                img, 24, 24, 24, 24,
                cv2.BORDER_CONSTANT, value=[11, 15, 23]
            )
            h_c, w_c = canvas.shape[:2]
            cv2.rectangle(canvas, (6, 6), (w_c - 7, h_c - 7), (254, 242, 0), 2)
            cv2.rectangle(canvas, (16, 16), (w_c - 17, h_c - 17), (200, 8, 255), 2)
            return canvas

        elif frame_type == "minimal":
            pad = int(min(h, w) * 0.05)
            return cv2.copyMakeBorder(
                img, pad, pad, pad, pad,
                cv2.BORDER_CONSTANT, value=[30, 41, 59]
            )

        elif frame_type == "gilded_gold":
            pad = int(min(h, w) * 0.08)
            canvas = cv2.copyMakeBorder(img, pad, pad, pad, pad, cv2.BORDER_CONSTANT, value=[20, 50, 90])
            h_c, w_c = canvas.shape[:2]
            # Bevel edges
            cv2.rectangle(canvas, (4, 4), (w_c - 5, h_c - 5), (50, 150, 220), 4)
            cv2.rectangle(canvas, (pad - 4, pad - 4), (w_c - pad + 3, h_c - pad + 3), (10, 30, 60), 2)
            return canvas

        elif frame_type == "comic_vignette":
            pad = int(min(h, w) * 0.06)
            canvas = cv2.copyMakeBorder(img, pad, pad, pad, pad, cv2.BORDER_CONSTANT, value=[255, 255, 255])
            h_c, w_c = canvas.shape[:2]
            cv2.rectangle(canvas, (pad, pad), (w_c - pad, h_c - pad), (0, 0, 0), 3)
            return canvas

        elif frame_type == "matrix_hud":
            pad = int(min(h, w) * 0.07)
            canvas = cv2.copyMakeBorder(img, pad, pad, pad, pad, cv2.BORDER_CONSTANT, value=[10, 15, 12])
            h_c, w_c = canvas.shape[:2]
            # Corner HUD target brackets
            bracket_len = int(pad * 1.5)
            cv2.polylines(canvas, [np.array([[pad - 10, pad + bracket_len], [pad - 10, pad - 10], [pad + bracket_len, pad - 10]])], False, (0, 255, 120), 3)
            cv2.polylines(canvas, [np.array([[w_c - pad + 10, pad + bracket_len], [w_c - pad + 10, pad - 10], [w_c - pad - bracket_len, pad - 10]])], False, (0, 255, 120), 3)
            cv2.polylines(canvas, [np.array([[pad - 10, h_c - pad - bracket_len], [pad - 10, h_c - pad + 10], [pad + bracket_len, h_c - pad + 10]])], False, (0, 255, 120), 3)
            cv2.polylines(canvas, [np.array([[w_c - pad + 10, h_c - pad - bracket_len], [w_c - pad + 10, h_c - pad + 10], [w_c - pad - bracket_len, h_c - pad + 10]])], False, (0, 255, 120), 3)
            return canvas

        elif frame_type == "art_deco":
            pad = int(min(h, w) * 0.08)
            canvas = cv2.copyMakeBorder(img, pad, pad, pad, pad, cv2.BORDER_CONSTANT, value=[15, 15, 20])
            h_c, w_c = canvas.shape[:2]
            cv2.rectangle(canvas, (8, 8), (w_c - 9, h_c - 9), (0, 215, 255), 2)
            cv2.rectangle(canvas, (16, 16), (w_c - 17, h_c - 17), (0, 215, 255), 1)
            return canvas

        return img

    @staticmethod
    def apply_custom_pattern_frame(
        img: np.ndarray,
        pattern_img: np.ndarray,
        item_size: int = 40,
        gap_spacing: int = 15,
        padding: int = 60
    ) -> np.ndarray:
        """
        Creates a custom border frame by repeating pattern_img around the entire image border
        with customizable item size, gap spacing, and border padding width.
        """
        h, w = img.shape[:2]
        item_size = max(10, int(item_size))
        gap = max(0, int(gap_spacing))
        pad = max(item_size + 10, int(padding))

        # Create outer canvas
        canvas = cv2.copyMakeBorder(
            img, pad, pad, pad, pad,
            cv2.BORDER_CONSTANT, value=[15, 20, 30]
        )
        h_c, w_c = canvas.shape[:2]

        # Prepare pattern stamp image
        pat_resized = cv2.resize(pattern_img, (item_size, item_size), interpolation=cv2.INTER_AREA)
        p_h, p_w = pat_resized.shape[:2]

        # Helper to blend pattern stamp
        def paste_pattern(target_x, target_y):
            if target_x < 0 or target_y < 0 or target_x + p_w > w_c or target_y + p_h > h_c:
                return

            if pat_resized.shape[2] == 4: # BGRA transparent
                alpha = pat_resized[:, :, 3] / 255.0
                for c in range(3):
                    canvas[target_y:target_y+p_h, target_x:target_x+p_w, c] = (
                        alpha * pat_resized[:, :, c] +
                        (1.0 - alpha) * canvas[target_y:target_y+p_h, target_x:target_x+p_w, c]
                    )
            else:
                canvas[target_y:target_y+p_h, target_x:target_x+p_w] = pat_resized[:, :, :3]

        step = item_size + gap
        margin_y = (pad - item_size) // 2

        # 1. Top & Bottom Edges
        for x in range(gap // 2, w_c - item_size, step):
            paste_pattern(x, margin_y)
            paste_pattern(x, h_c - pad + margin_y)

        # 2. Left & Right Edges
        margin_x = (pad - item_size) // 2
        for y in range(gap // 2, h_c - item_size, step):
            paste_pattern(margin_x, y)
            paste_pattern(w_c - pad + margin_x, y)

        # Inner border line
        cv2.rectangle(canvas, (pad - 2, pad - 2), (w_c - pad + 1, h_c - pad + 1), (0, 242, 254), 1)

        return canvas
