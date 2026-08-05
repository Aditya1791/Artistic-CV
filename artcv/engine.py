"""
ArtCV Engine - Core Processor interface for Images & Videos
"""
import io
import cv2
import numpy as np
from PIL import Image

from .effects import EFFECT_MAP
from .video_engine import ArtCVVideoEngine
from .enhancer import ArtCVEnhancer
from .inpainting import ArtCVInpainter
from .frames import ArtCVFrameOverlay

class ArtCVEngine:
    def __init__(self):
        self.effects = EFFECT_MAP
        self.video_engine = ArtCVVideoEngine(self)
        self.enhancer = ArtCVEnhancer()
        self.inpainter = ArtCVInpainter()
        self.frame_overlay = ArtCVFrameOverlay()

    def list_effects(self) -> dict:
        """Returns catalog of available effects with parameter metadata."""
        catalog = {}
        for key, info in self.effects.items():
            catalog[key] = {
                "id": key,
                "name": info["name"],
                "category": info["category"],
                "description": info["description"],
                "params": info["params"]
            }
        return catalog

    def process_image(self, input_data, effect_name: str, params: dict = None) -> np.ndarray:
        """Processes an image with specified filter effect."""
        if effect_name not in self.effects:
            raise ValueError(f"Unknown effect '{effect_name}'. Available: {list(self.effects.keys())}")

        img = self._load_image(input_data)

        effect_entry = self.effects[effect_name]
        fn = effect_entry["fn"]
        default_params = effect_entry["params"]
        
        kwargs = {}
        if params:
            for p_key, p_spec in default_params.items():
                if p_key in params:
                    val = params[p_key]
                    try:
                        if p_spec.get("type") == "int":
                            val = int(val)
                        elif p_spec.get("type") == "float":
                            val = float(val)
                    except Exception:
                        val = p_spec.get("default")
                    kwargs[p_key] = val

        try:
            result = fn(img, **kwargs)
        except Exception as err:
            import traceback
            print(f"[ARTCV ENGINE WARNING] Effect '{effect_name}' failed: {err}")
            traceback.print_exc()
            result = self.enhancer.enhance(img, brightness=5, contrast=10, saturation=10)

        if result is None or not isinstance(result, np.ndarray) or result.size == 0:
            result = img

        if len(result.shape) == 2:
            result = cv2.cvtColor(result, cv2.COLOR_GRAY2BGR)
        elif len(result.shape) == 3 and result.shape[2] == 4:
            result = cv2.cvtColor(result, cv2.COLOR_BGRA2BGR)
        elif len(result.shape) == 3 and result.shape[2] == 1:
            result = cv2.cvtColor(result, cv2.COLOR_GRAY2BGR)

        if result.dtype != np.uint8:
            result = np.clip(result, 0, 255).astype(np.uint8)

        return result

    def enhance_image(self, input_data, brightness=0, contrast=0, saturation=0, sharpness=0, warmth=0, gamma=1.0) -> np.ndarray:
        """Applies OpenCV image enhancements."""
        img = self._load_image(input_data)
        return self.enhancer.enhance(
            img,
            brightness=brightness,
            contrast=contrast,
            saturation=saturation,
            sharpness=sharpness,
            warmth=warmth,
            gamma=gamma
        )

    def inpaint_image(self, input_data, mask_data, radius=5, method="seamless", dilation=3) -> np.ndarray:
        """Erases objects using binary mask inpainting."""
        img = self._load_image(input_data)
        mask = self._load_image(mask_data)
        return self.inpainter.erase_object(img, mask, radius=radius, method=method, dilation=dilation)

    def apply_frame(self, input_data, frame_type="polaroid") -> np.ndarray:
        """Applies decorative border frame."""
        img = self._load_image(input_data)
        try:
            return self.frame_overlay.apply_frame(img, frame_type=frame_type)
        except Exception as err:
            import traceback
            print(f"[ARTCV ENGINE WARNING] Frame '{frame_type}' failed: {err}")
            traceback.print_exc()
            return img

    def apply_custom_pattern_frame(self, input_data, pattern_data, item_size=40, gap_spacing=15, padding=60) -> np.ndarray:
        """Creates custom border frame by repeating pattern_data image along the outer border."""
        img = self._load_image(input_data)
        pattern_img = self._load_image(pattern_data)
        try:
            return self.frame_overlay.apply_custom_pattern_frame(
                img, pattern_img, item_size=item_size, gap_spacing=gap_spacing, padding=padding
            )
        except Exception as err:
            import traceback
            print(f"[ARTCV ENGINE WARNING] Pattern frame failed: {err}")
            traceback.print_exc()
            return img

    def resize_image(self, input_data, width: int, height: int, interpolation: str = "lanczos4") -> np.ndarray:
        """Resizes input image to target width and height with specified interpolation method."""
        img = self._load_image(input_data)
        interp_map = {
            "lanczos4": cv2.INTER_LANCZOS4,
            "cubic": cv2.INTER_CUBIC,
            "linear": cv2.INTER_LINEAR,
            "nearest": cv2.INTER_NEAREST
        }
        interp_flag = interp_map.get(interpolation.lower(), cv2.INTER_LANCZOS4)
        return cv2.resize(img, (int(width), int(height)), interpolation=interp_flag)

    def process_to_bytes(self, input_data, effect_name: str, params: dict = None, ext: str = ".jpg") -> bytes:
        """Processes image and returns encoded byte buffer."""
        res_bgr = self.process_image(input_data, effect_name, params)
        if res_bgr is None or not isinstance(res_bgr, np.ndarray) or res_bgr.size == 0:
            raise RuntimeError("Filter processing returned an empty or invalid image array.")

        # Ensure image array is 3-channel uint8 BGR
        if len(res_bgr.shape) == 2:
            res_bgr = cv2.cvtColor(res_bgr, cv2.COLOR_GRAY2BGR)
        elif len(res_bgr.shape) == 3 and res_bgr.shape[2] == 4:
            res_bgr = cv2.cvtColor(res_bgr, cv2.COLOR_BGRA2BGR)
        elif len(res_bgr.shape) == 3 and res_bgr.shape[2] == 1:
            res_bgr = cv2.cvtColor(res_bgr, cv2.COLOR_GRAY2BGR)

        if res_bgr.dtype != np.uint8:
            res_bgr = np.clip(res_bgr, 0, 255).astype(np.uint8)

        success, encoded = cv2.imencode(ext, res_bgr)
        if not success:
            # Fallback PIL encoding
            pil_img = Image.fromarray(cv2.cvtColor(res_bgr, cv2.COLOR_BGR2RGB))
            buf = io.BytesIO()
            pil_img.save(buf, format="JPEG", quality=92)
            return buf.getvalue()

        return encoded.tobytes()

    def process_video(self, input_video_path: str, effect_name: str, params: dict = None, max_frames: int = None, stickers: list = None) -> str:
        """Processes a video file frame-by-frame returning path to stylized MP4 video."""
        return self.video_engine.process_video(input_video_path, effect_name, params, max_frames, stickers=stickers)

    def process_video_sequence(self, clips_spec: list, effect_name: str, params: dict = None, stickers: list = None) -> str:
        """Concatenates multiple video clips in sequence with duration trimming and filter processing."""
        return self.video_engine.process_video_sequence(clips_spec, effect_name, params, stickers=stickers)

    def resize_video(self, input_video_path: str, width: int, height: int, interpolation: str = "lanczos4") -> str:
        """Resizes a video or animated GIF file to specified width and height."""
        return self.video_engine.resize_video(input_video_path, width=width, height=height, interpolation=interpolation)

    def _load_image(self, input_data) -> np.ndarray:
        img = None
        if isinstance(input_data, np.ndarray):
            img = input_data
        elif isinstance(input_data, str):
            img = cv2.imread(input_data, cv2.IMREAD_COLOR)
            if img is None:
                try:
                    pil_img = Image.open(input_data).convert("RGB")
                    img = cv2.cvtColor(np.array(pil_img), cv2.COLOR_RGB2BGR)
                except Exception:
                    pass
        elif isinstance(input_data, (bytes, bytearray)):
            nparr = np.frombuffer(input_data, np.uint8)
            img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
            if img is None:
                try:
                    pil_img = Image.open(io.BytesIO(input_data)).convert("RGB")
                    img = cv2.cvtColor(np.array(pil_img), cv2.COLOR_RGB2BGR)
                except Exception:
                    pass
        elif isinstance(input_data, Image.Image):
            rgb = np.array(input_data.convert("RGB"))
            img = cv2.cvtColor(rgb, cv2.COLOR_RGB2BGR)

        if img is None or not isinstance(img, np.ndarray) or img.size == 0:
            raise ValueError("Failed to load or decode input image.")

        # MANDATORY SANITIZATION: Always ensure img is 3-channel BGR uint8 (H, W, 3)
        if len(img.shape) == 2:
            img = cv2.cvtColor(img, cv2.COLOR_GRAY2BGR)
        elif len(img.shape) == 3 and img.shape[2] == 4:
            img = cv2.cvtColor(img, cv2.COLOR_BGRA2BGR)
        elif len(img.shape) == 3 and img.shape[2] == 1:
            img = cv2.cvtColor(img, cv2.COLOR_GRAY2BGR)

        if img.dtype != np.uint8:
            img = np.clip(img, 0, 255).astype(np.uint8)

        return img

