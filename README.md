# Video Generator API

Professional video generation service for ThreadCraft Pro.

## Features

- 🎬 Generate videos from images
- 📝 Add text overlays with customizable positioning
- 🎵 Background music support
- ⚡ Multiple quality presets
- 🎨 Automatic image resizing and optimization
- 📱 Web-optimized MP4 output

## API Endpoints

### Health Check

```
GET /api/health
```

### Upload Images

```
POST /api/upload/images
Content-Type: multipart/form-data

Body: images (multiple files)
```

### Generate Video

```
POST /api/video/generate
Content-Type: application/json

{
  "upload_id": "uuid",
  "text_overlays": [
    {
      "text": "Your text",
      "position": "center",
      "font_size": 50,
      "color": "white",
      "image_index": 0
    }
  ],
  "music_file": "background.mp3",
  "duration_per_image": 3.0,
  "output_quality": "high"
}
```

### Check Status

```
GET /api/video/status/{job_id}
```

### Download Video

```
GET /api/video/download/{job_id}
```

## Environment Variables

```
FLASK_ENV=production
SECRET_KEY=your-secret-key
CORS_ORIGINS=https://threadcraft-pro.vercel.app
MAX_FILE_SIZE_MB=10
MAX_TOTAL_SIZE_MB=100
MAX_CONCURRENT_VIDEOS=3
```

## Deployment

Designed for Railway deployment with automatic Docker build.

## Tech Stack

- Flask 3.0
- MoviePy 1.0
- Python 3.9
- FFmpeg
- Gunicorn

```

**Запази файла**

---

## 🎉 ГОТОВО! Всички файлове са създадени!

Направи screenshot на твоя Explorer и ми го покажи, или просто кажи:
```

✅ Създадох app.py
✅ Създадох Dockerfile
✅ Създадох README.md
✅ Виждам всички 8 файла в Explorer

Готов за GitHub push: ДА
