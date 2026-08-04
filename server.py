"""
FastAPI Server for ArtCV - Rest API & Web Dashboard Host
"""
import os
import sys
import tempfile

# Ensure current directory is in sys.path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import io
import json
import uvicorn
import cv2
from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response, FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from artcv import ArtCVEngine

app = FastAPI(
    title="ArtCV REST API",
    description="High-performance Artistic Image, Video, Inpainting & Enhancement REST API",
    version="2.0.0"
)

# Enable CORS for cross-origin mobile/web app connections
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

engine = ArtCVEngine()

@app.get("/api/effects")
def get_effects():
    """Returns catalog of available artistic filters and parameters for dynamic app UIs."""
    return engine.list_effects()

@app.post("/api/process")
async def process_image(
    file: UploadFile = File(...),
    effect: str = Form("pencil_sketch"),
    params: str = Form("{}")
):
    """Processes uploaded image file with selected artistic effect."""
    try:
        contents = await file.read()
        try:
            param_dict = json.loads(params)
        except Exception:
            param_dict = {}

        output_bytes = engine.process_to_bytes(contents, effect_name=effect, params=param_dict, ext=".jpg")
        return Response(content=output_bytes, media_type="image/jpeg")
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Processing error: {str(e)}")

@app.post("/api/enhance")
async def enhance_image(
    file: UploadFile = File(...),
    brightness: float = Form(0.0),
    contrast: float = Form(0.0),
    saturation: float = Form(0.0),
    sharpness: float = Form(0.0),
    warmth: float = Form(0.0),
    gamma: float = Form(1.0)
):
    """Applies OpenCV image enhancements (Brightness, Contrast, Saturation, Sharpness, Warmth, Gamma)."""
    try:
        contents = await file.read()
        res_bgr = engine.enhance_image(
            contents,
            brightness=brightness,
            contrast=contrast,
            saturation=saturation,
            sharpness=sharpness,
            warmth=warmth,
            gamma=gamma
        )
        _, encoded = cv2.imencode(".jpg", res_bgr)
        return Response(content=encoded.tobytes(), media_type="image/jpeg")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Enhancement error: {str(e)}")

@app.post("/api/inpaint")
async def inpaint_image(
    file: UploadFile = File(...),
    mask: UploadFile = File(...),
    radius: int = Form(5),
    method: str = Form("seamless"),
    dilation: int = Form(3)
):
    """Erases objects using binary mask inpainting."""
    try:
        img_bytes = await file.read()
        mask_bytes = await mask.read()
        res_bgr = engine.inpaint_image(img_bytes, mask_bytes, radius=radius, method=method, dilation=dilation)
        _, encoded = cv2.imencode(".jpg", res_bgr)
        return Response(content=encoded.tobytes(), media_type="image/jpeg")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Inpainting error: {str(e)}")

@app.post("/api/frame")
async def apply_frame(
    file: UploadFile = File(...),
    frame_type: str = Form("polaroid")
):
    """Applies decorative border frame."""
    try:
        contents = await file.read()
        res_bgr = engine.apply_frame(contents, frame_type=frame_type)
        _, encoded = cv2.imencode(".jpg", res_bgr)
        return Response(content=encoded.tobytes(), media_type="image/jpeg")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Frame error: {str(e)}")

@app.post("/api/pattern-frame")
async def apply_pattern_frame(
    file: UploadFile = File(...),
    pattern: UploadFile = File(...),
    item_size: int = Form(40),
    gap_spacing: int = Form(15),
    padding: int = Form(60)
):
    """Applies custom repeated image pattern border frame with customizable gap spacing."""
    try:
        file_bytes = await file.read()
        pattern_bytes = await pattern.read()
        res_bgr = engine.apply_custom_pattern_frame(
            file_bytes, pattern_bytes, item_size=item_size, gap_spacing=gap_spacing, padding=padding
        )
        _, encoded = cv2.imencode(".jpg", res_bgr)
        return Response(content=encoded.tobytes(), media_type="image/jpeg")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Pattern frame error: {str(e)}")

@app.post("/api/resize")
async def resize_image(
    file: UploadFile = File(...),
    width: int = Form(...),
    height: int = Form(...),
    interpolation: str = Form("lanczos4")
):
    """Resizes uploaded image to target width and height."""
    try:
        img_bytes = await file.read()
        res_bgr = engine.resize_image(img_bytes, width=width, height=height, interpolation=interpolation)
        _, encoded = cv2.imencode(".jpg", res_bgr)
        return Response(content=encoded.tobytes(), media_type="image/jpeg")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Resize error: {str(e)}")

