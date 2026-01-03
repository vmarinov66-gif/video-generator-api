FROM python:3.9-slim

# Install system dependencies including ImageMagick
RUN apt-get update && apt-get install -y \
    ffmpeg \
    imagemagick \
    libsm6 \
    libxext6 \
    libxrender-dev \
    libmagickwand-dev \
    && rm -rf /var/lib/apt/lists/*

# Configure ImageMagick policy to allow text operations
RUN sed -i 's/rights="none" pattern="PDF"/rights="read|write" pattern="PDF"/' /etc/ImageMagick-6/policy.xml || true

# Set ImageMagick binary path for MoviePy
ENV IMAGEMAGICK_BINARY=/usr/bin/convert

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

RUN mkdir -p uploads outputs music_library

EXPOSE 5000

CMD ["gunicorn", "--bind", "0.0.0.0:5000", "--workers", "2", "--timeout", "300", "app:app"]