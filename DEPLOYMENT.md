# 🚀 ArtisticCV Online Hosting & Deployment Guide

This guide provides step-by-step instructions to host **ArtisticCV** online on **Render** with database support, user authentication, and image history.

---

## 📋 Table of Contents
1. [Deploy on Render (Recommended / Free)](#deploy-on-render-recommended--free)
2. [Deploy on Railway or Fly.io](#deploy-on-railway-or-flyio)
3. [Database & Environment Variables Setup](#database--environment-variables-setup)

---

## Deploy on Render (Recommended / Free)

Render allows you to host FastAPI web applications directly from Python code for free with automatic SSL (HTTPS).

### Steps:
1. Push your project code to **GitHub**.
2. Go to [Render.com](https://render.com) and create a free account.
3. Click **New +** -> **Web Service**.
4. Connect your GitHub repository.
5. Configure the service:
   - **Name**: `artistic-cv`
   - **Environment**: `Python 3`
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `uvicorn server:app --host 0.0.0.0 --port $PORT`
6. Add Environment Variables:
   - `JWT_SECRET`: `your-random-secret-key-12345`
   - `DATABASE_URL`: `sqlite:///./artcv.db` (or connect a Render / Google Cloud PostgreSQL Database URL)
7. Click **Create Web Service**. Your web app will be live at `https://artcv.onrender.com`!

---

## Deploy on Railway or Fly.io

### Railway:
1. Log in to [Railway.app](https://railway.app).
2. Click **New Project** -> **Deploy from GitHub repo**.
3. Railway auto-detects `requirements.txt` and `Procfile`.
4. Click **Variables** to add `JWT_SECRET` and `DATABASE_URL`.
5. Click **Generate Domain** to get your public live URL.

---

## Database & Environment Variables Setup

### Environment Variables (.env)
Set these environment variables in your cloud host dashboard:
```env
DATABASE_URL=sqlite:///./artcv.db
JWT_SECRET=your-secret-key-string
GOOGLE_CLIENT_ID=your-google-oauth-client-id
FACEBOOK_APP_ID=your-facebook-app-id
```

### Database Connection:
- **SQLite (Default)**: Zero configuration, uses `./artcv.db`.
- **PostgreSQL / Google Cloud SQL**: Set `DATABASE_URL=postgresql://user:pass@host:5432/dbname`. The backend handles table creation automatically!