@app.post("/api/resize-video")
async def resize_video(
    file: UploadFile = File(...),
    width: int = Form(...),
    height: int = Form(...),
    interpolation: str = Form("lanczos4")
):
    """Resizes uploaded video or animated GIF file to target width and height."""
    try:
        temp_dir = tempfile.gettempdir()
        temp_input_path = os.path.join(temp_dir, f"input_resize_{file.filename}")
        
        with open(temp_input_path, "wb") as f:
            content = await file.read()
            f.write(content)

        output_media_path = engine.resize_video(temp_input_path, width=width, height=height, interpolation=interpolation)
        ext = os.path.splitext(output_media_path)[1].lower()
        media_type = "image/gif" if ext == ".gif" else "video/mp4"

        return FileResponse(output_media_path, media_type=media_type, filename=os.path.basename(output_media_path))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Video resize error: {str(e)}")

@app.post("/api/process-video")
async def process_video(
    file: UploadFile = File(...),
    effect: str = Form("pencil_sketch"),
    params: str = Form("{}"),
    stickers: str = Form("[]")
):
    """Processes uploaded video or animated GIF file frame-by-frame with selected artistic effect and timed stickers."""
    try:
        try:
            param_dict = json.loads(params)
        except Exception:
            param_dict = {}

        try:
            sticker_list = json.loads(stickers)
        except Exception:
            sticker_list = []

        temp_dir = tempfile.gettempdir()
        temp_input_path = os.path.join(temp_dir, f"input_{file.filename}")
        
        with open(temp_input_path, "wb") as f:
            content = await file.read()
            f.write(content)

        output_media_path = engine.process_video(temp_input_path, effect_name=effect, params=param_dict, stickers=sticker_list)
        
        ext = os.path.splitext(output_media_path)[1].lower()
        media_type_map = {
            ".gif": "image/gif",
            ".mp4": "video/mp4",
            ".webm": "video/webm",
            ".avi": "video/x-msvideo",
            ".mov": "video/quicktime",
            ".mkv": "video/x-matroska"
        }
        media_type = media_type_map.get(ext, "video/mp4")
        return FileResponse(output_media_path, media_type=media_type, filename=os.path.basename(output_media_path))

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Video processing error: {str(e)}")

@app.post("/api/process-video-sequence")
async def process_video_sequence(
    files: list[UploadFile] = File(...),
    clips_meta: str = Form("[]"),
    effect: str = Form("pencil_sketch"),
    params: str = Form("{}"),
    stickers: str = Form("[]")
):
    """Concatenates, trims, and stylizes a sequence of video clips with timed stickers."""
    try:
        try:
            param_dict = json.loads(params)
        except Exception:
            param_dict = {}

        try:
            meta_list = json.loads(clips_meta)
        except Exception:
            meta_list = []

        try:
            sticker_list = json.loads(stickers)
        except Exception:
            sticker_list = []

        temp_dir = tempfile.gettempdir()
        clips_spec = []

        for idx, file in enumerate(files):
            temp_path = os.path.join(temp_dir, f"seq_{idx}_{file.filename}")
            content = await file.read()
            with open(temp_path, "wb") as f:
                f.write(content)

            meta = meta_list[idx] if idx < len(meta_list) else {}
            clips_spec.append({
                "path": temp_path,
                "start_time": meta.get("start_time", 0.0),
                "end_time": meta.get("end_time", None)
            })

        output_media_path = engine.process_video_sequence(clips_spec, effect_name=effect, params=param_dict, stickers=sticker_list)
        return FileResponse(output_media_path, media_type="video/mp4", filename=os.path.basename(output_media_path))

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Video sequence error: {str(e)}")

@app.get("/favicon.ico")
async def get_favicon():
    """Serves LOGO.jpg as application favicon."""
    return FileResponse("static/LOGO.jpg", media_type="image/jpeg")

# Mount static web dashboard UI files
app.mount("/", StaticFiles(directory="static", html=True), name="static")

if __name__ == "__main__":
    print("Starting ArtCV FastAPI Server on http://localhost:8000")
    print("API Documentation (Swagger) available at http://localhost:8000/docs")
    uvicorn.run("server:app", host="0.0.0.0", port=8000)
