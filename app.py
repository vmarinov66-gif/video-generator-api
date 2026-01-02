# app.py
"""
Flask API for Video Generator
"""

import os
import uuid
import logging
from datetime import datetime, timedelta
from pathlib import Path
from threading import Lock
from concurrent.futures import ThreadPoolExecutor
from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
from werkzeug.utils import secure_filename
from config import config
from video_generator import VideoGenerator

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Initialize Flask app
app = Flask(__name__)

# Load configuration
env = os.getenv('FLASK_ENV', 'production')
app.config.from_object(config[env])
Config = app.config

# Configure CORS
CORS(app, origins=Config['CORS_ORIGINS'])

# Thread pool for video generation
executor = ThreadPoolExecutor(max_workers=Config['MAX_CONCURRENT_VIDEOS'])

# Job tracking
job_status = {}
job_lock = Lock()


# ======================= Helper Functions =======================

def allowed_file(filename: str, allowed_extensions: set) -> bool:
    """Check if file extension is allowed"""
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in allowed_extensions


def cleanup_old_files():
    """Remove old uploaded and generated files"""
    try:
        now = datetime.utcnow()
        
        # Cleanup uploads
        upload_cutoff = now - timedelta(hours=Config['UPLOAD_RETENTION_HOURS'])
        for upload_dir in Config['UPLOAD_FOLDER'].iterdir():
            if upload_dir.is_dir():
                dir_time = datetime.fromtimestamp(upload_dir.stat().st_mtime)
                if dir_time < upload_cutoff:
                    import shutil
                    shutil.rmtree(upload_dir)
                    logger.info(f"Cleaned up old upload: {upload_dir}")
        
        # Cleanup outputs
        output_cutoff = now - timedelta(hours=Config['OUTPUT_RETENTION_HOURS'])
        for output_file in Config['OUTPUT_FOLDER'].iterdir():
            if output_file.is_file():
                file_time = datetime.fromtimestamp(output_file.stat().st_mtime)
                if file_time < output_cutoff:
                    output_file.unlink()
                    logger.info(f"Cleaned up old output: {output_file}")
                    
    except Exception as e:
        logger.error(f"Error during cleanup: {str(e)}")


# ======================= API Endpoints =======================

@app.route('/api/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({
        'status': 'healthy',
        'timestamp': datetime.utcnow().isoformat(),
        'version': '1.0.0'
    }), 200


@app.route('/api/music/library', methods=['GET'])
def get_music_library():
    """Get list of available music files"""
    try:
        music_files = []
        music_path = Config['MUSIC_LIBRARY_PATH']
        
        if music_path.exists():
            for file in music_path.iterdir():
                if file.is_file() and file.suffix.lower() in ['.mp3', '.wav', '.m4a']:
                    music_files.append({
                        'filename': file.name,
                        'size': file.stat().st_size,
                        'duration': None  # Could add duration detection here
                    })
        
        return jsonify({
            'success': True,
            'music_files': music_files,
            'count': len(music_files)
        }), 200
        
    except Exception as e:
        logger.error(f"Error getting music library: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'Failed to retrieve music library'
        }), 500


@app.route('/api/upload/images', methods=['POST'])
def upload_images():
    """
    Upload images for video generation
    Returns upload_id for tracking
    """
    try:
        # Check if files are present
        if 'images' not in request.files:
            return jsonify({
                'success': False,
                'error': 'No images provided'
            }), 400
        
        files = request.files.getlist('images')
        
        if not files or len(files) == 0:
            return jsonify({
                'success': False,
                'error': 'No images selected'
            }), 400
        
        # Validate file count
        if len(files) > 50:
            return jsonify({
                'success': False,
                'error': 'Maximum 50 images allowed'
            }), 400
        
        # Generate unique upload ID
        upload_id = str(uuid.uuid4())
        upload_dir = Config['UPLOAD_FOLDER'] / upload_id
        upload_dir.mkdir(parents=True, exist_ok=True)
        
        # Save uploaded files
        saved_files = []
        total_size = 0
        
        for file in files:
            if file and allowed_file(file.filename, Config['ALLOWED_IMAGE_EXTENSIONS']):
                filename = secure_filename(file.filename)
                file_path = upload_dir / filename
                file.save(str(file_path))
                
                file_size = file_path.stat().st_size
                total_size += file_size
                
                # Check individual file size
                if file_size > Config['MAX_FILE_SIZE_MB'] * 1024 * 1024:
                    return jsonify({
                        'success': False,
                        'error': f'File {filename} exceeds {Config["MAX_FILE_SIZE_MB"]}MB limit'
                    }), 400
                
                saved_files.append({
                    'filename': filename,
                    'size': file_size
                })
        
        # Check total size
        if total_size > Config['MAX_TOTAL_SIZE_MB'] * 1024 * 1024:
            # Cleanup
            import shutil
            shutil.rmtree(upload_dir)
            return jsonify({
                'success': False,
                'error': f'Total upload size exceeds {Config["MAX_TOTAL_SIZE_MB"]}MB limit'
            }), 400
        
        logger.info(f"Upload complete: {upload_id} - {len(saved_files)} files")
        
        return jsonify({
            'success': True,
            'upload_id': upload_id,
            'files_uploaded': len(saved_files),
            'total_size': total_size,
            'files': saved_files
        }), 200
        
    except Exception as e:
        logger.error(f"Error uploading images: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'Failed to upload images'
        }), 500


