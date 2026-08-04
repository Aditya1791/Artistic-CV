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
import uuid
import uvicorn
import cv2
from typing import Optional
from fastapi import FastAPI, UploadFile, File, Form, HTTPException, Depends, Header, Body
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response, FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy.orm import Session

from artcv import ArtCVEngine
from artcv.database import (
    init_db, get_db, create_user, get_user_by_email, get_user_by_id,
    save_gallery_item, get_user_gallery, delete_gallery_item, get_gallery_item_by_id
)
from artcv.auth import (
    hash_password, verify_password, create_access_token, decode_access_token,
    verify_google_token, verify_facebook_token
)

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

UPLOAD_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "uploads", "gallery"))

@app.on_event("startup")
def on_startup():
    """Initializes database tables and upload storage directories."""
    init_db()
    os.makedirs(UPLOAD_DIR, exist_ok=True)

# Helper Dependency for Authenticated Requests
def get_current_user(authorization: Optional[str] = Header(None), db: Session = Depends(get_db)):
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Authentication required")
    token = authorization.split(" ", 1)[1]
    payload = decode_access_token(token)
    if not payload:
        raise HTTPException(status_code=401, detail="Invalid or expired session token")
    user_id = int(payload.get("sub", 0))
    user = get_user_by_id(db, user_id)
    if not user:
        raise HTTPException(status_code=401, detail="User not found")
    return user

# Helper Dependency for Optional Auth
def get_optional_user(authorization: Optional[str] = Header(None), db: Session = Depends(get_db)):
    if not authorization or not authorization.startswith("Bearer "):
        return None
    token = authorization.split(" ", 1)[1]
    payload = decode_access_token(token)
    if not payload:
        return None
    user_id = int(payload.get("sub", 0))
    return get_user_by_id(db, user_id)


# --- AUTHENTICATION ENDPOINTS ---

@app.post("/api/auth/signup")
def signup(data: dict = Body(...), db: Session = Depends(get_db)):
    """Registers a new user with Email, Name & Password."""
    email = data.get("email", "").strip()
    password = data.get("password", "")
    name = data.get("name", "").strip() or email.split("@")[0]

    if not email or "@" not in email:
        raise HTTPException(status_code=400, detail="Valid email address is required")
    if not password or len(password) < 6:
        raise HTTPException(status_code=400, detail="Password must be at least 6 characters")

    existing = get_user_by_email(db, email)
    if existing:
        raise HTTPException(status_code=400, detail="An account with this email already exists")

    pwd_hash = hash_password(password)
    user = create_user(db, email=email, name=name, password_hash=pwd_hash, provider="email")
    token = create_access_token(user.id, user.email)
    return {"token": token, "user": user.to_dict()}


