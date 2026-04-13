"""
Video Processor Module
Applies FFmpeg modifications for copyright protection:
- Horizontal mirror flip
- Speed adjustment
- Crop
- Color adjustments (brightness, contrast, saturation)

IMPORTANT: Speed adjustment SHORTENS the video duration.
  - Speed 1.05x = video becomes ~5% shorter (2:00 → 1:54)
  - This is EXPECTED behavior for copyright protection.
  - The audio is also sped up to match, no content is "cut".
"""

import logging
import subprocess
from pathlib import Path
from typing import Optional

import config

logger = logging.getLogger(__name__)


class VideoProcessor:
    """Processes videos with FFmpeg for copyright protection modifications."""

    def __init__(self, processed_dir: Optional[Path] = None):
        self.processed_dir = processed_dir or config.PROCESSED_DIR
        self.processed_dir.mkdir(parents=True, exist_ok=True)

    def process(self, input_path: Path, video_id: str) -> Optional[Path]:
        """
        Apply all copyright protection modifications to a video.
        
        Args:
            input_path: Path to the input video file
            video_id: Video ID for output filename
            
        Returns:
            Path to processed video file, or None if failed
        """
        output_path = self.processed_dir / f"{video_id}_processed.mp4"

        if not input_path.exists():
            logger.error(f"Input file not found: {input_path}")
            return None

        try:
            # Log original duration
            original_duration = self.get_video_duration(input_path)
            if original_duration:
                logger.info(f"Original duration: {original_duration:.1f}s ({self._format_duration(original_duration)})")

            # Build the FFmpeg filter chain
            filters = self._build_filter_chain()
            
            # Build the FFmpeg command
            cmd = self._build_ffmpeg_command(input_path, output_path, filters)
            
            logger.info(f"Processing video: {input_path.name}")
            logger.debug(f"FFmpeg command: {' '.join(cmd)}")
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=600  # 10 min timeout
            )

            if result.returncode != 0:
                logger.error(f"FFmpeg error: {result.stderr[-500:]}")
                return None

            if output_path.exists():
                # Log processed duration
                processed_duration = self.get_video_duration(output_path)
                if processed_duration and original_duration:
                    diff = original_duration - processed_duration
                    logger.info(
                        f"Processed duration: {processed_duration:.1f}s ({self._format_duration(processed_duration)}) "
                        f"[Original: {original_duration:.1f}s, Diff: {diff:.1f}s]"
                    )
                    if config.FFMPEG_SPEED > 1.0:
                        expected = original_duration / config.FFMPEG_SPEED
                        logger.info(
                            f"Speed adjustment: {config.FFMPEG_SPEED}x → "
                            f"Expected: {expected:.1f}s, Got: {processed_duration:.1f}s"
                        )
                logger.info(f"Processed video saved: {output_path}")
                return output_path
            else:
                logger.error("Processed file not created")
                return None

        except subprocess.TimeoutExpired:
            logger.error("FFmpeg processing timed out")
            return None
        except Exception as e:
            logger.error(f"Error processing video: {e}")
            return None

    def _format_duration(self, seconds: float) -> str:
        """Format seconds to MM:SS."""
        m = int(seconds) // 60
        s = int(seconds) % 60
        return f"{m}:{s:02d}"

    def _build_filter_chain(self) -> str:
        """
        Build the FFmpeg filter chain based on config settings.
        
        Returns:
            FFmpeg filter string
        """
        filters = []

        # 1. Horizontal mirror flip
        if config.FFMPEG_MIRROR:
            filters.append("hflip")
            logger.debug("Added: horizontal mirror flip")

        # 2. Crop (percentage-based)
        if config.FFMPEG_CROP_PERCENT > 0:
            crop_pct = config.FFMPEG_CROP_PERCENT
            scale = (100 - 2 * crop_pct) / 100
            filters.append(
                f"crop=iw*{scale}:ih*{scale},pad=iw:ih:(ow-iw)/2:(oh-ih)/2:black"
            )
            logger.debug(f"Added: crop {crop_pct}% from each side")

        # 3. Speed adjustment
        # NOTE: Speed > 1.0 SHORTENS the video. This is normal.
        # 1.05x speed = video is ~5% shorter but ALL content is preserved.
        if config.FFMPEG_SPEED != 1.0:
            speed = config.FFMPEG_SPEED
            video_speed = f"setpts={1/speed}*PTS"
            filters.append(video_speed)
            logger.debug(f"Added: speed x{speed} (video will be {1/speed:.2f}x original length)")

        # 4. Color adjustments
        color_filters = []
        if config.FFMPEG_BRIGHTNESS != 0:
            color_filters.append(f"eq=brightness={config.FFMPEG_BRIGHTNESS}")
        if config.FFMPEG_CONTRAST != 1.0:
            color_filters.append(f"eq=contrast={config.FFMPEG_CONTRAST}")
        if config.FFMPEG_SATURATION != 1.0:
            color_filters.append(f"eq=saturation={config.FFMPEG_SATURATION}")

        if color_filters:
            filters.append(",".join(color_filters))
            logger.debug("Added: color adjustments")

        # Combine all video filters
        video_filter = ",".join(filters)

        # Add audio speed if needed
        if config.FFMPEG_SPEED != 1.0:
            audio_speed = self._build_atempo_filter(config.FFMPEG_SPEED)
            full_filter = f"[0:v]{video_filter}[v];[0:a]{audio_speed}[a]"
        else:
            full_filter = video_filter

        return full_filter

    def _build_atempo_filter(self, speed: float) -> str:
        """
        Build atempo filter chain for audio speed adjustment.
        atempo only supports 0.5-2.0, so we chain for values outside.
        """
        if 0.5 <= speed <= 2.0:
            return f"atempo={speed}"

        # Chain multiple atempo filters
        filters = []
        remaining = speed
        while remaining > 2.0:
            filters.append("atempo=2.0")
            remaining /= 2.0
        while remaining < 0.5:
            filters.append("atempo=0.5")
            remaining /= 0.5
        filters.append(f"atempo={remaining}")
        return ",".join(filters)

    def _build_ffmpeg_command(
        self, input_path: Path, output_path: Path, filters: str
    ) -> list:
        """
        Build the complete FFmpeg command.
        
        Args:
            input_path: Input video path
            output_path: Output video path
            filters: FFmpeg filter string
            
        Returns:
            Command as list of strings
        """
        cmd = ["ffmpeg", "-y", "-i", str(input_path)]

        # Check if we have separate audio processing
        if "[v]" in filters and "[a]" in filters:
            # Complex filter with separate audio
            cmd.extend(["-filter_complex", filters, "-map", "[v]", "-map", "[a]"])
        else:
            # Simple video filter, handle audio separately
            if config.FFMPEG_SPEED != 1.0:
                audio_speed = self._build_atempo_filter(config.FFMPEG_SPEED)
                cmd.extend(["-vf", filters, "-af", audio_speed])
            else:
                cmd.extend(["-vf", filters])

        # Output settings - maintain quality
        cmd.extend([
            "-c:v", "libx264",
            "-preset", "medium",
            "-crf", "18",  # High quality
            "-c:a", "aac",
            "-b:a", "192k",
            "-movflags", "+faststart",
            "-pix_fmt", "yuv420p",
            str(output_path)
        ])

        return cmd

    def get_video_duration(self, video_path: Path) -> Optional[float]:
        """Get video duration in seconds using ffprobe."""
        try:
            cmd = [
                "ffprobe", "-v", "error",
                "-show_entries", "format=duration",
                "-of", "default=noprint_wrappers=1:nokey=1",
                str(video_path)
            ]
            result = subprocess.run(cmd, capture_output=True, text=True)
            if result.returncode == 0:
                return float(result.stdout.strip())
        except Exception as e:
            logger.error(f"Error getting duration: {e}")
        return None

    def cleanup(self, video_id: str):
        """Remove processed file after upload."""
        path = self.processed_dir / f"{video_id}_processed.mp4"
        if path.exists():
            path.unlink()
            logger.info(f"Cleaned up processed: {path}")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    processor = VideoProcessor()
