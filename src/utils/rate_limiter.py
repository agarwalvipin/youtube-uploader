"""
Rate limiter for YouTube API quota management.

Tracks API quota usage and implements request throttling to prevent
quota exhaustion.
"""

import json
import logging
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Optional


class RateLimiter:
    """
    Manages YouTube API rate limiting and quota tracking.

    Implements token bucket algorithm for request throttling and tracks
    daily quota consumption.
    """

    # YouTube API operation costs (in quota units)
    OPERATION_COSTS = {
        "video_upload": 1600,
        "video_insert": 1600,
        "playlist_create": 50,
        "playlist_insert": 50,
        "playlist_list": 1,
        "video_list": 1,
    }

    def __init__(
        self,
        daily_quota: int = 10000,
        max_requests_per_minute: int = 60,
        quota_file: Optional[str] = None,
    ):
        """
        Initialize rate limiter.

        Args:
            daily_quota: Maximum API quota units per day
            max_requests_per_minute: Maximum requests allowed per minute
            quota_file: Path to file for persisting quota tracking
        """
        self.daily_quota = daily_quota
        self.max_requests_per_minute = max_requests_per_minute
        self.quota_file = (
            Path(quota_file) if quota_file else Path("./data/quota_tracking.json")
        )

        self.logger = logging.getLogger("youtube_uploader.rate_limiter")

        # Token bucket for request throttling
        self.tokens = max_requests_per_minute
        self.last_refill = time.time()

        # Load quota tracking data
        self.quota_data = self._load_quota_data()

    def _load_quota_data(self) -> Dict:
        """Load quota tracking data from file."""
        if self.quota_file.exists():
            try:
                with open(self.quota_file, "r") as f:
                    data = json.load(f)
                    # Check if quota data is from today
                    reset_time = datetime.fromisoformat(data.get("reset_time", ""))
                    if reset_time.date() < datetime.now(timezone.utc).date():
                        self.logger.info("Quota reset detected, starting fresh")
                        return self._create_new_quota_data()
                    return data
            except Exception as e:
                self.logger.warning(f"Failed to load quota data: {e}")

        return self._create_new_quota_data()

    def _create_new_quota_data(self) -> Dict:
        """Create new quota tracking data structure."""
        # Calculate next reset time (midnight Pacific Time)
        now = datetime.now(timezone.utc)
        reset_time = now.replace(
            hour=8, minute=0, second=0, microsecond=0
        )  # 00:00 PT = 08:00 UTC
        if now.hour >= 8:
            # Next day
            from datetime import timedelta

            reset_time += timedelta(days=1)

        return {
            "daily_quota": self.daily_quota,
            "used_quota": 0,
            "remaining_quota": self.daily_quota,
            "reset_time": reset_time.isoformat(),
            "operations": [],
        }

    def _save_quota_data(self):
        """Save quota tracking data to file."""
        try:
            self.quota_file.parent.mkdir(parents=True, exist_ok=True)
            with open(self.quota_file, "w") as f:
                json.dump(self.quota_data, f, indent=2)
        except Exception as e:
            self.logger.error(f"Failed to save quota data: {e}")

    def _refill_tokens(self):
        """Refill token bucket based on elapsed time."""
        now = time.time()
        elapsed = now - self.last_refill

        # Refill rate: max_requests_per_minute tokens per 60 seconds
        tokens_to_add = (elapsed / 60.0) * self.max_requests_per_minute
        self.tokens = min(self.max_requests_per_minute, self.tokens + tokens_to_add)
        self.last_refill = now

    def wait_for_token(self):
        """
        Wait until a token is available for making a request.

        Implements token bucket algorithm for request throttling.
        """
        self._refill_tokens()

        while self.tokens < 1:
            wait_time = (1 - self.tokens) * (60.0 / self.max_requests_per_minute)
            self.logger.debug(f"Rate limit reached, waiting {wait_time:.2f} seconds")
            time.sleep(wait_time)
            self._refill_tokens()

        self.tokens -= 1

    def check_quota(self, operation: str) -> bool:
        """
        Check if sufficient quota is available for an operation.

        Args:
            operation: Operation type (e.g., 'video_upload', 'playlist_create')

        Returns:
            True if quota is available, False otherwise
        """
        cost = self.OPERATION_COSTS.get(operation, 0)
        remaining = self.quota_data["remaining_quota"]

        if cost > remaining:
            reset_time = datetime.fromisoformat(self.quota_data["reset_time"])
            self.logger.warning(
                f"Insufficient quota for {operation}. "
                f"Required: {cost}, Available: {remaining}. "
                f"Quota resets at: {reset_time}"
            )
            return False

        return True

    def consume_quota(self, operation: str, details: Optional[str] = None):
        """
        Consume quota for an operation and track it.

        Args:
            operation: Operation type
            details: Additional details about the operation
        """
        cost = self.OPERATION_COSTS.get(operation, 0)

        self.quota_data["used_quota"] += cost
        self.quota_data["remaining_quota"] -= cost

        operation_record = {
            "type": operation,
            "cost": cost,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "details": details,
        }
        self.quota_data["operations"].append(operation_record)

        self.logger.info(
            f"Quota consumed: {operation} ({cost} units). "
            f"Remaining: {self.quota_data['remaining_quota']}/{self.daily_quota}"
        )

        self._save_quota_data()

    def get_quota_status(self) -> Dict:
        """
        Get current quota status.

        Returns:
            Dictionary with quota information
        """
        return {
            "daily_quota": self.quota_data["daily_quota"],
            "used": self.quota_data["used_quota"],
            "remaining": self.quota_data["remaining_quota"],
            "percentage_used": (self.quota_data["used_quota"] / self.daily_quota) * 100,
            "reset_time": self.quota_data["reset_time"],
        }

    def estimate_operation_cost(self, operation: str) -> int:
        """
        Get the quota cost for a specific operation.

        Args:
            operation: Operation type

        Returns:
            Quota cost in units
        """
        return self.OPERATION_COSTS.get(operation, 0)

    def can_perform_operations(self, operations: Dict[str, int]) -> bool:
        """
        Check if multiple operations can be performed with current quota.

        Args:
            operations: Dictionary of operation types and counts
                       e.g., {'video_upload': 3, 'playlist_create': 1}

        Returns:
            True if all operations can be performed, False otherwise
        """
        total_cost = sum(
            self.OPERATION_COSTS.get(op, 0) * count for op, count in operations.items()
        )

        return total_cost <= self.quota_data["remaining_quota"]
