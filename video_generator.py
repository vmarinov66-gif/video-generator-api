# video_generator.py
"""
Core video generation engine using MoviePy
"""

import os
import logging
from typing import List, Dict, Callable, Optional
from moviepy.editor import (
    ImageClip, 
    concatenate_videoclips, 
    CompositeVideoClip,
    AudioFileClip
)
from moviepy.video.fx.fadein import fadein
from moviepy.video.fx.fadeout import fadeout
from PIL import Image, ImageDraw, ImageFont

logger = logging.getLogger(__name__)


class VideoGenerator:
    """
    Main video generation class
    Handles image processing, text overlays, audio, and video assembly
    """
    
    def __init__(self, upload_dir: str, output_dir: str, music_library_path: str):
        """
        Initialize Video Generator
        
        Args:
            upload_dir: Directory containing uploaded images
            output_dir: Directory for output videos
            music_library_path: Path to music library
        """
        self.upload_dir = upload_dir
        self.output_dir = output_dir
        self.music_library_path = music_library_path
        
        self.video_codec = 'libx264'
        self.audio_codec = 'aac'
        
        self.quality_settings = {
            'low': {
                'bitrate': '500k',
                'audio_bitrate': '96k',
                'preset': 'ultrafast'
            },
            'medium': {
                'bitrate': '1500k',
                'audio_bitrate': '128k',
                'preset': 'medium'
            },
            'high': {
                'bitrate': '3000k',
                'audio_bitrate': '192k',
                'preset': 'slow'
            }
        }
    
    def _get_image_files(self) -> List[str]:
        """Get all image files from upload directory"""
        import glob
        image_extensions = ['*.jpg', '*.jpeg', '*.png', '*.gif', '*.bmp']
        image_files = []
        
        for ext in image_extensions:
            image_files.extend(glob.glob(os.path.join(self.upload_dir, ext)))
            image_files.extend(glob.glob(os.path.join(self.upload_dir, ext.upper())))
        
        image_files.sort()
        
        if not image_files:
            raise ValueError("No images found in upload directory")
        
        return image_files
    
    def _resize_image(self, image_path: str, target_size: tuple = (1280, 720)) -> str:
        """
        Resize and optimize image for video
        
        Args:
            image_path: Path to image
            target_size: Target resolution (width, height)
            
        Returns:
            Path to processed image
        """
        try:
            img = Image.open(image_path)
            img = img.convert('RGB')
            
            img_aspect = img.size[0] / img.size[1]
            target_aspect = target_size[0] / target_size[1]
            
            if img_aspect > target_aspect:
                new_width = target_size[0]
                new_height = int(target_size[0] / img_aspect)
            else:
                new_height = target_size[1]
                new_width = int(target_size[1] * img_aspect)
            
            img = img.resize((new_width, new_height), Image.LANCZOS)
            
            background = Image.new('RGB', target_size, (0, 0, 0))
            
            paste_x = (target_size[0] - new_width) // 2
            paste_y = (target_size[1] - new_height) // 2
            background.paste(img, (paste_x, paste_y))
            
            processed_path = image_path.replace('.', '_processed.')
            background.save(processed_path, 'JPEG', quality=95)
            
            return processed_path
            
        except Exception as e:
            logger.error(f"Error processing image {image_path}: {str(e)}")
            raise
    
    def _create_text_overlay(
        self, 
        text: str, 
        position: str = 'center',
        font_size: int = 50,
        color: str = 'white',
        duration: float = 3.0
    ) -> ImageClip:
        """
        Create text overlay using PIL instead of TextClip
        
        Args:
            text: Text to display
            position: Position on screen ('top', 'center', 'bottom')
            font_size: Font size in pixels
            color: Text color
            duration: Duration in seconds
            
        Returns:
            ImageClip object with text
        """
        try:
            import tempfile
            
            # Create transparent image for text
            img_width, img_height = 1280, 720
            img = Image.new('RGBA', (img_width, img_height), (0, 0, 0, 0))
            draw = ImageDraw.Draw(img)
            
            # Try to use DejaVu font, fall back to default
            try:
                font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", font_size)
            except:
                try:
                    font = ImageFont.load_default()
                except:
                    font = None
            
            # Get text size
            if font:
                bbox = draw.textbbox((0, 0), text, font=font)
            else:
                bbox = draw.textbbox((0, 0), text)
            
            text_width = bbox[2] - bbox[0]
            text_height = bbox[3] - bbox[1]
            
            # Calculate position
            position_map = {
                'center': ((img_width - text_width) // 2, (img_height - text_height) // 2),
                'top': ((img_width - text_width) // 2, 50),
                'bottom': ((img_width - text_width) // 2, img_height - text_height - 50)
            }
            
            text_position = position_map.get(position, position_map['center'])
            
            # Color mapping
            color_map = {
                'white': (255, 255, 255),
                'black': (0, 0, 0),
                'red': (255, 0, 0),
                'blue': (0, 0, 255),
                'yellow': (255, 255, 0),
                'green': (0, 255, 0)
            }
            
            text_color = color_map.get(color, (255, 255, 255))
            
            # Draw text with outline/stroke
            stroke_color = (0, 0, 0) if color != 'black' else (255, 255, 255)
            
            if font:
                draw.text(text_position, text, font=font, fill=text_color, stroke_width=2, stroke_fill=stroke_color)
            else:
                draw.text(text_position, text, fill=text_color)
            
            # Save to temp file
            temp_file = tempfile.NamedTemporaryFile(suffix='.png', delete=False)
            img.save(temp_file.name, 'PNG')
            temp_file.close()
            
            # Create ImageClip from the text image
            text_clip = ImageClip(temp_file.name, duration=duration).set_position('center')
            
            return text_clip
            
        except Exception as e:
            logger.error(f"Error creating text overlay: {str(e)}")
            raise
    
    def generate_video(
        self,
        text_overlays: Optional[List[Dict]] = None,
        music_file: Optional[str] = None,
        duration_per_image: float = 3.0,
        transition_duration: float = 0.5,
        output_quality: str = 'high',
        progress_callback: Optional[Callable[[int], None]] = None
    ) -> str:
        """
        Generate video from images with text overlays and music
        
        Args:
            text_overlays: List of text overlay configurations
            music_file: Optional background music filename
            duration_per_image: Duration each image is displayed
            transition_duration: Duration of fade transitions
            output_quality: Video quality preset ('low', 'medium', 'high')
            progress_callback: Optional progress callback function
            
        Returns:
            Path to generated video file
        """
        video_clips = []
        text_overlays = text_overlays or []
        
        try:
            if progress_callback:
                progress_callback(10)
            
            image_files = self._get_image_files()
            logger.info(f"Found {len(image_files)} images to process")
            
            if progress_callback:
                progress_callback(20)
            
            for idx, image_path in enumerate(image_files):
                logger.info(f"Processing image {idx + 1}/{len(image_files)}")
                
                processed_image = self._resize_image(image_path)
                
                img_clip = ImageClip(processed_image, duration=duration_per_image)
                
                if transition_duration > 0:
                    img_clip = fadein(img_clip, transition_duration)
                    img_clip = fadeout(img_clip, transition_duration)
                
                clips_to_composite = [img_clip]
                
                for overlay in text_overlays:
                    if overlay.get('image_index', idx) == idx:
                        text_clip = self._create_text_overlay(
                            text=overlay['text'],
                            position=overlay.get('position', 'center'),
                            font_size=overlay.get('font_size', 50),
                            color=overlay.get('color', 'white'),
                            duration=duration_per_image
                        )
                        clips_to_composite.append(text_clip)
                
                if len(clips_to_composite) > 1:
                    composite_clip = CompositeVideoClip(clips_to_composite)
                    video_clips.append(composite_clip)
                else:
                    video_clips.append(img_clip)
                
                if progress_callback:
                    progress = 20 + int((idx + 1) / len(image_files) * 40)
                    progress_callback(progress)
            
            logger.info("Concatenating video clips")
            final_video = concatenate_videoclips(video_clips, method='compose')
            
            if progress_callback:
                progress_callback(70)
            
            if music_file:
                music_path = os.path.join(self.music_library_path, music_file)
                if os.path.exists(music_path):
                    logger.info(f"Adding background music: {music_file}")
                    audio = AudioFileClip(music_path)
                    
                    if audio.duration < final_video.duration:
                        num_loops = int(final_video.duration / audio.duration) + 1
                        from moviepy.editor import concatenate_audioclips
                        audio = concatenate_audioclips([audio] * num_loops)
                    
                    audio = audio.subclip(0, final_video.duration)
                    final_video = final_video.set_audio(audio)
            
            if progress_callback:
                progress_callback(80)
            
            output_filename = f"video_{os.path.basename(self.upload_dir)}.mp4"
            output_path = os.path.join(self.output_dir, output_filename)
            
            quality = self.quality_settings.get(output_quality, self.quality_settings['high'])
            
            logger.info(f"Writing video to {output_path}")
            final_video.write_videofile(
                output_path,
                fps=30,
                codec=self.video_codec,
                audio_codec=self.audio_codec,
                bitrate=quality['bitrate'],
                audio_bitrate=quality['audio_bitrate'],
                preset=quality['preset'],
                threads=4,
                logger=None
            )
            
            if progress_callback:
                progress_callback(95)
            
            self._cleanup_processed_images()
            
            final_video.close()
            for clip in video_clips:
                clip.close()
            
            if progress_callback:
                progress_callback(100)
            
            logger.info(f"Video generation completed: {output_path}")
            
            file_size = os.path.getsize(output_path) / (1024 * 1024)
            logger.info(f"File size: {file_size:.2f} MB")
            logger.info(f"Duration: {final_video.duration:.2f} seconds")
            
            return output_path
            
        except Exception as e:
            logger.error(f"Error generating video: {str(e)}")
            for clip in video_clips:
                try:
                    clip.close()
                except:
                    pass
            raise
    
    def _cleanup_processed_images(self):
        """Remove temporary processed images"""
        try:
            import glob
            processed_images = glob.glob(os.path.join(self.upload_dir, '*_processed.*'))
            for img in processed_images:
                try:
                    os.remove(img)
                except:
                    pass
        except Exception as e:
            logger.warning(f"Error cleaning up processed images: {str(e)}")
