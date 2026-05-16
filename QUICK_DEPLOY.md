# Quick Deploy to Render

## 1️⃣ Prepare Your Code Locally

Make sure everything is working on your machine:

```bash
cd d:\Modules\project\recommendator

# Verify requirements.txt is correct
pip install -r requirements.txt

# Test the app locally (should show "Application is ready to accept requests!")
uvicorn app.main:app --reload
```

## 2️⃣ Create a GitHub Repository

If you don't have a GitHub account, create one at https://github.com

### Initialize Git & Push Code:

```bash
cd d:\Modules\project\recommendator

# Initialize git
git init

# Add all files
git add .

# Create initial commit
git commit -m "Initial commit: Fashionpedia API for Render deployment"

# Rename branch to main (GitHub default)
git branch -M main

# Add remote repository (replace <USERNAME> and <REPO_NAME>)
git remote add origin https://github.com/<YOUR_USERNAME>/<YOUR_REPO_NAME>.git

# Push code to GitHub
git push -u origin main
```

**Example:**

```bash
git remote add origin https://github.com/rajat123/fashionpedia-api.git
git push -u origin main
```

## 3️⃣ Deploy to Render

### Quick Deploy (2 minutes):

1. Go to https://render.com and sign up with GitHub
2. Click **Dashboard** → **New +** → **Web Service**
3. Select your GitHub repository
4. Name it `fashionpedia-api`
5. Keep these defaults:
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`
6. Click **Create Web Service**
7. Wait 2-5 minutes for deployment
8. Copy your service URL (e.g., `https://fashionpedia-api.onrender.com`)

## 4️⃣ Update Flutter App

In your Flutter `main.dart`:

```dart
// Change this line from:
static const String baseUrl = 'http://localhost:8000/api/v1';

// To your Render URL:
static const String baseUrl = 'https://fashionpedia-api.onrender.com/api/v1';
```

## 5️⃣ Test Your Deployment

### Option A: Browser

```
https://fashionpedia-api.onrender.com/docs
```

(Opens Swagger UI where you can test all endpoints)

### Option B: Flutter App

- Rebuild and run your Flutter app
- Click **Health** tab → **Check Health**
- Should show ✅ Status: healthy

### Option C: curl

```bash
curl https://fashionpedia-api.onrender.com/api/v1/health
```

---

## ✅ You're Done!

Your API is now live and your Flutter app can connect to it from anywhere in the world! 🎉

**Cost**: Free tier on Render (~$0/month)

---

## Troubleshooting

If deployment fails:

1. **Check logs**: Render Dashboard → Logs
2. **Common issue**: Missing `Procfile` or `requirements.txt`
   - ✅ Both are included in this project
3. **Slow first request**: Normal! Free tier spins down after 15 min
4. **Need help?** See `DEPLOYMENT.md` in this project root
