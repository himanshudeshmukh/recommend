# 🚀 Render Deployment Guide for Fashionpedia API

This document explains how to deploy the Fashionpedia FastAPI application to Render.

## Prerequisites

1. **GitHub Account** — Push your code to GitHub first
2. **Render Account** — Sign up at https://render.com (free tier available)

---

## Step 1: Push Code to GitHub

```bash
cd d:\Modules\project\recommendator

git init
git add .
git commit -m "Initial commit: Fashionpedia API"
git branch -M main
git remote add origin https://github.com/<YOUR_USERNAME>/<REPO_NAME>.git
git push -u origin main
```

---

## Step 2: Create a Render Web Service

### Option A: Using Dashboard (Recommended for beginners)

1. Go to https://dashboard.render.com
2. Click **"New +"** → **"Web Service"**
3. Select **"Build and deploy from a Git repository"**
4. Connect your GitHub account and select the `recommendator` repository
5. Fill in these settings:

   | Setting           | Value                                              |
   | ----------------- | -------------------------------------------------- |
   | **Name**          | `fashionpedia-api`                                 |
   | **Environment**   | `Python 3`                                         |
   | **Region**        | `Oregon` (or closest to you)                       |
   | **Branch**        | `main`                                             |
   | **Build Command** | `pip install -r requirements.txt`                  |
   | **Start Command** | `uvicorn app.main:app --host 0.0.0.0 --port $PORT` |
   | **Plan**          | `Free` (or Starter if free tier is full)           |

6. Click **"Create Web Service"**
7. Wait for deployment (2-5 minutes)

### Option B: Using render.yaml (Infrastructure as Code)

The `render.yaml` file is already created in the project. Just:

1. Go to https://dashboard.render.com
2. Click **"New +"** → **"Web Service"**
3. Select the GitHub repository
4. Render will auto-detect `render.yaml` and use those settings

---

## Step 3: Configure Environment Variables (if needed)

In the Render dashboard, go to **Settings** → **Environment** and add:

```
WARM_MODEL_ON_STARTUP=false
MAX_UPLOAD_SIZE_BYTES=15728640
DETECTION_THRESHOLD=0.35
```

**Note:** Keep `WARM_MODEL_ON_STARTUP=false` on free tier to avoid timeout during startup.

---

## Step 4: Access Your Deployed API

Once deployment completes:

- **API Base URL**: `https://<service-name>.onrender.com/api/v1`
- **Health Check**: `GET https://<service-name>.onrender.com/api/v1/health`
- **API Docs**: `https://<service-name>.onrender.com/docs` (Swagger UI)
- **ReDoc**: `https://<service-name>.onrender.com/redoc`

---

## Step 5: Update Flutter Client

In your Flutter app's `main.dart`, change the baseUrl:

```dart
// Before (local):
static const String baseUrl = 'http://localhost:8000/api/v1';

// After (Render):
static const String baseUrl = 'https://<service-name>.onrender.com/api/v1';
```

Or use an environment variable:

```dart
static const String baseUrl = String.fromEnvironment(
  'API_BASE_URL',
  defaultValue: 'https://<service-name>.onrender.com/api/v1',
);
```

---

## Common Issues & Solutions

### ❌ Build fails with "ImportError"

**Cause:** Missing dependencies in `requirements.txt`  
**Fix:** Ensure your `requirements.txt` is complete and all packages are listed.

### ❌ Service crashes immediately after deploy

**Cause:** `WARM_MODEL_ON_STARTUP=true` causes timeout on free tier  
**Fix:** Set `WARM_MODEL_ON_STARTUP=false` in environment variables.

### ❌ Can't connect from Flutter: "Connection refused"

**Cause:** Using `http://localhost:8000` instead of the Render URL  
**Fix:** Update baseUrl to your Render deployment URL.

### ❌ Timeout during image analysis

**Cause:** Free tier has limited resources and model loading is slow  
**Fix:** Expected on first request. Subsequent requests will be faster. Consider upgrading to Starter plan.

### ❌ Model download fails during deployment

**Cause:** Hugging Face Hub rate limits or network issues  
**Fix:** Keep `WARM_MODEL_ON_STARTUP=false` so model loads on first request instead.

---

## Deployment Checklist

- [ ] Code pushed to GitHub
- [ ] Git repo connected to Render
- [ ] `Procfile` exists in root directory
- [ ] `render.yaml` exists (optional but recommended)
- [ ] `runtime.txt` specifies Python version
- [ ] `requirements.txt` is complete and tested locally
- [ ] Environment variables configured (if any)
- [ ] Health check endpoint returns 200 OK
- [ ] Flutter client baseUrl updated to Render URL
- [ ] Test image upload from Flutter
- [ ] Test recommendation endpoint from Flutter

---

## Free Tier Limits (Render)

- **Dyno hours:** 750/month (runs ~24/7)
- **Memory:** 512 MB
- **Spins down:** After 15 min of inactivity (cold start ~30 sec)
- **Bandwidth:** Unlimited
- **No custom domain needed** (unless you want one)

---

## Next Steps

1. **Monitor logs**: Render Dashboard → Logs tab
2. **Test endpoints**: Use Render's /docs page or your Flutter app
3. **Upgrade plan**: If you need 24/7 uptime, upgrade to Starter ($7/month)

---

## Support

- **Render Docs**: https://render.com/docs
- **FastAPI Docs**: https://fastapi.tiangolo.com
- **Common Render Issues**: https://render.com/docs/troubleshooting