@app.post("/api/auth/login")
def login(data: dict = Body(...), db: Session = Depends(get_db)):
    """Authenticates existing user with Email & Password."""
    email = data.get("email", "").strip()
    password = data.get("password", "")

    if not email or not password:
        raise HTTPException(status_code=400, detail="Email and password are required")

    user = get_user_by_email(db, email)
    if not user or not user.password_hash or not verify_password(password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid email or password")

    token = create_access_token(user.id, user.email)
    return {"token": token, "user": user.to_dict()}


@app.post("/api/auth/google")
def google_auth(data: dict = Body(...), db: Session = Depends(get_db)):
    """Authenticates or signs up user via Google OAuth ID token or simulated OAuth payload."""
    credential = data.get("credential") or data.get("token")
    user_info = None

    if credential:
        user_info = verify_google_token(credential)
    
    # Fallback to direct client payload if verifying directly
    if not user_info and data.get("email"):
        user_info = {
            "email": data.get("email"),
            "name": data.get("name") or "Google User",
            "avatar_url": data.get("picture") or data.get("avatar_url"),
            "provider": "google"
        }

    if not user_info:
        raise HTTPException(status_code=400, detail="Invalid Google OAuth token or credentials")

    email = user_info["email"]
    user = get_user_by_email(db, email)

    if not user:
        user = create_user(
            db,
            email=email,
            name=user_info.get("name", "Google User"),
            avatar_url=user_info.get("avatar_url"),
            provider="google"
        )

    token = create_access_token(user.id, user.email)
    return {"token": token, "user": user.to_dict()}


@app.post("/api/auth/facebook")
def facebook_auth(data: dict = Body(...), db: Session = Depends(get_db)):
    """Authenticates or signs up user via Facebook Access Token or simulated OAuth payload."""
    access_token = data.get("accessToken") or data.get("token")
    user_info = None

    if access_token:
        user_info = verify_facebook_token(access_token)

    # Fallback to direct client payload if verifying directly
    if not user_info and (data.get("email") or data.get("facebook_id")):
        fb_id = data.get("facebook_id", "user")
        user_info = {
            "email": data.get("email") or f"fb_{fb_id}@facebook.user",
            "name": data.get("name") or f"Facebook User {fb_id}",
            "avatar_url": data.get("avatar_url"),
            "provider": "facebook"
        }

    if not user_info:
        raise HTTPException(status_code=400, detail="Invalid Facebook OAuth token or credentials")

    email = user_info["email"]
    user = get_user_by_email(db, email)

    if not user:
        user = create_user(
            db,
            email=email,
            name=user_info.get("name", "Facebook User"),
            avatar_url=user_info.get("avatar_url"),
            provider="facebook"
        )

    token = create_access_token(user.id, user.email)
    return {"token": token, "user": user.to_dict()}


@app.get("/api/auth/me")
def get_me(user = Depends(get_current_user)):
    """Returns current authenticated user profile."""
    return {"user": user.to_dict()}


# --- DATABASE GALLERY ENDPOINTS ---

@app.get("/api/gallery")
def get_gallery(user = Depends(get_current_user), db: Session = Depends(get_db)):
    """Retrieves all edited images and videos saved in the database for the authenticated user."""
    items = get_user_gallery(db, user.id)
    return [item.to_dict() for item in items]


@app.post("/api/gallery/save")
async def save_to_gallery(
    file: UploadFile = File(...),
    title: str = Form("Edited Art"),
    effect: str = Form("filter"),
    params: str = Form("{}"),
    media_type: str = Form("image"),
    user = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Saves processed media file and records metadata into the user's database gallery."""
    try:
        os.makedirs(UPLOAD_DIR, exist_ok=True)
        ext = os.path.splitext(file.filename)[1] or (".mp4" if media_type == "video" else ".jpg")
        filename = f"{uuid.uuid4().hex}{ext}"
        saved_file_path = os.path.join(UPLOAD_DIR, filename)

        content = await file.read()
        with open(saved_file_path, "wb") as f:
            f.write(content)

        gallery_item = save_gallery_item(
            db,
            user_id=user.id,
            title=title,
            effect_name=effect,
            file_path=saved_file_path,
            params=params,
            media_type=media_type
        )
        return gallery_item.to_dict()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to save gallery item: {str(e)}")


@app.get("/api/gallery/file/{filename}")
def serve_gallery_file(filename: str):
    """Serves media file stored in user gallery."""
    file_path = os.path.join(UPLOAD_DIR, filename)
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="File not found")
    
    ext = os.path.splitext(filename)[1].lower()
    media_type = "video/mp4" if ext == ".mp4" else "image/gif" if ext == ".gif" else "image/jpeg"
    return FileResponse(file_path, media_type=media_type)


@app.delete("/api/gallery/{item_id}")
def delete_gallery_entry(item_id: str, user = Depends(get_current_user), db: Session = Depends(get_db)):
    """Deletes an edited image or video record from user gallery database and storage."""
    success = delete_gallery_item(db, item_id=item_id, user_id=user.id)
    if not success:
        raise HTTPException(status_code=404, detail="Item not found or permission denied")
    return {"message": "Gallery item deleted successfully"}


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
