"""
Configuration parser with Pydantic validation.

Handles loading and validating JSON configuration files for the YouTube uploader.
"""

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator


class VideoMetadata(BaseModel):
    """Video metadata model with validation."""

    model_config = ConfigDict(extra="forbid")

    filename: str = Field(..., description="Video filename")
    title: str = Field(..., min_length=1, max_length=100, description="Video title")
    description: str = Field(
        default="", max_length=5000, description="Video description"
    )
    tags: List[str] = Field(default_factory=list, description="Video tags")
    category_id: str = Field(default="22", description="YouTube category ID")
    privacy_status: str = Field(default="private", description="Privacy status")
    playlist: Optional[str] = Field(default=None, description="Playlist title")
    language: str = Field(default="en", description="Video language ISO code")

    @field_validator("privacy_status")
    @classmethod
    def validate_privacy(cls, v: str) -> str:
        """Validate privacy status."""
        allowed = ["private", "public", "unlisted"]
        if v.lower() not in allowed:
            raise ValueError(f"Privacy status must be one of {allowed}")
        return v.lower()

    @field_validator("tags")
    @classmethod
    def validate_tags(cls, v: List[str]) -> List[str]:
        """Validate tags total length."""
        total_length = sum(len(tag) for tag in v)
        if total_length > 500:
            raise ValueError("Total tags length cannot exceed 500 characters")
        return v


class PathConfig(BaseModel):
    """Path configuration model."""

    model_config = ConfigDict(extra="forbid")

    videos_directory: str = Field(
        default="./videos", description="Videos directory path"
    )
    credentials_file: str = Field(
        default="./config/client_secrets.json", description="OAuth credentials file"
    )
    upload_history: str = Field(
        default="./data/upload_history.json", description="Upload history file"
    )


class UploadConfig(BaseModel):
    """Upload configuration model."""

    model_config = ConfigDict(extra="forbid")

    default_privacy: str = Field(
        default="private", description="Default privacy status"
    )
    chunk_size_mb: int = Field(
        default=10, ge=1, le=100, description="Upload chunk size in MB"
    )
    max_retries: int = Field(
        default=5, ge=1, le=10, description="Maximum retry attempts"
    )
    retry_delay_seconds: int = Field(
        default=2, ge=1, le=60, description="Base retry delay"
    )
    concurrent_uploads: int = Field(
        default=1, ge=1, le=5, description="Concurrent uploads"
    )

    @field_validator("default_privacy")
    @classmethod
    def validate_privacy(cls, v: str) -> str:
        """Validate privacy status."""
        allowed = ["private", "public", "unlisted"]
        if v.lower() not in allowed:
            raise ValueError(f"Privacy status must be one of {allowed}")
        return v.lower()


class PlaylistConfig(BaseModel):
    """Playlist configuration model."""

    model_config = ConfigDict(extra="forbid")

    create_if_not_exists: bool = Field(
        default=True, description="Create playlist if doesn't exist"
    )
    default_playlist_privacy: str = Field(
        default="private", description="Default playlist privacy"
    )

    @field_validator("default_playlist_privacy")
    @classmethod
    def validate_privacy(cls, v: str) -> str:
        """Validate privacy status."""
        allowed = ["private", "public", "unlisted"]
        if v.lower() not in allowed:
            raise ValueError(f"Privacy status must be one of {allowed}")
        return v.lower()


class APIConfig(BaseModel):
    """API configuration model."""

    model_config = ConfigDict(extra="forbid")

    quota_limit_per_day: int = Field(
        default=10000, ge=1, description="Daily quota limit"
    )
    max_requests_per_minute: int = Field(
        default=60, ge=1, le=100, description="Max requests per minute"
    )


class LoggingConfig(BaseModel):
    """Logging configuration model."""

    model_config = ConfigDict(extra="forbid")

    level: str = Field(default="INFO", description="Logging level")
    log_directory: str = Field(default="./logs", description="Log directory path")
    max_log_size_mb: int = Field(
        default=50, ge=1, le=1000, description="Max log file size in MB"
    )
    backup_count: int = Field(
        default=5, ge=1, le=100, description="Number of backup logs"
    )

    @field_validator("level")
    @classmethod
    def validate_level(cls, v: str) -> str:
        """Validate logging level."""
        allowed = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        if v.upper() not in allowed:
            raise ValueError(f"Log level must be one of {allowed}")
        return v.upper()


class AppConfig(BaseModel):
    """Main application configuration model."""

    model_config = ConfigDict(extra="allow")

    paths: PathConfig = Field(default_factory=PathConfig)
    upload: UploadConfig = Field(default_factory=UploadConfig)
    playlist: PlaylistConfig = Field(default_factory=PlaylistConfig)
    api: APIConfig = Field(default_factory=APIConfig)
    logging: LoggingConfig = Field(default_factory=LoggingConfig)


class DefaultMetadata(BaseModel):
    """Default metadata model."""

    model_config = ConfigDict(extra="forbid")

    category_id: str = Field(default="22")
    privacy_status: str = Field(default="private")
    tags: List[str] = Field(default_factory=list)
    language: str = Field(default="en")
    playlist: Optional[str] = Field(default=None)


class FallbackConfig(BaseModel):
    """Fallback configuration for missing metadata."""

    model_config = ConfigDict(extra="forbid")

    title_template: str = Field(default="{filename}")
    description_template: str = Field(default="Uploaded on {date}")
    use_filename_as_title: bool = Field(default=True)


