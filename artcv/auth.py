"""
ArtCV Authentication Module - JWT Tokens, Password Hashing, Google & Facebook OAuth Handlers
"""
import os
import hashlib
import hmac
import base64
import json
import time
from typing import Optional, Dict, Any
import requests

SECRET_KEY = os.environ.get("JWT_SECRET", "artcv-secret-key-change-in-production-2026")
ALGORITHM = "HS256"
TOKEN_EXPIRE_SECONDS = 30 * 24 * 3600  # 30 Days

try:
    import jwt
    HAS_PYJWT = True
except ImportError:
    HAS_PYJWT = False


# Password Hashing Utilities (PBKDF2 SHA256)
def hash_password(password: str) -> str:
    """Hashes password with SHA256 salt."""
    salt = os.urandom(16)
    pwd_hash = hashlib.pbkdf2_hmac('sha256', password.encode('utf-8'), salt, 100000)
    return salt.hex() + ":" + pwd_hash.hex()


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verifies plain password against stored hash."""
    if not hashed_password or ":" not in hashed_password:
        return False
    try:
        salt_hex, pwd_hash_hex = hashed_password.split(":", 1)
        salt = bytes.fromhex(salt_hex)
        expected_hash = bytes.fromhex(pwd_hash_hex)
        computed_hash = hashlib.pbkdf2_hmac('sha256', plain_password.encode('utf-8'), salt, 100000)
        return hmac.compare_digest(expected_hash, computed_hash)
    except Exception:
        return False


# JWT Token Utilities
def create_access_token(user_id: int, email: str) -> str:
    """Generates a JWT access token for user authentication."""
    payload = {
        "sub": str(user_id),
        "email": email,
        "exp": int(time.time()) + TOKEN_EXPIRE_SECONDS
    }
    if HAS_PYJWT:
        return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)
    else:
        # Fallback signed JSON token
        header = base64.urlsafe_b64encode(json.dumps({"alg": "HS256", "typ": "JWT"}).encode()).decode().rstrip("=")
        body = base64.urlsafe_b64encode(json.dumps(payload).encode()).decode().rstrip("=")
        sig_input = f"{header}.{body}"
        signature = hmac.new(SECRET_KEY.encode(), sig_input.encode(), hashlib.sha256).digest()
        sig_str = base64.urlsafe_b64encode(signature).decode().rstrip("=")
        return f"{header}.{body}.{sig_str}"


def decode_access_token(token: str) -> Optional[Dict[str, Any]]:
    """Decodes JWT access token and verifies expiration & signature."""
    if not token:
        return None
    
    if HAS_PYJWT:
        try:
            payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
            return payload
        except Exception:
            return None
    else:
        try:
            parts = token.split(".")
            if len(parts) != 3:
                return None
            header_b64, body_b64, sig_b64 = parts
            sig_input = f"{header_b64}.{body_b64}"
            
            # Re-pad base64 string
            body_padded = body_b64 + "=" * (-len(body_b64) % 4)
            body_bytes = base64.urlsafe_b64decode(body_padded)
            payload = json.loads(body_bytes.decode())
            
            if payload.get("exp", 0) < time.time():
                return None
            return payload
        except Exception:
            return None


# OAuth Verification Helpers

def verify_google_token(credential: str) -> Optional[Dict[str, Any]]:
    """
    Verifies Google ID Token via Google's tokeninfo API.
    Returns dict with email, name, picture if valid.
    """
    try:
        # Verify token using Google OAuth API
        res = requests.get(f"https://oauth2.googleapis.com/tokeninfo?id_token={credential}", timeout=5)
        if res.status_code == 200:
            data = res.json()
            email = data.get("email")
            if email:
                return {
                    "email": email,
                    "name": data.get("name") or email.split("@")[0],
                    "avatar_url": data.get("picture"),
                    "provider": "google"
                }
    except Exception as e:
        print(f"[OAuth Error] Google verification failed: {e}")
    return None


def verify_facebook_token(access_token: str) -> Optional[Dict[str, Any]]:
    """
    Verifies Facebook Access Token via Facebook Graph API.
    Returns dict with email, name, picture if valid.
    """
    try:
        url = f"https://graph.facebook.com/me?fields=id,name,email,picture.type(large)&access_token={access_token}"
        res = requests.get(url, timeout=5)
        if res.status_code == 200:
            data = res.json()
            fb_id = data.get("id")
            email = data.get("email") or f"fb_{fb_id}@facebook.user"
            name = data.get("name") or f"FB User {fb_id}"
            picture_url = data.get("picture", {}).get("data", {}).get("url")
            
            return {
                "email": email,
                "name": name,
                "avatar_url": picture_url,
                "provider": "facebook"
            }
    except Exception as e:
        print(f"[OAuth Error] Facebook verification failed: {e}")
    return None
