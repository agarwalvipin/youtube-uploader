"""
YouTube Uploader - Main Orchestrator Script

Coordinates the entire upload workflow including authentication, video scanning,
metadata loading, upload processing, and playlist management.
"""

import json
import logging
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from src.auth.authenticator import Authenticator
from src.config.config_parser import ConfigParser
from src.playlist.playlist_manager import PlaylistManager
from src.uploader.video_uploader import VideoUploader
from src.utils.logger import setup_logger
from src.utils.rate_limiter import RateLimiter


class UploadHistory:
    """Manages upload history to prevent duplicate uploads."""

    def __init__(self, history_file: str):
        """
        Initialize upload history manager.

        Args:
            history_file: Path to upload history JSON file
        """
        self.history_file = Path(history_file)
        self.history = self._load_history()
        self.logger = logging.getLogger("youtube_uploader.history")

    def _load_history(self) -> Dict[str, Any]:
        """Load upload history from file."""
        if self.history_file.exists():
            try:
                with open(self.history_file, "r") as f:
                    return json.load(f)
            except Exception:
                pass

        return {"uploads": [], "last_updated": None}

    def _save_history(self):
        """Save upload history to file."""
        try:
            self.history_file.parent.mkdir(parents=True, exist_ok=True)
            self.history["last_updated"] = datetime.now(timezone.utc).isoformat()

            with open(self.history_file, "w") as f:
                json.dump(self.history, f, indent=2)
        except Exception as e:
            self.logger.error(f"Failed to save upload history: {e}")

    def is_uploaded(self, filename: str) -> bool:
        """Check if a video has already been uploaded."""
        for upload in self.history["uploads"]:
            if (
                upload.get("filename") == filename
                and upload.get("status") == "completed"
            ):
                return True
        return False

    def add_upload(
        self,
        filename: str,
        video_id: str,
        title: str,
        playlist_id: Optional[str] = None,
        status: str = "completed",
    ):
        """Add an upload record to history."""
        record = {
            "filename": filename,
            "video_id": video_id,
            "title": title,
            "uploaded_at": datetime.now(timezone.utc).isoformat(),
            "playlist_id": playlist_id,
            "status": status,
        }

        self.history["uploads"].append(record)
        self._save_history()
        self.logger.info(f"Added upload record for {filename}")

    def get_uploaded_count(self) -> int:
        """Get count of successfully uploaded videos."""
        return sum(1 for u in self.history["uploads"] if u.get("status") == "completed")