class VideoMetadataConfig(BaseModel):
    """Video metadata configuration container."""

    model_config = ConfigDict(extra="forbid")

    default_metadata: DefaultMetadata = Field(default_factory=DefaultMetadata)
    videos: List[VideoMetadata] = Field(default_factory=list)
    fallback: FallbackConfig = Field(default_factory=FallbackConfig)


class ConfigParser:
    """
    Configuration parser and validator.

    Loads and validates JSON configuration files using Pydantic models.
    """

    def __init__(self):
        """Initialize configuration parser."""
        self.logger = logging.getLogger("youtube_uploader.config_parser")
        self.app_config: Optional[AppConfig] = None
        self.video_metadata_config: Optional[VideoMetadataConfig] = None

    def load_config(self, config_path: str) -> AppConfig:
        """
        Load main application configuration.

        Args:
            config_path: Path to config.json file

        Returns:
            Validated AppConfig object

        Raises:
            FileNotFoundError: If config file doesn't exist
            ValueError: If config validation fails
        """
        config_file = Path(config_path)

        if not config_file.exists():
            self.logger.warning(f"Config file not found: {config_path}, using defaults")
            self.app_config = AppConfig()
            return self.app_config

        try:
            with open(config_file, "r") as f:
                config_data = json.load(f)

            self.app_config = AppConfig(**config_data)
            self.logger.info(f"Configuration loaded from {config_path}")
            return self.app_config

        except json.JSONDecodeError as e:
            self.logger.error(f"Invalid JSON in config file: {e}")
            raise ValueError(f"Invalid JSON in config file: {e}")
        except Exception as e:
            self.logger.error(f"Failed to load config: {e}")
            raise

    def load_video_metadata(self, metadata_path: str) -> VideoMetadataConfig:
        """
        Load video metadata configuration.

        Args:
            metadata_path: Path to videos_metadata.json file

        Returns:
            Validated VideoMetadataConfig object

        Raises:
            FileNotFoundError: If metadata file doesn't exist
            ValueError: If metadata validation fails
        """
        metadata_file = Path(metadata_path)

        if not metadata_file.exists():
            self.logger.warning(
                f"Metadata file not found: {metadata_path}, using defaults"
            )
            self.video_metadata_config = VideoMetadataConfig()
            return self.video_metadata_config

        try:
            with open(metadata_file, "r") as f:
                metadata_data = json.load(f)

            self.video_metadata_config = VideoMetadataConfig(**metadata_data)
            self.logger.info(f"Video metadata loaded from {metadata_path}")
            self.logger.info(
                f"Loaded metadata for {len(self.video_metadata_config.videos)} videos"
            )
            return self.video_metadata_config

        except json.JSONDecodeError as e:
            self.logger.error(f"Invalid JSON in metadata file: {e}")
            raise ValueError(f"Invalid JSON in metadata file: {e}")
        except Exception as e:
            self.logger.error(f"Failed to load metadata: {e}")
            raise

    def get_video_metadata(self, filename: str) -> VideoMetadata:
        """
        Get metadata for a specific video file.

        Args:
            filename: Video filename

        Returns:
            VideoMetadata object (uses fallback if not found)
        """
        if not self.video_metadata_config:
            self.logger.warning("Video metadata config not loaded, using defaults")
            return self._create_fallback_metadata(filename)

        # Search for matching filename
        for video_meta in self.video_metadata_config.videos:
            if video_meta.filename == filename:
                self.logger.debug(f"Found metadata for {filename}")
                return video_meta

        # Use fallback
        self.logger.info(f"No metadata found for {filename}, using fallback")
        return self._create_fallback_metadata(filename)

    def _create_fallback_metadata(self, filename: str) -> VideoMetadata:
        """
        Create fallback metadata for a video.

        Args:
            filename: Video filename

        Returns:
            VideoMetadata with fallback values
        """
        if not self.video_metadata_config:
            self.video_metadata_config = VideoMetadataConfig()

        defaults = self.video_metadata_config.default_metadata
        fallback = self.video_metadata_config.fallback

        # Generate title
        if fallback.use_filename_as_title:
            # Remove extension and clean up filename
            title = Path(filename).stem.replace("_", " ").replace("-", " ")
        else:
            title = fallback.title_template.format(filename=filename)

        # Generate description
        description = fallback.description_template.format(
            date=datetime.now().strftime("%Y-%m-%d"), filename=filename
        )

        return VideoMetadata(
            filename=filename,
            title=title,
            description=description,
            tags=defaults.tags,
            category_id=defaults.category_id,
            privacy_status=defaults.privacy_status,
            playlist=defaults.playlist,
            language=defaults.language,
        )

    def validate_config(self) -> bool:
        """
        Validate loaded configuration.

        Returns:
            True if configuration is valid, False otherwise
        """
        try:
            if not self.app_config:
                self.logger.error("App configuration not loaded")
                return False

            # Validate paths exist or can be created
            paths = self.app_config.paths
            videos_dir = Path(paths.videos_directory)

            if not videos_dir.exists():
                self.logger.warning(f"Videos directory does not exist: {videos_dir}")

            self.logger.info("Configuration validation successful")
            return True

        except Exception as e:
            self.logger.error(f"Configuration validation failed: {e}")
            return False
