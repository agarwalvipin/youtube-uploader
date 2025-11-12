"""
OAuth 2.0 authentication handler for YouTube API.

Manages authentication flow, token storage, and refresh.
"""

import logging
import os
from pathlib import Path
from typing import Optional

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError


class Authenticator:
    """
    Handles OAuth 2.0 authentication for YouTube API.

    Manages the complete authentication lifecycle including initial OAuth flow,
    token storage, and automatic token refresh.
    """

    # YouTube API scopes required for upload and playlist management
    SCOPES = [
        "https://www.googleapis.com/auth/youtube.upload",
        "https://www.googleapis.com/auth/youtube",
        "https://www.googleapis.com/auth/youtube.force-ssl",
    ]

    API_SERVICE_NAME = "youtube"
    API_VERSION = "v3"

    def __init__(
        self, client_secrets_file: str, credentials_file: Optional[str] = None
    ):
        """
        Initialize authenticator.

        Args:
            client_secrets_file: Path to OAuth 2.0 client secrets JSON file
            credentials_file: Path to store credentials (default: ~/.youtube-uploader/credentials.json)
        """
        self.client_secrets_file = Path(client_secrets_file)

        if credentials_file:
            self.credentials_file = Path(credentials_file)
        else:
            # Default credentials location
            creds_dir = Path.home() / ".youtube-uploader"
            creds_dir.mkdir(parents=True, exist_ok=True)
            self.credentials_file = creds_dir / "credentials.json"

            # Set restrictive permissions (owner read/write only)
            try:
                os.chmod(creds_dir, 0o700)
            except Exception:
                pass  # Windows doesn't support chmod

        self.logger = logging.getLogger("youtube_uploader.authenticator")
        self.credentials: Optional[Credentials] = None
        self.service = None

    def authenticate(self) -> bool:
        """
        Perform authentication flow.

        Loads existing credentials if available, refreshes if expired,
        or initiates new OAuth flow if needed.

        Returns:
            True if authentication successful, False otherwise
        """
        try:
            # Load existing credentials
            if self.credentials_file.exists():
                self.logger.info("Loading existing credentials")
                self.credentials = Credentials.from_authorized_user_file(
                    str(self.credentials_file), self.SCOPES
                )

            # Refresh or obtain new credentials
            if not self.credentials or not self.credentials.valid:
                if (
                    self.credentials
                    and self.credentials.expired
                    and self.credentials.refresh_token
                ):
                    self.logger.info("Refreshing expired credentials")
                    self.credentials.refresh(Request())
                else:
                    self.logger.info("Starting OAuth 2.0 flow")
                    if not self.client_secrets_file.exists():
                        self.logger.error(
                            f"Client secrets file not found: {self.client_secrets_file}"
                        )
                        return False

                    flow = InstalledAppFlow.from_client_secrets_file(
                        str(self.client_secrets_file), self.SCOPES
                    )
                    try:
                        # Try opening a local server for the OAuth callback (default, user-friendly).
                        self.credentials = flow.run_local_server(
                            port=8080,
                            prompt="consent",
                            success_message="Authentication successful! You can close this window.",
                        )
                    except OSError as e:
                        # Common on systems where the port is in use or not bindable.
                        self.logger.warning(
                            f"Local server failed on port 8080: {e}; falling back to console-based OAuth flow"
                        )
                        # Fall back to console flow: user copies the URL and pastes the code.
                        self.credentials = flow.run_console()
                    except Exception as e:
                        # Re-raise unexpected exceptions after logging.
                        self.logger.error(f"OAuth flow failed: {e}")
                        raise

                # Save credentials
                self._save_credentials()

            self.logger.info("Authentication successful")
            return True

        except Exception as e:
            self.logger.error(f"Authentication failed: {e}", exc_info=True)
            return False

    def _save_credentials(self):
        """Save credentials to file."""
        try:
            with open(self.credentials_file, "w") as f:
                f.write(self.credentials.to_json())

            # Set restrictive permissions
            try:
                os.chmod(self.credentials_file, 0o600)
            except Exception:
                pass  # Windows doesn't support chmod

            self.logger.debug(f"Credentials saved to {self.credentials_file}")
        except Exception as e:
            self.logger.error(f"Failed to save credentials: {e}")

    def get_authenticated_service(self):
        """
        Get authenticated YouTube API service object.

        Returns:
            YouTube API service object or None if authentication failed
        """
        if not self.credentials or not self.credentials.valid:
            self.logger.warning("Credentials invalid, attempting re-authentication")
            if not self.authenticate():
                return None

        if not self.service:
            try:
                self.service = build(
                    self.API_SERVICE_NAME,
                    self.API_VERSION,
                    credentials=self.credentials,
                )
                self.logger.info("YouTube API service initialized")
            except Exception as e:
                self.logger.error(f"Failed to build API service: {e}")
                return None

        return self.service

    def refresh_credentials(self) -> bool:
        """
        Manually refresh credentials.

        Returns:
            True if refresh successful, False otherwise
        """
        try:
            if not self.credentials:
                self.logger.error("No credentials to refresh")
                return False

            if not self.credentials.refresh_token:
                self.logger.error("No refresh token available")
                return False

            self.logger.info("Refreshing credentials")
            self.credentials.refresh(Request())
            self._save_credentials()

            # Invalidate service to force rebuild with new credentials
            self.service = None

            return True
        except Exception as e:
            self.logger.error(f"Failed to refresh credentials: {e}")
            return False

    def revoke_credentials(self) -> bool:
        """
        Revoke access and delete stored credentials.

        Returns:
            True if revocation successful, False otherwise
        """
        try:
            if self.credentials and self.credentials.valid:
                # Revoke token
                import requests

                requests.post(
                    "https://oauth2.googleapis.com/revoke",
                    params={"token": self.credentials.token},
                    headers={"content-type": "application/x-www-form-urlencoded"},
                )
                self.logger.info("Credentials revoked")

            # Delete credentials file
            if self.credentials_file.exists():
                self.credentials_file.unlink()
                self.logger.info("Credentials file deleted")

            self.credentials = None
            self.service = None

            return True
        except Exception as e:
            self.logger.error(f"Failed to revoke credentials: {e}")
            return False

    def is_authenticated(self) -> bool:
        """
        Check if currently authenticated.

        Returns:
            True if valid credentials exist, False otherwise
        """
        return self.credentials is not None and self.credentials.valid

    def get_user_info(self) -> Optional[dict]:
        """
        Get authenticated user information.

        Returns:
            Dictionary with user info or None if unavailable
        """
        try:
            service = self.get_authenticated_service()
            if not service:
                return None

            request = service.channels().list(part="snippet", mine=True)
            response = request.execute()

            if "items" in response and len(response["items"]) > 0:
                channel = response["items"][0]
                return {
                    "channel_id": channel["id"],
                    "title": channel["snippet"]["title"],
                    "description": channel["snippet"].get("description", ""),
                    "custom_url": channel["snippet"].get("customUrl", ""),
                }

            return None
        except HttpError as e:
            self.logger.error(f"Failed to get user info: {e}")
            return None