@app.route('/api/video/generate', methods=['POST'])
def generate_video():
    """
    Start video generation job
    Returns job_id for status tracking
    """
    try:
        data = request.get_json()
        
        # Validate required fields
        required_fields = ['upload_id', 'text_overlays']
        for field in required_fields:
            if field not in data:
                return jsonify({
                    'success': False,
                    'error': f'Missing required field: {field}'
                }), 400
        
        upload_id = data['upload_id']
        text_overlays = data['text_overlays']
        music_file = data.get('music_file', None)
        duration_per_image = data.get('duration_per_image', 3.0)
        transition_duration = data.get('transition_duration', 0.5)
        output_quality = data.get('output_quality', 'high')
        
        # Validate upload directory exists
        upload_dir = Config['UPLOAD_FOLDER'] / upload_id
        if not upload_dir.exists():
            return jsonify({
                'success': False,
                'error': 'Invalid upload_id or upload expired'
            }), 404
        
        # Validate music file if provided
        if music_file:
            music_path = Config['MUSIC_LIBRARY_PATH'] / music_file
            if not music_path.exists():
                return jsonify({
                    'success': False,
                    'error': 'Invalid music file'
                }), 400
        
        # Create job ID
        job_id = str(uuid.uuid4())
        
        with job_lock:
            job_status[job_id] = {
                'status': 'queued',
                'progress': 0,
                'created_at': datetime.utcnow().isoformat(),
                'video_url': None,
                'error': None
            }
        
        # Submit job to thread pool
        executor.submit(
            process_video_generation,
            job_id,
            str(upload_dir),
            text_overlays,
            music_file,
            duration_per_image,
            transition_duration,
            output_quality
        )
        
        return jsonify({
            'success': True,
            'job_id': job_id,
            'message': 'Video generation started',
            'status_url': f'/api/video/status/{job_id}'
        }), 202
        
    except Exception as e:
        logger.error(f"Error initiating video generation: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'Failed to initiate video generation'
        }), 500


def process_video_generation(
    job_id, 
    upload_dir, 
    text_overlays, 
    music_file, 
    duration_per_image, 
    transition_duration, 
    output_quality
):
    """Background task for video generation"""
    try:
        # Update status to processing
        with job_lock:
            job_status[job_id]['status'] = 'processing'
            job_status[job_id]['progress'] = 10
        
        # Initialize video generator
        generator = VideoGenerator(
            upload_dir=upload_dir,
            output_dir=str(Config['OUTPUT_FOLDER']),
            music_library_path=str(Config['MUSIC_LIBRARY_PATH'])
        )
        
        # Progress callback
        def update_progress(progress):
            with job_lock:
                job_status[job_id]['progress'] = progress
        
        # Generate video
        output_path = generator.generate_video(
            text_overlays=text_overlays,
            music_file=music_file,
            duration_per_image=duration_per_image,
            transition_duration=transition_duration,
            output_quality=output_quality,
            progress_callback=update_progress
        )
        
        # Update status to completed
        with job_lock:
            job_status[job_id]['status'] = 'completed'
            job_status[job_id]['progress'] = 100
            job_status[job_id]['video_url'] = f'/api/video/download/{job_id}'
            job_status[job_id]['output_path'] = output_path
            job_status[job_id]['completed_at'] = datetime.utcnow().isoformat()
        
    except Exception as e:
        logger.error(f"Error processing video {job_id}: {str(e)}")
        with job_lock:
            job_status[job_id]['status'] = 'failed'
            job_status[job_id]['error'] = str(e)


@app.route('/api/video/status/<job_id>', methods=['GET'])
def get_video_status(job_id):
    """Get status of video generation job"""
    with job_lock:
        if job_id not in job_status:
            return jsonify({
                'success': False,
                'error': 'Job not found'
            }), 404
        
        status = job_status[job_id].copy()
    
    return jsonify({
        'success': True,
        'job_id': job_id,
        **status
    }), 200


@app.route('/api/video/download/<job_id>', methods=['GET'])
def download_video(job_id):
    """Download generated video"""
    with job_lock:
        if job_id not in job_status:
            return jsonify({
                'success': False,
                'error': 'Job not found'
            }), 404
        
        status = job_status[job_id]
        
        if status['status'] != 'completed':
            return jsonify({
                'success': False,
                'error': f"Video not ready. Current status: {status['status']}"
            }), 400
        
        output_path = status.get('output_path')
    
    if not output_path or not os.path.exists(output_path):
        return jsonify({
            'success': False,
            'error': 'Video file not found'
        }), 404
    
    return send_file(
        output_path,
        mimetype='video/mp4',
        as_attachment=True,
        download_name=os.path.basename(output_path)
    )


# ======================= Error Handlers =======================

@app.errorhandler(404)
def not_found(error):
    return jsonify({
        'success': False,
        'error': 'Endpoint not found'
    }), 404


@app.errorhandler(500)
def internal_error(error):
    logger.error(f"Internal server error: {str(error)}")
    return jsonify({
        'success': False,
        'error': 'Internal server error'
    }), 500


# ======================= Startup =======================

if __name__ == '__main__':
    # Cleanup old files on startup
    cleanup_old_files()
    
    # Run Flask app
    port = int(os.getenv('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=Config['DEBUG'])