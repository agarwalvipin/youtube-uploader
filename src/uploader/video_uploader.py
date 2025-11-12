"""
Video uploader with resumable upload support.

Handles video uploads to YouTube with chunked resumable uploads,
progress tracking, and retry logic.
"""

import logging
import time
from pathlib import Path
from typing import Any, Dict, Optional

from googleapiclient.errors import HttpError, ResumableUploadError
from googleapiclient.http import MediaFileUpload
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from ..config.config_parser import VideoMetadata


class VideoUploader:
    """
    Handles video uploads to YouTube with resumable upload support.

    Implements chunked uploads with progress tracking, automatic retries,
    and error handling.
    """

    # Supported video formats
    SUPPORTED_FORMATS = {
        ".mp4",
        ".avi",
        ".mov",
        ".wmv",
        ".flv",
        ".webm",
        ".mkv",
        ".ts",
        ".mpeg",
        ".mpg",
        ".m4v",
        ".3gp",
    }

    # Maximum file size (256 GB as per YouTube limits)
    MAX_FILE_SIZE = 256 * 1024 * 1024 * 1024

    def __init__(
        self,
        youtube_service,
        chunk_size_mb: int = 10,
        max_retries: int = 5,
        retry_delay: int = 2,
    ):
        """
        Initialize video uploader.

        Args:
            youtube_service: Authenticated YouTube API service object
            chunk_size_mb: Upload chunk size in megabytes
            max_retries: Maximum number of retry attempts
            retry_delay: Base delay in seconds for exponential backoff
        """
        self.youtube = youtube_service
        self.chunk_size = chunk_size_mb * 1024 * 1024  # Convert to bytes
        self.max_retries = max_retries
        self.retry_delay = retry_delay

        self.logger = logging.getLogger("youtube_uploader.video_uploader")

    def validate_video_file(self, video_path: str) -> bool:
        """
        Validate video file before upload.

        Args:
            video_path: Path to video file

        Returns:
            True if valid, False otherwise
        """
        path = Path(video_path)

        # Check if file exists
        if not path.exists():
            self.logger.error(f"Video file not found: {video_path}")
            return False

        # Check if it's a file
        if not path.is_file():
            self.logger.error(f"Path is not a file: {video_path}")
            return False

        # Check file extension
        if path.suffix.lower() not in self.SUPPORTED_FORMATS:
            self.logger.error(
                f"Unsupported video format: {path.suffix}. "
                f"Supported formats: {', '.join(self.SUPPORTED_FORMATS)}"
            )
            return False

        # Check file size
        file_size = path.stat().st_size
        if file_size > self.MAX_FILE_SIZE:
            self.logger.error(
                f"File too large: {file_size / (1024**3):.2f} GB. "
                f"Maximum: {self.MAX_FILE_SIZE / (1024**3):.0f} GB"
            )
            return False

        if file_size == 0:
            self.logger.error(f"File is empty: {video_path}")
            return False

        self.logger.debug(
            f"Video file validated: {video_path} ({file_size / (1024**2):.2f} MB)"
        )
        return True

    def is_valid_video_file(self, video_path: str) -> bool:
        """
        Backwards-compatible alias for validate_video_file.
        Some callers may reference `is_valid_video_file`; route those calls
        to the canonical `validate_video_file` method so `.ts` and other
        formats are recognized consistently.
        """
        return self.validate_video_file(video_path)

    def prepare_upload_request(
        self, video_path: str, metadata: VideoMetadata
    ) -> Dict[str, Any]:
        """
        Prepare video upload request body.

        Args:
            video_path: Path to video file
            metadata: Video metadata

        Returns:
            Request body dictionary
        """
        body = {
            "snippet": {
                "title": metadata.title,
                "description": metadata.description,
                "tags": metadata.tags,
                "categoryId": metadata.category_id,
                "defaultLanguage": metadata.language,
            },
            "status": {
                "privacyStatus": metadata.privacy_status,
                "selfDeclaredMadeForKids": False,
            },
        }

        self.logger.debug(f"Prepared upload request for: {metadata.title}")
        return body

    @retry(
        stop=stop_after_attempt(5),
        wait=wait_exponential(multiplier=2, min=2, max=300),
        retry=retry_if_exception_type(
            (HttpError, ResumableUploadError, ConnectionError)
        ),
        reraise=True,
    )
    def _execute_upload_with_retry(self, request) -> Dict[str, Any]:
        """
        Execute upload request with retry logic.

        Args:
            request: Upload request object

        Returns:
            Response dictionary with video_id
        """
        response = None
        error_count = 0

        while response is None:
            try:
                status, response = request.next_chunk()

                if status:
                    progress = int(status.progress() * 100)
                    self.logger.info(f"Upload progress: {progress}%")

            except HttpError as e:
                if e.resp.status in [500, 502, 503, 504]:
                    # Retryable server errors
                    error_count += 1
                    self.logger.warning(f"Retryable HTTP error {e.resp.status}: {e}")
                    if error_count > self.max_retries:
                        raise
                    time.sleep(self.retry_delay * (2**error_count))
                else:
                    # Non-retryable error
                    self.logger.error(f"Non-retryable HTTP error: {e}")
                    raise

            except ResumableUploadError as e:
                # Handle resumable upload errors
                error_count += 1
                self.logger.warning(f"Resumable upload error: {e}")
                if error_count > self.max_retries:
                    raise
                time.sleep(self.retry_delay * (2**error_count))

        return response

    def upload_video(
        self, video_path: str, metadata: VideoMetadata, progress_callback=None
    ) -> Optional[str]:
        """
        Upload video to YouTube.

        Args:
            video_path: Path to video file
            metadata: Video metadata
            progress_callback: Optional callback for progress updates

        Returns:
            Video ID if successful, None otherwise
        """
        # Validate video file
        if not self.validate_video_file(video_path):
            return None

        try:
            path = Path(video_path)
            file_size = path.stat().st_size

            self.logger.info(
                f"Starting upload: {metadata.title} ({file_size / (1024**2):.2f} MB)"
            )

            # Prepare request body
            body = self.prepare_upload_request(video_path, metadata)

            # Create media upload object with resumable upload
            media = MediaFileUpload(
                video_path,
                chunksize=self.chunk_size,
                resumable=True,
                mimetype="video/*",
            )

            # Create insert request
            request = self.youtube.videos().insert(
                part=",".join(body.keys()), body=body, media_body=media
            )

            # Execute upload with retry logic
            start_time = time.time()
            response = self._execute_upload_with_retry(request)
            upload_duration = time.time() - start_time

            video_id = response.get("id")

            if video_id:
                self.logger.info(
                    f"Upload completed successfully. Video ID: {video_id} "
                    f"(Duration: {upload_duration:.2f}s)"
                )
                return video_id
            else:
                self.logger.error("Upload completed but no video ID received")
                return None

        except HttpError as e:
            self.logger.error(f"HTTP error during upload: {e}", exc_info=True)
            return None

        except Exception as e:
            self.logger.error(f"Upload failed: {e}", exc_info=True)
            return None

    def verify_upload(self, video_id: str) -> bool:
        """
        Verify that a video was uploaded successfully.

        Args:
            video_id: YouTube video ID

        Returns:
            True if video exists and is accessible, False otherwise
        """
        try:
            request = self.youtube.videos().list(part="status,snippet", id=video_id)
            response = request.execute()

            if "items" in response and len(response["items"]) > 0:
                video = response["items"][0]
                status = video["status"]["uploadStatus"]

                self.logger.info(f"Video {video_id} status: {status}")
                return status in ["uploaded", "processed"]
            else:
                self.logger.warning(f"Video {video_id} not found")
                return False

        except HttpError as e:
            self.logger.error(f"Failed to verify upload: {e}")
            return False

    def get_upload_status(self, video_id: str) -> Optional[Dict[str, Any]]:
        """
        Get detailed upload status for a video.

        Args:
            video_id: YouTube video ID

        Returns:
            Dictionary with video status information or None
        """
        try:
            request = self.youtube.videos().list(
                part="status,snippet,processingDetails", id=video_id
            )
            response = request.execute()

            if "items" in response and len(response["items"]) > 0:
                video = response["items"][0]
                return {
                    "video_id": video_id,
                    "title": video["snippet"]["title"],
                    "upload_status": video["status"]["uploadStatus"],
                    "privacy_status": video["status"]["privacyStatus"],
                    "processing_status": video.get("processingDetails", {}).get(
                        "processingStatus"
                    ),
                    "published_at": video["snippet"].get("publishedAt"),
                }

            return None

        except HttpError as e:
            self.logger.error(f"Failed to get upload status: {e}")
            return None
