"""
ArtCV Video & Animation Engine - Multi-Format Video & Animated GIF Stylizer
Supports MP4, GIF, WebM, AVI, MOV, MKV, WMV, OGV, and FLV media files with Multi-Clip Concatenation, Duration Trimming, and Timed Interactive Sticker Overlays.
"""
import os
import tempfile
import cv2
import numpy as np
from PIL import Image, ImageSequence, ImageDraw, ImageFont

class ArtCVVideoEngine:
    def __init__(self, core_engine):
        self.core_engine = core_engine

    def process_video(self, input_media_path: str, effect_name: str, params: dict = None, max_frames: int = None, stickers: list = None) -> str:
        ext = os.path.splitext(input_media_path)[1].lower()

        if ext == ".gif":
            return self._process_gif(input_media_path, effect_name, params, max_frames, stickers)

        return self._process_video_stream(input_media_path, effect_name, params, max_frames, ext, stickers)

    def resize_video(self, input_media_path: str, width: int, height: int, interpolation: str = "lanczos4") -> str:
        """
        Resizes a video or GIF file to target width and height using specified interpolation.
        """
        ext = os.path.splitext(input_media_path)[1].lower()
        target_w = int(width) & ~1
        target_h = int(height) & ~1

        interp_map = {
            "lanczos4": cv2.INTER_LANCZOS4,
            "cubic": cv2.INTER_CUBIC,
            "linear": cv2.INTER_LINEAR,
            "nearest": cv2.INTER_NEAREST
        }
        interp_flag = interp_map.get(interpolation.lower(), cv2.INTER_LANCZOS4)

        if ext == ".gif":
            gif_img = Image.open(input_media_path)
            frames = []
            duration = gif_img.info.get('duration', 100)

            resample_map = {
                "lanczos4": Image.Resampling.LANCZOS,
                "cubic": Image.Resampling.BICUBIC,
                "linear": Image.Resampling.BILINEAR,
                "nearest": Image.Resampling.NEAREST
            }
            resample_flag = resample_map.get(interpolation.lower(), Image.Resampling.LANCZOS)

            for frame in ImageSequence.Iterator(gif_img):
                resized_frame = frame.convert('RGB').resize((target_w, target_h), resample_flag)
                frames.append(resized_frame)

            temp_dir = tempfile.gettempdir()
            output_path = os.path.join(temp_dir, f"artcv_resized_{target_w}x{target_h}_{os.path.basename(input_media_path)}")
            if not output_path.endswith(".gif"):
                output_path += ".gif"

            frames[0].save(output_path, save_all=True, append_images=frames[1:], duration=duration, loop=0)
            return output_path

        cap = cv2.VideoCapture(input_media_path)
        if not cap.isOpened():
            raise ValueError(f"Could not open video file '{input_media_path}'.")

        fps = cap.get(cv2.CAP_PROP_FPS)
        if fps <= 0 or np.isnan(fps):
            fps = 24.0

        temp_dir = tempfile.gettempdir()
        base_name = os.path.splitext(os.path.basename(input_media_path))[0]
        output_path = os.path.join(temp_dir, f"artcv_resized_{target_w}x{target_h}_{base_name}.mp4")

        codec_options = [('avc1', '.mp4'), ('H264', '.mp4'), ('mp4v', '.mp4'), ('MJPG', '.avi')]
        out = None
        for fourcc_str, ext_str in codec_options:
            try:
                fourcc = cv2.VideoWriter_fourcc(*fourcc_str)
                out = cv2.VideoWriter(output_path, fourcc, fps, (target_w, target_h))
                if out.isOpened():
                    break
            except Exception:
                continue

        if out is None or not out.isOpened():
            output_path = os.path.join(temp_dir, f"artcv_resized_{target_w}x{target_h}_{base_name}.avi")
            fourcc = cv2.VideoWriter_fourcc(*'MJPG')
            out = cv2.VideoWriter(output_path, fourcc, fps, (target_w, target_h))

        try:
            while cap.isOpened():
                ret, frame = cap.read()
                if not ret:
                    break
                resized = cv2.resize(frame, (target_w, target_h), interpolation=interp_flag)
                out.write(resized)
        finally:
            cap.release()
            if out is not None:
                out.release()

        return output_path

    def process_video_sequence(self, clips_spec: list, effect_name: str, params: dict = None, stickers: list = None) -> str:
        """
        Concatenates multiple video clips in sequence, trims duration per clip, applies artistic filter, and overlays timed stickers.
        """
        if not clips_spec:
            raise ValueError("No video clips provided for sequence stitching.")

        target_w, target_h, fps = 1280, 720, 24.0
        for item in clips_spec:
            cap = cv2.VideoCapture(item['path'])
            if cap.isOpened():
                target_w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH)) & ~1
                target_h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT)) & ~1
                vid_fps = cap.get(cv2.CAP_PROP_FPS)
                if vid_fps > 0 and not np.isnan(vid_fps):
                    fps = vid_fps
                cap.release()
                break

        temp_dir = tempfile.gettempdir()
        output_filename = f"artcv_stitched_sequence_{effect_name}_{int(cv2.getTickCount())}.mp4"
        output_path = os.path.join(temp_dir, output_filename)

        codec_options = [('avc1', '.mp4'), ('H264', '.mp4'), ('mp4v', '.mp4'), ('MJPG', '.avi')]
        out = None
        for fourcc_str, ext_str in codec_options:
            try:
                fourcc = cv2.VideoWriter_fourcc(*fourcc_str)
                out = cv2.VideoWriter(output_path, fourcc, fps, (target_w, target_h))
                if out.isOpened():
                    break
            except Exception:
                continue

        if out is None or not out.isOpened():
            output_path = os.path.join(temp_dir, f"artcv_stitched_sequence_{effect_name}.avi")
            fourcc = cv2.VideoWriter_fourcc(*'MJPG')
            out = cv2.VideoWriter(output_path, fourcc, fps, (target_w, target_h))

        total_written = 0
        global_time_sec = 0.0

        try:
            for item in clips_spec:
                clip_path = item['path']
                start_sec = float(item.get('start_time', 0.0) or 0.0)
                end_sec = item.get('end_time', None)
                if end_sec is not None:
                    end_sec = float(end_sec)

                cap = cv2.VideoCapture(clip_path)
                if not cap.isOpened():
                    continue

                clip_fps = cap.get(cv2.CAP_PROP_FPS)
                if clip_fps <= 0 or np.isnan(clip_fps):
                    clip_fps = fps

                start_frame = int(start_sec * clip_fps)
                end_frame = int(end_sec * clip_fps) if end_sec is not None else int(cap.get(cv2.CAP_PROP_FRAME_COUNT))

                cap.set(cv2.CAP_PROP_POS_FRAMES, start_frame)
                curr_frame = start_frame

                while cap.isOpened() and curr_frame < end_frame:
                    ret, frame = cap.read()
                    if not ret:
                        break

                    processed = self.core_engine.process_image(frame, effect_name=effect_name, params=params)

                    if processed.shape[1] != target_w or processed.shape[0] != target_h:
                        processed = cv2.resize(processed, (target_w, target_h))

                    # Overlay timed stickers if present
                    if stickers:
                        processed = self._overlay_stickers_on_frame(processed, stickers, global_time_sec)

                    out.write(processed)
                    total_written += 1
                    curr_frame += 1
                    global_time_sec += 1.0 / fps

                cap.release()

        finally:
            if out is not None:
                out.release()

        if total_written == 0:
            raise ValueError("No video frames were rendered during sequence stitching.")

        return output_path

    def _overlay_stickers_on_frame(self, frame_bgr: np.ndarray, stickers: list, time_sec: float) -> np.ndarray:
        """
        Overlays active stickers onto a video BGR frame at given time_sec.
        Supports custom PNG image stamps and text/emoji stamps with position, size, angle, and timing range.
        """
        if not stickers:
            return frame_bgr

        # Convert OpenCV BGR to PIL RGBA for high-quality alpha composite rendering & rotation
        frame_pil = Image.fromarray(cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB)).convert("RGBA")

        for st in stickers:
            start_t = float(st.get("start_time", 0.0) or 0.0)
            end_t = st.get("end_time", None)
            if end_t is not None and end_t != "":
                end_t = float(end_t)

            if time_sec < start_t or (end_t is not None and time_sec > end_t):
                continue

            x = float(st.get("x", frame_bgr.shape[1] / 2))
            y = float(st.get("y", frame_bgr.shape[0] / 2))
            w = max(10, int(float(st.get("width", 80))))
            h = max(10, int(float(st.get("height", 80))))
            rotation_deg = float(st.get("rotation", 0.0)) * 180.0 / np.pi if abs(float(st.get("rotation", 0.0))) <= 6.29 else float(st.get("rotation", 0.0))

            st_type = st.get("type", "emoji")
            st_img_path = st.get("img_path", None)
            st_emoji = st.get("emoji", "🎨")

            stamp_img = None

            if st_type == "custom" and st_img_path and os.path.exists(st_img_path):
                try:
                    stamp_img = Image.open(st_img_path).convert("RGBA")
                    stamp_img = stamp_img.resize((w, h), Image.Resampling.LANCZOS)
                except Exception:
                    stamp_img = None

            if stamp_img is None:
                # Render emoji onto transparent canvas
                stamp_img = Image.new("RGBA", (w, h), (0, 0, 0, 0))
                draw = ImageDraw.Draw(stamp_img)
                try:
                    font_size = int(w * 0.75)
                    font = ImageFont.truetype("seguiemj.ttf", font_size)
                except Exception:
                    try:
                        font = ImageFont.truetype("arial.ttf", font_size)
                    except Exception:
                        font = ImageFont.load_default()

                draw.text((w / 2, h / 2), st_emoji, font=font, anchor="mm", fill=(255, 255, 255, 255))

            # Apply rotation angle
            if abs(rotation_deg) > 0.1:
                stamp_img = stamp_img.rotate(-rotation_deg, expand=True, resample=Image.Resampling.BICUBIC)

            # Paste rotated stamp with alpha channel onto video frame
            paste_x = int(x - stamp_img.width / 2)
            paste_y = int(y - stamp_img.height / 2)

            frame_pil.paste(stamp_img, (paste_x, paste_y), stamp_img)

        # Convert back to OpenCV BGR
        res_bgr = cv2.cvtColor(np.array(frame_pil.convert("RGB")), cv2.COLOR_RGB2BGR)
        return res_bgr

    def _process_gif(self, input_path: str, effect_name: str, params: dict = None, max_frames: int = None, stickers: list = None) -> str:
        gif_img = Image.open(input_path)
        frames = []
        duration = gif_img.info.get('duration', 100)
        fps = 1000.0 / max(1.0, float(duration))

        count = 0
        time_sec = 0.0

        for frame in ImageSequence.Iterator(gif_img):
            frame_rgb = frame.convert('RGB')
            frame_bgr = cv2.cvtColor(np.array(frame_rgb), cv2.COLOR_RGB2BGR)

            styled_bgr = self.core_engine.process_image(frame_bgr, effect_name=effect_name, params=params)

            if stickers:
                styled_bgr = self._overlay_stickers_on_frame(styled_bgr, stickers, time_sec)

            styled_rgb = cv2.cvtColor(styled_bgr, cv2.COLOR_BGR2RGB)
            frames.append(Image.fromarray(styled_rgb))
            
            count += 1
            time_sec += 1.0 / fps
            if max_frames and count >= max_frames:
                break

        if not frames:
            raise ValueError("No frames extracted from GIF file.")

        temp_dir = tempfile.gettempdir()
        output_filename = f"artcv_styled_{effect_name}_{os.path.basename(input_path)}"
        if not output_filename.endswith(".gif"):
            output_filename += ".gif"
        output_path = os.path.join(temp_dir, output_filename)

        frames[0].save(
            output_path,
            save_all=True,
            append_images=frames[1:],
            duration=duration,
            loop=0
        )
        return output_path

    def _process_video_stream(self, input_path: str, effect_name: str, params: dict = None, max_frames: int = None, orig_ext: str = ".mp4", stickers: list = None) -> str:
        cap = cv2.VideoCapture(input_path)
        if not cap.isOpened():
            raise ValueError(f"Could not open video file '{input_path}'.")

        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH)) & ~1
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT)) & ~1
        fps = cap.get(cv2.CAP_PROP_FPS)
        if fps <= 0 or np.isnan(fps):
            fps = 24.0

        temp_dir = tempfile.gettempdir()
        base_name = os.path.splitext(os.path.basename(input_path))[0]
        
        codec_options = [
            ('avc1', '.mp4'),
            ('H264', '.mp4'),
            ('mp4v', '.mp4'),
            ('MJPG', '.avi'),
            ('XVID', '.avi')
        ]

        out = None
        output_path = ""
        
        for fourcc_str, ext_str in codec_options:
            output_path = os.path.join(temp_dir, f"artcv_styled_{effect_name}_{base_name}{ext_str}")
            try:
                fourcc = cv2.VideoWriter_fourcc(*fourcc_str)
                out = cv2.VideoWriter(output_path, fourcc, fps, (width, height))
                if out.isOpened():
                    break
            except Exception:
                continue

        if out is None or not out.isOpened():
            output_path = os.path.join(temp_dir, f"artcv_styled_{effect_name}_{base_name}.avi")
            fourcc = cv2.VideoWriter_fourcc(*'MJPG')
            out = cv2.VideoWriter(output_path, fourcc, fps, (width, height))

        frame_count = 0
        time_sec = 0.0

        try:
            while cap.isOpened():
                ret, frame = cap.read()
                if not ret:
                    break

                processed_frame = self.core_engine.process_image(frame, effect_name=effect_name, params=params)
                if processed_frame.shape[1] != width or processed_frame.shape[0] != height:
                    processed_frame = cv2.resize(processed_frame, (width, height))

                if stickers:
                    processed_frame = self._overlay_stickers_on_frame(processed_frame, stickers, time_sec)

                out.write(processed_frame)
                frame_count += 1
                time_sec += 1.0 / fps

                if max_frames and frame_count >= max_frames:
                    break
        finally:
            cap.release()
            out.release()

        if frame_count == 0:
            raise ValueError("No video frames could be decoded from input video.")

        return output_path
