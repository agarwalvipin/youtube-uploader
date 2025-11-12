"""
Playlist management module for YouTube.

Handles playlist creation, video addition, and playlist queries.
"""

import logging
from typing import Any, Dict, List, Optional

from googleapiclient.errors import HttpError


class PlaylistManager:
    """
    Manages YouTube playlists.

    Provides functionality to create playlists, add videos to playlists,
    and query existing playlists.
    """

    def __init__(self, youtube_service):
        """
        Initialize playlist manager.

        Args:
            youtube_service: Authenticated YouTube API service object
        """
        self.youtube = youtube_service
        self.logger = logging.getLogger("youtube_uploader.playlist_manager")

        # Cache for playlist lookups
        self._playlist_cache: Dict[str, str] = {}  # title -> playlist_id

    def create_playlist(
        self, title: str, description: str = "", privacy_status: str = "private"
    ) -> Optional[str]:
        """
        Create a new YouTube playlist.

        Args:
            title: Playlist title
            description: Playlist description
            privacy_status: Privacy status (private/public/unlisted)

        Returns:
            Playlist ID if successful, None otherwise
        """
        try:
            self.logger.info(f"Creating playlist: {title}")

            request_body = {
                "snippet": {"title": title, "description": description},
                "status": {"privacyStatus": privacy_status},
            }

            request = self.youtube.playlists().insert(
                part="snippet,status", body=request_body
            )

            response = request.execute()
            playlist_id = response.get("id")

            if playlist_id:
                self.logger.info(f"Playlist created successfully. ID: {playlist_id}")
                # Cache the playlist
                self._playlist_cache[title] = playlist_id
                return playlist_id
            else:
                self.logger.error("Playlist creation failed: No ID in response")
                return None

        except HttpError as e:
            self.logger.error(f"HTTP error creating playlist: {e}", exc_info=True)
            return None

        except Exception as e:
            self.logger.error(f"Failed to create playlist: {e}", exc_info=True)
            return None

    def list_playlists(self, max_results: int = 50) -> List[Dict[str, Any]]:
        """
        List user's playlists.

        Args:
            max_results: Maximum number of playlists to retrieve

        Returns:
            List of playlist dictionaries
        """
        playlists = []

        try:
            self.logger.debug("Fetching user playlists")

            request = self.youtube.playlists().list(
                part="snippet,status", mine=True, maxResults=max_results
            )

            while request:
                response = request.execute()

                for item in response.get("items", []):
                    playlist_info = {
                        "id": item["id"],
                        "title": item["snippet"]["title"],
                        "description": item["snippet"].get("description", ""),
                        "privacy_status": item["status"]["privacyStatus"],
                        "published_at": item["snippet"].get("publishedAt"),
                    }
                    playlists.append(playlist_info)

                    # Cache the playlist
                    self._playlist_cache[playlist_info["title"]] = playlist_info["id"]

                # Check if there are more results
                request = self.youtube.playlists().list_next(request, response)

            self.logger.info(f"Found {len(playlists)} playlists")
            return playlists

        except HttpError as e:
            self.logger.error(f"HTTP error listing playlists: {e}", exc_info=True)
            return []

        except Exception as e:
            self.logger.error(f"Failed to list playlists: {e}", exc_info=True)
            return []

    def find_playlist_by_title(self, title: str) -> Optional[str]:
        """
        Find playlist ID by title.

        Args:
            title: Playlist title to search for

        Returns:
            Playlist ID if found, None otherwise
        """
        # Check cache first
        if title in self._playlist_cache:
            self.logger.debug(f"Playlist '{title}' found in cache")
            return self._playlist_cache[title]

        # Search through user's playlists
        playlists = self.list_playlists()

        for playlist in playlists:
            if playlist["title"] == title:
                self.logger.info(f"Found playlist '{title}' with ID: {playlist['id']}")
                return playlist["id"]

        self.logger.info(f"Playlist '{title}' not found")
        return None

    def get_or_create_playlist(
        self,
        title: str,
        description: str = "",
        privacy_status: str = "private",
        create_if_not_exists: bool = True,
    ) -> Optional[str]:
        """
        Get existing playlist by title or create if it doesn't exist.

        Args:
            title: Playlist title
            description: Playlist description (used if creating)
            privacy_status: Privacy status (used if creating)
            create_if_not_exists: Whether to create playlist if not found

        Returns:
            Playlist ID if found or created, None otherwise
        """
        # Try to find existing playlist
        playlist_id = self.find_playlist_by_title(title)

        if playlist_id:
            return playlist_id

        # Create new playlist if requested
        if create_if_not_exists:
            self.logger.info(f"Playlist '{title}' not found, creating new one")
            return self.create_playlist(title, description, privacy_status)
        else:
            self.logger.warning(f"Playlist '{title}' not found and creation disabled")
            return None

    def add_video_to_playlist(
        self, video_id: str, playlist_id: str, position: Optional[int] = None
    ) -> bool:
        """
        Add a video to a playlist.

        Args:
            video_id: YouTube video ID
            playlist_id: YouTube playlist ID
            position: Position in playlist (0-based, None for end)

        Returns:
            True if successful, False otherwise
        """
        try:
            self.logger.info(f"Adding video {video_id} to playlist {playlist_id}")

            request_body = {
                "snippet": {
                    "playlistId": playlist_id,
                    "resourceId": {"kind": "youtube#video", "videoId": video_id},
                }
            }

            # Add position if specified
            if position is not None:
                request_body["snippet"]["position"] = position

            request = self.youtube.playlistItems().insert(
                part="snippet", body=request_body
            )

            response = request.execute()

            if response.get("id"):
                self.logger.info(
                    f"Video added to playlist successfully. "
                    f"Playlist item ID: {response['id']}"
                )
                return True
            else:
                self.logger.error("Failed to add video to playlist: No ID in response")
                return False

        except HttpError as e:
            self.logger.error(
                f"HTTP error adding video to playlist: {e}", exc_info=True
            )
            return False

        except Exception as e:
            self.logger.error(f"Failed to add video to playlist: {e}", exc_info=True)
            return False

    def remove_video_from_playlist(self, playlist_item_id: str) -> bool:
        """
        Remove a video from a playlist.

        Args:
            playlist_item_id: YouTube playlist item ID (not video ID)

        Returns:
            True if successful, False otherwise
        """
        try:
            self.logger.info(f"Removing playlist item {playlist_item_id}")

            request = self.youtube.playlistItems().delete(id=playlist_item_id)

            request.execute()
            self.logger.info("Video removed from playlist successfully")
            return True

        except HttpError as e:
            self.logger.error(
                f"HTTP error removing video from playlist: {e}", exc_info=True
            )
            return False

        except Exception as e:
            self.logger.error(
                f"Failed to remove video from playlist: {e}", exc_info=True
            )
            return False

    def get_playlist_videos(
        self, playlist_id: str, max_results: int = 50
    ) -> List[Dict[str, Any]]:
        """
        Get videos in a playlist.

        Args:
            playlist_id: YouTube playlist ID
            max_results: Maximum number of videos to retrieve

        Returns:
            List of video information dictionaries
        """
        videos = []

        try:
            self.logger.debug(f"Fetching videos for playlist {playlist_id}")

            request = self.youtube.playlistItems().list(
                part="snippet,contentDetails",
                playlistId=playlist_id,
                maxResults=max_results,
            )

            while request:
                response = request.execute()

                for item in response.get("items", []):
                    video_info = {
                        "playlist_item_id": item["id"],
                        "video_id": item["contentDetails"]["videoId"],
                        "title": item["snippet"]["title"],
                        "position": item["snippet"]["position"],
                        "published_at": item["snippet"].get("publishedAt"),
                    }
                    videos.append(video_info)

                # Check if there are more results
                request = self.youtube.playlistItems().list_next(request, response)

            self.logger.info(f"Found {len(videos)} videos in playlist")
            return videos

        except HttpError as e:
            self.logger.error(
                f"HTTP error fetching playlist videos: {e}", exc_info=True
            )
            return []

        except Exception as e:
            self.logger.error(f"Failed to fetch playlist videos: {e}", exc_info=True)
            return []

    def clear_cache(self):
        """Clear the playlist cache."""
        self._playlist_cache.clear()
        self.logger.debug("Playlist cache cleared")
