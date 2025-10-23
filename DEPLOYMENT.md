# Specify Production Deployment Guide

This guide covers deploying the Specify system to production using Vercel (frontend) and Railway (backend).

## Overview

- **Frontend**: Next.js app deployed to Vercel
- **Backend**: FastAPI server deployed to Railway
- **Architecture**: Client-side frontend communicates with RESTful API backend

## Prerequisites

1. **Vercel Account**: Sign up at [vercel.com](https://vercel.com)
2. **Railway Account**: Sign up at [railway.app](https://railway.app)
3. **Anthropic API Key**: Get from [console.anthropic.com](https://console.anthropic.com)
4. **Git Repository**: Fork or clone this repository

## Backend Deployment (Railway)

### 1. Prepare Backend for Railway

The backend is already configured for Railway with:
- `/railway.json` - Railway deployment configuration
- `/Procfile` - Web process definition
- `/runtime.txt` - Python version specification
- `.env.production.example` - Environment variables template

### 2. Deploy to Railway

1. **Connect Repository**:
   ```bash
   # Install Railway CLI
   npm install -g @railway/cli

   # Login to Railway
   railway login

   # Create new project
   railway init

   # Deploy from root directory
   railway up
   ```

2. **Set Environment Variables**:
   Go to your Railway project dashboard and set these variables:

   **Required**:
   ```
   SPECIFY_ANTHROPIC_API_KEY=your_anthropic_api_key_here
   SPECIFY_CORS_ORIGINS=https://your-frontend-domain.vercel.app
   ```

   **Recommended**:
   ```
   SPECIFY_ENVIRONMENT=production
   SPECIFY_DEBUG=false
   SPECIFY_LOG_LEVEL=INFO
   SPECIFY_ALLOWED_HOSTS=your-backend-domain.railway.app
   ```

3. **Get Backend URL**:
   After deployment, Railway will provide a URL like:
   `https://your-backend-domain.railway.app`

### 3. Verify Backend Deployment

Test your backend at:
- Health check: `https://your-backend-domain.railway.app/api/health`
- API docs: `https://your-backend-domain.railway.app/api/docs`

## Frontend Deployment (Vercel)

### 1. Prepare Frontend for Vercel

The frontend is configured for Vercel with:
- `/frontend/vercel.json` - Vercel deployment configuration
- `/frontend/.env.example` - Environment variables template

### 2. Deploy to Vercel

1. **Connect Repository**:
   - Go to [vercel.com/dashboard](https://vercel.com/dashboard)
   - Click "New Project"
   - Import your Git repository
   - Set root directory to `frontend/`

2. **Set Environment Variables**:
   In Vercel project settings, add these environment variables:

   **Required**:
   ```
   NEXT_PUBLIC_API_URL=https://your-backend-domain.railway.app
   NEXT_PUBLIC_WS_URL=wss://your-backend-domain.railway.app
   ```

3. **Deploy**:
   - Vercel will automatically build and deploy
   - Get your frontend URL: `https://your-frontend-domain.vercel.app`

### 3. Update Backend CORS

Update your Railway backend environment variable:
```
SPECIFY_CORS_ORIGINS=https://your-frontend-domain.vercel.app
```

## Local Development Setup

### Backend Setup

1. **Navigate to project root**:
   ```bash
   cd /path/to/Specify
   ```

2. **Create virtual environment**:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

4. **Create environment file**:
   ```bash
   cp .env.example .env
   # Edit .env and add your SPECIFY_ANTHROPIC_API_KEY
   ```

5. **Run backend**:
   ```bash
   uvicorn api.main:app --reload --host 0.0.0.0 --port 8000
   ```

### Frontend Setup

1. **Navigate to frontend directory**:
   ```bash
   cd frontend
   ```

2. **Install dependencies**:
   ```bash
   npm install
   ```

3. **Create environment file**:
   ```bash
   cp .env.example .env.local
   # Defaults should work for local development
   ```

4. **Run frontend**:
   ```bash
   npm run dev
   ```

5. **Access application**:
   - Frontend: http://localhost:3000
   - Backend API: http://localhost:8000/api/docs

## Environment Variables Reference

### Backend Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `SPECIFY_ANTHROPIC_API_KEY` | ✅ | - | Anthropic API key for AI processing |
| `SPECIFY_CORS_ORIGINS` | ✅ | localhost URLs | Comma-separated allowed origins |
| `SPECIFY_ENVIRONMENT` | ❌ | development | Environment mode (development/production) |
| `SPECIFY_DEBUG` | ❌ | false | Enable debug mode |
| `SPECIFY_HOST` | ❌ | 0.0.0.0 | Server host |
| `SPECIFY_PORT` | ❌ | 8000 | Server port |
| `SPECIFY_ALLOWED_HOSTS` | ❌ | - | Comma-separated allowed hosts |
| `SPECIFY_LOG_LEVEL` | ❌ | INFO | Logging level |

### Frontend Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `NEXT_PUBLIC_API_URL` | ✅ | http://localhost:8000 | Backend API URL |
| `NEXT_PUBLIC_WS_URL` | ✅ | ws://localhost:8000 | Backend WebSocket URL |

## Production Checklist

### Before Deployment

- [ ] Set up Anthropic API key
- [ ] Configure repository on Vercel and Railway
- [ ] Set all required environment variables
- [ ] Test locally with production-like setup

### After Deployment

- [ ] Verify backend health check endpoint works
- [ ] Test API documentation is accessible
- [ ] Verify frontend loads and can connect to backend
- [ ] Test end-to-end workflow (analyze → specify → refine)
- [ ] Check logs for any errors
- [ ] Test CORS configuration with real domains

### Security Considerations

- [ ] Ensure `.env` files are in `.gitignore`
- [ ] Use HTTPS for all production URLs
- [ ] Set `SPECIFY_ALLOWED_HOSTS` in production
- [ ] Limit `SPECIFY_CORS_ORIGINS` to your domains only
- [ ] Keep API keys secure and rotate regularly

## Troubleshooting

### Common Issues

1. **CORS Errors**:
   - Ensure `SPECIFY_CORS_ORIGINS` includes your frontend domain
   - Check for trailing slashes in URLs
   - Verify environment variables are set correctly

2. **Backend Won't Start**:
   - Check `SPECIFY_ANTHROPIC_API_KEY` is set
   - Verify Python version is 3.12
   - Check Railway logs for error details

3. **Frontend Can't Connect**:
   - Verify `NEXT_PUBLIC_API_URL` points to your Railway backend
   - Check backend health endpoint is accessible
   - Ensure backend is running and healthy

4. **Build Failures**:
   - Frontend: Check Node.js version compatibility
   - Backend: Verify all dependencies in `requirements.txt`

### Getting Help

- Check Railway deployment logs
- Check Vercel deployment logs
- Verify environment variables are set correctly
- Test API endpoints directly
- Check network connectivity between services

## Scaling Considerations

- **Backend**: Railway auto-scales based on traffic
- **Frontend**: Vercel Edge Network provides global distribution
- **Database**: Consider adding PostgreSQL for persistent storage
- **Caching**: Consider Redis for session management
- **Monitoring**: Set up logging and monitoring services

## Cost Optimization

- **Railway**: Offers free tier with usage limits
- **Vercel**: Free tier includes generous allowances
- **API Costs**: Monitor Anthropic API usage
- **Optimization**: Implement caching and request optimization