class YouTubeUploader:
    """Main orchestrator for YouTube upload workflow."""

    def __init__(self, config_path: str = "./config/config.json"):
        """
        Initialize YouTube uploader.

        Args:
            config_path: Path to main configuration file
        """
        self.logger = None
        self.config_parser = ConfigParser()
        self.config = None
        self.authenticator = None
        self.uploader = None
        self.playlist_manager = None
        self.rate_limiter = None
        self.upload_history = None
        self.config_path = config_path

    def initialize_system(self) -> bool:
        """
        Initialize all system components.

        Returns:
            True if initialization successful, False otherwise
        """
        try:
            # Load configuration
            print("Loading configuration...")
            self.config = self.config_parser.load_config(self.config_path)

            # Setup logging
            self.logger = setup_logger(
                name="youtube_uploader",
                log_level=self.config.logging.level,
                log_dir=self.config.logging.log_directory,
                max_bytes=self.config.logging.max_log_size_mb * 1024 * 1024,
                backup_count=self.config.logging.backup_count,
            )

            self.logger.info("=" * 60)
            self.logger.info("YouTube Uploader v1.0.0")
            self.logger.info("=" * 60)

            # Validate configuration
            if not self.config_parser.validate_config():
                self.logger.error("Configuration validation failed")
                return False

            # Initialize authenticator
            self.logger.info("Initializing authenticator...")
            self.authenticator = Authenticator(
                client_secrets_file=self.config.paths.credentials_file
            )

            # Perform authentication
            self.logger.info("Authenticating with YouTube API...")
            if not self.authenticator.authenticate():
                self.logger.error("Authentication failed")
                return False

            # Get authenticated service
            youtube_service = self.authenticator.get_authenticated_service()
            if not youtube_service:
                self.logger.error("Failed to get YouTube service")
                return False

            # Get user info
            user_info = self.authenticator.get_user_info()
            if user_info:
                self.logger.info(f"Authenticated as: {user_info['title']}")

            # Initialize uploader
            self.logger.info("Initializing video uploader...")
            self.uploader = VideoUploader(
                youtube_service=youtube_service,
                chunk_size_mb=self.config.upload.chunk_size_mb,
                max_retries=self.config.upload.max_retries,
                retry_delay=self.config.upload.retry_delay_seconds,
            )

            # Initialize playlist manager
            self.logger.info("Initializing playlist manager...")
            self.playlist_manager = PlaylistManager(youtube_service)

            # Initialize rate limiter
            self.logger.info("Initializing rate limiter...")
            self.rate_limiter = RateLimiter(
                daily_quota=self.config.api.quota_limit_per_day,
                max_requests_per_minute=self.config.api.max_requests_per_minute,
            )

            # Initialize upload history
            self.upload_history = UploadHistory(self.config.paths.upload_history)

            self.logger.info("System initialization completed successfully")
            return True

        except Exception as e:
            if self.logger:
                self.logger.error(f"System initialization failed: {e}", exc_info=True)
            else:
                print(f"System initialization failed: {e}")
            return False

    def scan_videos(self) -> List[Path]:
        """
        Scan videos directory and return sorted list of video files.

        Returns:
            List of video file paths, sorted alphabetically
        """
        videos_dir = Path(self.config.paths.videos_directory)

        if not videos_dir.exists():
            self.logger.warning(f"Videos directory does not exist: {videos_dir}")
            return []

        # Get all video files
        video_files = []
        for ext in VideoUploader.SUPPORTED_FORMATS:
            video_files.extend(videos_dir.glob(f"*{ext}"))

        # Sort alphabetically
        video_files.sort(key=lambda p: p.name.lower())

        self.logger.info(f"Found {len(video_files)} video files in {videos_dir}")
        for video in video_files:
            self.logger.debug(f"  - {video.name}")

        return video_files

    def process_uploads(self) -> Dict[str, Any]:
        """
        Process all videos for upload.

        Returns:
            Dictionary with upload statistics
        """
        stats = {
            "total": 0,
            "successful": 0,
            "failed": 0,
            "skipped": 0,
            "start_time": datetime.now(),
            "videos": [],
        }

        # Load video metadata
        metadata_file = (
            Path(self.config.paths.videos_directory).parent
            / "config"
            / "videos_metadata.json"
        )
        if not metadata_file.exists():
            metadata_file = Path("./config/videos_metadata.json")

        self.config_parser.load_video_metadata(str(metadata_file))

        # Scan videos
        video_files = self.scan_videos()
        stats["total"] = len(video_files)

        if not video_files:
            self.logger.warning("No videos found to upload")
            return stats

        # Process each video
        for index, video_path in enumerate(video_files, 1):
            filename = video_path.name

            self.logger.info(f"\n[{index}/{len(video_files)}] Processing: {filename}")

            # Check if already uploaded
            if self.upload_history.is_uploaded(filename):
                self.logger.info(f"Video already uploaded, skipping: {filename}")
                stats["skipped"] += 1
                continue

            # Get metadata
            metadata = self.config_parser.get_video_metadata(filename)

            # Check quota before upload
            if not self.rate_limiter.check_quota("video_upload"):
                self.logger.error("Insufficient quota, stopping uploads")
                break

            # Check quota for playlist operations if needed
            if metadata.playlist:
                operations_needed = {"video_upload": 1, "playlist_insert": 1}
                if not self.rate_limiter.can_perform_operations(operations_needed):
                    self.logger.error(
                        "Insufficient quota for upload + playlist, stopping"
                    )
                    break

            # Wait for rate limit
            self.rate_limiter.wait_for_token()

            # Upload video
            self.logger.info(f"Title: {metadata.title}")
            self.logger.info(f"Privacy: {metadata.privacy_status}")
            if metadata.playlist:
                self.logger.info(f"Playlist: {metadata.playlist}")

            video_id = self.uploader.upload_video(
                video_path=str(video_path), metadata=metadata
            )

            if video_id:
                # Consume quota
                self.rate_limiter.consume_quota("video_upload", metadata.title)

                # Handle playlist
                playlist_id = None
                if metadata.playlist:
                    playlist_id = self.playlist_manager.get_or_create_playlist(
                        title=metadata.playlist,
                        description=f"Playlist for {metadata.playlist}",
                        privacy_status=self.config.playlist.default_playlist_privacy,
                        create_if_not_exists=self.config.playlist.create_if_not_exists,
                    )

                    if playlist_id:
                        self.rate_limiter.wait_for_token()

                        if self.playlist_manager.add_video_to_playlist(
                            video_id, playlist_id
                        ):
                            self.rate_limiter.consume_quota(
                                "playlist_insert", metadata.playlist
                            )
                            self.logger.info(f"Added to playlist: {metadata.playlist}")
                        else:
                            self.logger.warning(
                                f"Failed to add video to playlist: {metadata.playlist}"
                            )

                # Record in history
                self.upload_history.add_upload(
                    filename=filename,
                    video_id=video_id,
                    title=metadata.title,
                    playlist_id=playlist_id,
                    status="completed",
                )

                stats["successful"] += 1
                stats["videos"].append(
                    {"filename": filename, "video_id": video_id, "status": "success"}
                )

                self.logger.info(f"✓ Upload completed: {video_id}")
            else:
                stats["failed"] += 1
                stats["videos"].append({"filename": filename, "status": "failed"})
                self.logger.error(f"✗ Upload failed: {filename}")

        stats["end_time"] = datetime.now()
        stats["duration"] = (stats["end_time"] - stats["start_time"]).total_seconds()

        return stats

    def print_summary(self, stats: Dict[str, Any]):
        """Print upload summary."""
        print("\n" + "=" * 60)
        print("UPLOAD SUMMARY")
        print("=" * 60)
        print(f"Total videos:     {stats['total']}")
        print(f"Successful:       {stats['successful']}")
        print(f"Failed:           {stats['failed']}")
        print(f"Skipped:          {stats['skipped']}")
        print(f"Duration:         {stats['duration']:.2f} seconds")

        quota_status = self.rate_limiter.get_quota_status()
        print(
            f"\nQuota used:       {quota_status['used']}/{quota_status['daily_quota']} units"
        )
        print(f"Quota remaining:  {quota_status['remaining']} units")
        print("=" * 60)

        if stats["successful"] == stats["total"] - stats["skipped"]:
            print("✓ All uploads completed successfully!")
        elif stats["successful"] > 0:
            print(
                f"⚠ Partial success: {stats['successful']}/{stats['total'] - stats['skipped']} uploaded"
            )
        else:
            print("✗ No uploads completed successfully")

    def cleanup(self):
        """Cleanup resources."""
        if self.logger:
            self.logger.info("Cleaning up resources...")

        # No explicit cleanup needed for current implementation

        if self.logger:
            self.logger.info("Cleanup completed")

    def run(self) -> int:
        """
        Run the complete upload workflow.

        Returns:
            Exit code (0 for success, 1 for failure)
        """
        try:
            # Initialize system
            if not self.initialize_system():
                print("Failed to initialize system")
                return 1

            # Process uploads
            stats = self.process_uploads()

            # Print summary
            self.print_summary(stats)

            # Cleanup
            self.cleanup()

            return 0 if stats["failed"] == 0 else 1

        except KeyboardInterrupt:
            if self.logger:
                self.logger.warning("Upload interrupted by user")
            print("\nUpload interrupted by user")
            return 1

        except Exception as e:
            if self.logger:
                self.logger.error(f"Unexpected error: {e}", exc_info=True)
            print(f"Unexpected error: {e}")
            return 1


def main():
    """Main entry point."""
    # Get config path from command line if provided
    config_path = sys.argv[1] if len(sys.argv) > 1 else "./config/config.json"

    # Create and run uploader
    uploader = YouTubeUploader(config_path)
    exit_code = uploader.run()

    sys.exit(exit_code)


if __name__ == "__main__":
    main()
