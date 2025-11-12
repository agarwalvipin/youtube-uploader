# YouTube Uploader System - Architecture Design

## Executive Summary

This document outlines the architecture for a Python-based YouTube video uploader system that processes videos from a folder sequentially, uploads them to YouTube with configurable metadata, and manages playlists. The system emphasizes reliability, user-friendliness, and best practices for API interaction.

---

## 1. Project Structure

```
youtube-uploader/
├── src/
│   ├── __init__.py
│   ├── main.py                    # Main orchestrator script
│   ├── auth/
│   │   ├── __init__.py
│   │   └── authenticator.py       # OAuth 2.0 authentication handler
│   ├── uploader/
│   │   ├── __init__.py
│   │   ├── video_uploader.py      # Video upload functionality
│   │   └── resumable_upload.py    # Resumable upload implementation
│   ├── playlist/
│   │   ├── __init__.py
│   │   └── playlist_manager.py    # Playlist creation and management
│   ├── config/
│   │   ├── __init__.py
│   │   └── config_parser.py       # Configuration file parser
│   ├── utils/
│   │   ├── __init__.py
│   │   ├── logger.py              # Logging configuration
│   │   ├── validators.py          # Input validation utilities
│   │   └── rate_limiter.py        # API rate limiting handler
│   └── models/
│       ├── __init__.py
│       ├── video_metadata.py      # Video metadata data model
│       └── upload_state.py        # Upload state tracking model
├── config/
│   ├── config.json                # Main configuration file
│   ├── videos_metadata.json       # Video metadata configuration
│   └── client_secrets.json        # OAuth 2.0 client credentials
├── videos/                        # Directory for videos to upload
├── logs/                          # Log files directory
├── data/
│   └── upload_history.json        # Upload history tracking
├── tests/
│   ├── __init__.py
│   ├── test_auth.py
│   ├── test_uploader.py
│   ├── test_playlist.py
│   └── test_config.py
├── docs/
│   └── setup_guide.md             # User setup instructions
├── requirements.txt               # Python dependencies
├── .env.example                   # Environment variables template
├── .gitignore
└── README.md
```

### Directory Responsibilities

- **`src/`**: Core application source code
- **`config/`**: Configuration files (credentials, metadata)
- **`videos/`**: Input directory for videos to be uploaded
- **`logs/`**: Application logs and error tracking
- **`data/`**: Runtime data (upload history, state)
- **`tests/`**: Unit and integration tests
- **`docs/`**: User documentation

---

## 2. Technology Stack

### Core Python Libraries

```
google-api-python-client==2.108.0   # YouTube Data API v3 client
google-auth==2.25.0                 # Google authentication
google-auth-oauthlib==1.1.0         # OAuth 2.0 flow
google-auth-httplib2==0.1.1         # HTTP library for auth
```

### Supporting Libraries

```
pydantic==2.5.0                     # Data validation and settings
python-dotenv==1.0.0                # Environment variable management
tenacity==8.2.3                     # Retry logic with exponential backoff
rich==13.7.0                        # Rich terminal output and progress bars
```

### Optional/Development Libraries

```
pytest==7.4.3                       # Testing framework
pytest-cov==4.1.0                   # Code coverage
black==23.12.0                      # Code formatting
pylint==3.0.3                       # Code linting
```

### Python Version

- **Minimum**: Python 3.8
- **Recommended**: Python 3.10+

---

## 3. System Components

### 3.1 Component Overview

```
┌─────────────────────────────────────────────────────────────┐
│                        Main Orchestrator                     │
│                          (main.py)                           │
└───────────────┬─────────────────────────────────────────────┘
                │
                ├──── Authenticator ────────────────────────┐
                │     (OAuth 2.0 Handler)                   │
                │                                           │
                ├──── Configuration Parser ─────────────────┤
                │     (JSON/YAML Parser)                    │
                │                                           │
                ├──── Video Uploader ───────────────────────┤
                │     (Upload Logic + Resumable Upload)    │
                │                                           │
                ├──── Playlist Manager ─────────────────────┤
                │     (Playlist Creation & Video Addition) │
                │                                           │
                └──── Utilities ────────────────────────────┤
                      (Logger, Rate Limiter, Validators)   │
                                                            │
                ┌───────────────────────────────────────────┘
                │
                ▼
          YouTube Data API v3
```

### 3.2 Component Responsibilities

#### **Main Orchestrator** ([`main.py`](src/main.py))

**Responsibilities:**

- Initialize all components
- Scan videos directory and sort files alphabetically
- Load and validate configuration
- Coordinate authentication flow
- Iterate through videos and orchestrate upload process
- Manage upload history to prevent duplicates
- Handle graceful shutdown and cleanup

**Key Functions:**

- `main()`: Entry point
- `initialize_system()`: Setup components
- `scan_videos()`: Discover and sort video files
- `process_uploads()`: Main upload loop
- `cleanup()`: Cleanup resources

---

#### **Authenticator** ([`auth/authenticator.py`](src/auth/authenticator.py))

**Responsibilities:**

- Manage OAuth 2.0 authentication flow
- Store and refresh access tokens
- Handle credential validation
- Provide authenticated API client

**Key Functions:**

- `authenticate()`: Perform OAuth flow
- `get_authenticated_service()`: Return YouTube API service object
- `refresh_credentials()`: Refresh expired tokens
- `revoke_credentials()`: Revoke access

**Authentication Storage:**

- Credentials stored in `~/.youtube-uploader/credentials.json`
- Token refresh handled automatically

---

#### **Video Uploader** ([`uploader/video_uploader.py`](src/uploader/video_uploader.py))

**Responsibilities:**

- Upload video files to YouTube
- Apply metadata (title, description, tags)
- Set privacy status
- Implement resumable uploads for large files
- Handle upload retries with exponential backoff

**Key Functions:**

- `upload_video(video_path, metadata)`: Main upload function
- `prepare_upload_request()`: Build API request
- `execute_resumable_upload()`: Handle chunked upload
- `verify_upload()`: Confirm successful upload

**Upload Strategy:**

- Uses resumable upload protocol for files > 5MB
- Chunk size: 10MB (configurable)
- Retry on network errors (max 5 attempts)

---

#### **Resumable Upload Handler** ([`uploader/resumable_upload.py`](src/uploader/resumable_upload.py))

**Responsibilities:**

- Implement YouTube's resumable upload protocol
- Handle upload progress tracking
- Resume interrupted uploads
- Manage upload sessions

**Key Functions:**

- `initialize_upload()`: Start upload session
- `upload_chunk()`: Upload single chunk
- `resume_upload()`: Continue interrupted upload
- `get_upload_status()`: Query current progress

---

#### **Playlist Manager** ([`playlist/playlist_manager.py`](src/playlist/playlist_manager.py))

**Responsibilities:**

- Create new playlists
- Check if playlist exists
- Add videos to playlists
- Manage playlist metadata

**Key Functions:**

- `create_playlist(title, description, privacy)`: Create new playlist
- `get_or_create_playlist(title)`: Get existing or create new
- `add_video_to_playlist(video_id, playlist_id)`: Add video
- `list_playlists()`: List user's playlists

---

#### **Configuration Parser** ([`config/config_parser.py`](src/config/config_parser.py))

**Responsibilities:**

- Load and validate configuration files
- Parse video metadata
- Validate configuration schema
- Provide default values

**Key Functions:**

- `load_config()`: Load main config.json
- `load_video_metadata()`: Load videos_metadata.json
- `validate_config()`: Validate against schema
- `get_video_metadata(filename)`: Get metadata for specific video

---

#### **Utilities**

**Logger** ([`utils/logger.py`](src/utils/logger.py))

- Configure logging with rotation
- Multiple log levels (DEBUG, INFO, WARNING, ERROR)
- Both file and console output
- Structured logging format

**Rate Limiter** ([`utils/rate_limiter.py`](src/utils/rate_limiter.py))

- Implement rate limiting for API calls
- Track quota usage
- Prevent quota exhaustion
- Exponential backoff on quota errors

**Validators** ([`utils/validators.py`](src/utils/validators.py))

- Validate video file formats
- Validate metadata fields
- Check file size limits
- Validate configuration values

---

## 4. Configuration Schema

### 4.1 Main Configuration ([`config/config.json`](config/config.json))

```json
{
  "application": {
    "name": "YouTube Uploader",
    "version": "1.0.0"
  },
  "paths": {
    "videos_directory": "./videos",
    "credentials_file": "./config/client_secrets.json",
    "upload_history": "./data/upload_history.json"
  },
  "upload": {
    "default_privacy": "private",
    "chunk_size_mb": 10,
    "max_retries": 5,
    "retry_delay_seconds": 2,
    "concurrent_uploads": 1
  },
  "playlist": {
    "create_if_not_exists": true,
    "default_playlist_privacy": "private"
  },
  "api": {
    "quota_limit_per_day": 10000,
    "max_requests_per_minute": 60
  },
  "logging": {
    "level": "INFO",
    "log_directory": "./logs",
    "max_log_size_mb": 50,
    "backup_count": 5
  }
}
```

### 4.2 Video Metadata Configuration ([`config/videos_metadata.json`](config/videos_metadata.json))

```json
{
  "default_metadata": {
    "category_id": "22",
    "privacy_status": "private",
    "tags": ["default", "tag"],
    "language": "en",
    "playlist": null
  },
  "videos": [
    {
      "filename": "video001.mp4",
      "title": "Introduction to Python Programming",
      "description": "Learn the basics of Python programming in this comprehensive tutorial.",
      "tags": ["python", "programming", "tutorial", "beginner"],
      "category_id": "27",
      "privacy_status": "private",
      "playlist": "Python Tutorial Series"
    },
    {
      "filename": "video002.mp4",
      "title": "Advanced Python Concepts",
      "description": "Deep dive into advanced Python concepts including decorators, generators, and more.",
      "tags": ["python", "programming", "advanced", "tutorial"],
      "category_id": "27",
      "privacy_status": "private",
      "playlist": "Python Tutorial Series"
    }
  ],
  "fallback": {
    "title_template": "{filename}",
    "description_template": "Uploaded on {date}",
    "use_filename_as_title": true
  }
}
```

### 4.3 OAuth Client Secrets ([`config/client_secrets.json`](config/client_secrets.json))

```json
{
  "installed": {
    "client_id": "YOUR_CLIENT_ID.apps.googleusercontent.com",
    "project_id": "your-project-id",
    "auth_uri": "https://accounts.google.com/o/oauth2/auth",
    "token_uri": "https://oauth2.googleapis.com/token",
    "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
    "client_secret": "YOUR_CLIENT_SECRET",
    "redirect_uris": ["http://localhost:8080/"]
  }
}
```

### 4.4 Upload History ([`data/upload_history.json`](data/upload_history.json))

```json
{
  "uploads": [
    {
      "filename": "video001.mp4",
      "video_id": "dQw4w9WgXcQ",
      "title": "Introduction to Python Programming",
      "uploaded_at": "2024-01-15T10:30:00Z",
      "playlist_id": "PLxyz123",
      "status": "completed"
    }
  ],
  "last_updated": "2024-01-15T10:30:00Z"
}
```

### 4.5 Configuration Field Definitions

#### Video Metadata Fields

| Field            | Type   | Required | Description                                |
| ---------------- | ------ | -------- | ------------------------------------------ |
| `filename`       | string | Yes      | Exact filename in videos directory         |
| `title`          | string | Yes      | Video title (max 100 chars)                |
| `description`    | string | No       | Video description (max 5000 chars)         |
| `tags`           | array  | No       | Video tags (max 500 chars total)           |
| `category_id`    | string | No       | YouTube category ID (default: 22)          |
| `privacy_status` | enum   | No       | private/public/unlisted (default: private) |
| `playlist`       | string | No       | Playlist title to add video to             |

#### YouTube Category IDs (Common)

- 1: Film & Animation
- 10: Music
- 22: People & Blogs
- 23: Comedy
- 24: Entertainment
- 25: News & Politics
- 27: Education
- 28: Science & Technology

---

## 5. Authentication Flow

### 5.1 OAuth 2.0 Flow Diagram

```
┌──────────┐                                    ┌─────────────┐
│  User    │                                    │   Google    │
│          │                                    │   OAuth     │
└────┬─────┘                                    └──────┬──────┘
     │                                                 │
     │ 1. Run application                             │
     │ ──────────────────────────────────────>        │
     │                                                 │
     │ 2. Check for stored credentials                │
     │ <──────────────────────────────────────        │
     │                                                 │
     │ 3. If no credentials: Open browser             │
     │ ──────────────────────────────────────>        │
     │                                                 │
     │ 4. User authenticates and grants permissions   │
     │ ─────────────────────────────────────────────> │
     │                                                 │
     │ 5. Receive authorization code                  │
     │ <───────────────────────────────────────────── │
     │                                                 │
     │ 6. Exchange code for tokens                    │
     │ ─────────────────────────────────────────────> │
     │                                                 │
     │ 7. Receive access token + refresh token        │
     │ <───────────────────────────────────────────── │
     │                                                 │
     │ 8. Store tokens locally                        │
     │ <──────────────────────────────────────        │
     │                                                 │
     │ 9. Make API calls with access token            │
     │ ─────────────────────────────────────────────> │
     │                                                 │
     │ 10. Token expires? Auto-refresh                │
     │ <───────────────────────────────────────────── │
```

### 5.2 Authentication Implementation Details

**OAuth 2.0 Scopes Required:**

```python
SCOPES = [
    'https://www.googleapis.com/auth/youtube.upload',
    'https://www.googleapis.com/auth/youtube',
    'https://www.googleapis.com/auth/youtube.force-ssl'
]
```

**Credential Storage:**

- Location: `~/.youtube-uploader/credentials.json`
- Format: JSON with access token, refresh token, expiry
- Permissions: Read/write only for owner (chmod 600)

**First-Time Setup:**

1. User runs application
2. Browser opens for Google account login
3. User grants YouTube API permissions
4. Authorization code received via redirect
5. Tokens stored locally for future use

**Subsequent Runs:**

1. Application loads stored credentials
2. Checks token expiry
3. Auto-refreshes if expired
4. Proceeds with uploads

**Security Considerations:**

- Never commit `client_secrets.json` to version control
- Store credentials outside project directory
- Use environment variables for sensitive data
- Implement token encryption (optional enhancement)

---

## 6. Upload Workflow

### 6.1 Main Upload Process Flow

```
START
  │
  ├─> Initialize System
  │    ├─> Load configuration
  │    ├─> Setup logging
  │    └─> Authenticate with YouTube API
  │
  ├─> Scan Videos Directory
  │    ├─> List all video files
  │    ├─> Sort alphabetically
  │    └─> Filter already uploaded (check history)
  │
  ├─> Load Video Metadata
  │    ├─> Parse videos_metadata.json
  │    └─> Match filenames with metadata
  │
  ├─> For Each Video:
  │    │
  │    ├─> Validate Video File
  │    │    ├─> Check file exists
  │    │    ├─> Verify format
  │    │    └─> Check file size
  │    │
  │    ├─> Get/Create Playlist (if specified)
  │    │    ├─> Check if playlist exists
  │    │    └─> Create if doesn't exist
  │    │
  │    ├─> Upload Video
  │    │    ├─> Initialize resumable upload
  │    │    ├─> Upload in chunks
  │    │    ├─> Display progress
  │    │    └─> Verify completion
  │    │
  │    ├─> Add to Playlist (if specified)
  │    │    └─> Call playlist API
  │    │
  │    ├─> Update Upload History
  │    │    └─> Record video_id, timestamp, status
  │    │
  │    └─> Log Success/Failure
  │
  └─> Cleanup and Exit
       ├─> Close API connections
       ├─> Save final state
       └─> Display summary report
```

### 6.2 Resumable Upload Process

```
Initialize Upload Session
  │
  ├─> Send POST request with metadata
  ├─> Receive upload URL
  │
Upload Chunks
  │
  ├─> For each chunk (10MB):
  │    │
  │    ├─> Send PUT request with chunk data
  │    ├─> Include Content-Range header
  │    │
  │    ├─> Response 308? Continue next chunk
  │    ├─> Response 200/201? Upload complete
  │    └─> Response 5xx/Network Error? Retry
  │         │
  │         ├─> Wait (exponential backoff)
  │         ├─> Query upload status
  │         └─> Resume from last successful byte
  │
Finalize Upload
  │
  ├─> Receive video_id
  ├─> Verify video status
  └─> Return success
```

---

## 7. Error Handling Strategy

### 7.1 Error Categories

#### **Authentication Errors**

- **Invalid credentials**: Prompt user to re-authenticate
- **Expired token**: Auto-refresh and retry
- **Revoked access**: Re-initiate OAuth flow
- **Network errors**: Retry with exponential backoff

#### **Upload Errors**

- **File not found**: Log error, skip to next video
- **Invalid format**: Log error, skip to next video
- **File too large**: Log warning, attempt resumable upload
- **Network interruption**: Resume from last successful chunk
- **Quota exceeded**: Pause, log error, provide quota reset time

#### **API Errors**

- **Rate limit exceeded**: Wait and retry with exponential backoff
- **Invalid metadata**: Log validation error, use defaults
- **Playlist not found**: Create playlist if configured
- **Service unavailable**: Retry with exponential backoff

#### **Configuration Errors**

- **Invalid JSON**: Fail fast with clear error message
- **Missing required fields**: Use defaults or prompt user
- **Invalid file paths**: Fail fast with clear error message

### 7.2 Retry Strategy

**Exponential Backoff Configuration:**

```
Base delay: 2 seconds
Max delay: 300 seconds (5 minutes)
Max retries: 5
Backoff factor: 2

Retry delays:
  Attempt 1: 2 seconds
  Attempt 2: 4 seconds
  Attempt 3: 8 seconds
  Attempt 4: 16 seconds
  Attempt 5: 32 seconds
```

**Retryable Operations:**

- Network requests to YouTube API
- Chunk uploads in resumable upload
- Playlist creation/modification
- Token refresh

**Non-Retryable Errors:**

- Invalid credentials (requires user intervention)
- Malformed requests (fix required)
- Permanent quota exhaustion
- Invalid video format

### 7.3 Error Recovery Mechanisms

**Upload State Persistence:**

- Save upload progress to disk every 10 chunks
- On restart, check for incomplete uploads
- Resume from last successful checkpoint

**Graceful Degradation:**

- If playlist creation fails, continue upload without playlist
- If metadata incomplete, use defaults
- If thumbnail upload fails, continue with video upload

**User Notifications:**

- Real-time progress updates
- Clear error messages with actionable steps
- Summary report at completion

---

## 8. Logging Strategy

### 8.1 Log Levels and Use Cases

| Level    | Use Case                         | Examples                                                 |
| -------- | -------------------------------- | -------------------------------------------------------- |
| DEBUG    | Development debugging            | API request/response details, variable values            |
| INFO     | Normal operations                | Upload start/complete, file processing                   |
| WARNING  | Potential issues                 | Missing metadata, using defaults, rate limit approaching |
| ERROR    | Failures that allow continuation | Single video upload failure, validation errors           |
| CRITICAL | System-level failures            | Authentication failure, config file not found            |

### 8.2 Log Format

```
[TIMESTAMP] [LEVEL] [COMPONENT] [MESSAGE] [CONTEXT]

Example:
[2024-01-15 10:30:45.123] [INFO] [VideoUploader] Upload started for video001.mp4 {size: 150MB, duration: 10:30}
[2024-01-15 10:31:15.456] [INFO] [VideoUploader] Upload progress: 25% {uploaded: 37.5MB, remaining: 112.5MB}
[2024-01-15 10:35:22.789] [INFO] [VideoUploader] Upload completed {video_id: dQw4w9WgXcQ, duration: 4m 37s}
```

### 8.3 Log File Organization

```
logs/
├── youtube_uploader.log           # Main application log (INFO+)
├── youtube_uploader_debug.log     # Debug log (DEBUG+)
├── youtube_uploader_error.log     # Error log (ERROR+ only)
└── archive/                       # Rotated log archives
    ├── youtube_uploader.log.2024-01-14
    └── youtube_uploader.log.2024-01-13
```

**Rotation Policy:**

- Max file size: 50MB
- Backup count: 5 files
- Rotation trigger: Size-based
- Archive format: Date-stamped

### 8.4 Logged Events

**Authentication:**

- OAuth flow initiation
- Token acquisition/refresh
- Authentication errors

**Video Processing:**

- Video discovery and sorting
- File validation
- Upload initiation and progress (every 10%)
- Upload completion with video_id
- Metadata application

**Playlist Management:**

- Playlist creation/lookup
- Video addition to playlist
- Playlist errors

**Errors and Exceptions:**

- All exceptions with stack traces
- API error responses
- Validation failures
- Network errors

**Performance Metrics:**

- Upload duration per video
- Total bandwidth used
- API quota consumption
- Success/failure rates

---

## 9. API Rate Limiting Strategy

### 9.1 YouTube API Quota System

**Daily Quota Allocation:**

- Default: 10,000 units per day
- Units reset at midnight Pacific Time (PT)

**Operation Costs:**
| Operation | Cost (Units) |
|-----------|--------------|
| Video upload | 1,600 |
| Video insert (metadata) | 1,600 |
| Playlist creation | 50 |
| Playlist item insert | 50 |
| Video list | 1 |
| Playlist list | 1 |

**Example Scenario:**

- Upload 1 video with metadata: 1,600 units
- Create playlist: 50 units
- Add video to playlist: 50 units
- **Total: 1,700 units per video**
- **Daily capacity: ~5-6 videos**

### 9.2 Rate Limiting Implementation

**Quota Tracking:**

```python
{
  "daily_quota": 10000,
  "used_quota": 3400,
  "remaining_quota": 6600,
  "reset_time": "2024-01-16T08:00:00Z",
  "operations": [
    {"type": "video_upload", "cost": 1600, "timestamp": "..."},
    {"type": "playlist_create", "cost": 50, "timestamp": "..."}
  ]
}
```

**Pre-Upload Validation:**

1. Check remaining quota before upload
2. Estimate total cost for batch
3. Warn user if insufficient quota
4. Optionally pause until reset

**Quota Exceeded Handling:**

1. Detect quota exceeded error (HTTP 403)
2. Calculate time until reset
3. Log error with reset time
4. Offer options:
   - Wait and auto-resume
   - Stop and resume tomorrow
   - Skip to next day

**Request Throttling:**

- Max requests per minute: 60
- Implement token bucket algorithm
- Add artificial delay between requests if needed

---

## 10. Data Models

### 10.1 Video Metadata Model

```python
class VideoMetadata:
    filename: str                    # Required
    title: str                       # Required, max 100 chars
    description: str = ""            # Optional, max 5000 chars
    tags: List[str] = []            # Optional, max 500 chars total
    category_id: str = "22"         # Optional, default: People & Blogs
    privacy_status: str = "private" # private/public/unlisted
    playlist: Optional[str] = None  # Playlist title
    language: str = "en"            # ISO 639-1 code
```

### 10.2 Upload State Model

```python
class UploadState:
    filename: str
    video_id: Optional[str]
    upload_url: Optional[str]
    bytes_uploaded: int = 0
    total_bytes: int
    status: str  # pending/uploading/completed/failed
    retry_count: int = 0
    last_error: Optional[str] = None
    created_at: datetime
    updated_at: datetime
```

### 10.3 Playlist Model

```python
class Playlist:
    id: Optional[str]
    title: str
    description: str = ""
    privacy_status: str = "private"
    created_at: Optional[datetime]
```

---

## 11. System Architecture Diagram

```
┌───────────────────────────────────────────────────────────────────┐
│                          USER INTERFACE                           │
│                     (CLI with Progress Display)                   │
└────────────────┬──────────────────────────────────────────────────┘
                 │
                 ▼
┌───────────────────────────────────────────────────────────────────┐
│                       MAIN ORCHESTRATOR                           │
│  ┌─────────────────────────────────────────────────────────────┐ │
│  │  • Initialize components                                     │ │
│  │  • Scan and sort videos                                      │ │
│  │  • Coordinate upload workflow                                │ │
│  │  • Manage application state                                  │ │
│  └─────────────────────────────────────────────────────────────┘ │
└────┬──────────┬──────────┬──────────┬──────────┬────────────┬───┘
     │          │          │          │          │            │
     ▼          ▼          ▼          ▼          ▼            ▼
┌─────────┐ ┌─────────┐ ┌────────┐ ┌─────────┐ ┌────────┐ ┌──────┐
│  Auth   │ │ Config  │ │ Video  │ │Playlist │ │ Logger │ │ Rate │
│ Handler │ │ Parser  │ │Uploader│ │Manager  │ │        │ │Limit │
└────┬────┘ └────┬────┘ └───┬────┘ └────┬────┘ └───┬────┘ └──┬───┘
     │           │           │           │          │         │
     │           │           │           │          │         │
     └───────────┴───────────┴───────────┴──────────┴─────────┘
                             │
                             ▼
                    ┌─────────────────┐
                    │  YouTube Data   │
                    │    API v3       │
                    └─────────────────┘
                             │
                             ▼
                    ┌─────────────────┐
                    │    YouTube      │
                    │    Platform     │
                    └─────────────────┘
```

---

## 12. Security Considerations

### 12.1 Credential Management

**Best Practices:**

- Store OAuth credentials outside project directory
- Use environment variables for sensitive data
- Never commit credentials to version control
- Set restrictive file permissions (chmod 600)
- Implement credential encryption (optional)

**`.gitignore` Requirements:**

```
config/client_secrets.json
config/credentials.json
.env
*.log
data/upload_history.json
```

### 12.2 API Security

- Use HTTPS for all API communications
- Validate SSL certificates
- Implement request signing
- Rotate tokens regularly
- Monitor for suspicious activity

### 12.3 Data Privacy

- Videos default to "private" status
- No telemetry or analytics unless opted-in
- Local storage of upload history only
- Clear user consent for OAuth scopes

---

## 13. Performance Considerations

### 13.1 Upload Optimization

**Chunked Uploads:**

- Optimal chunk size: 10MB (balance between reliability and efficiency)
- Parallel chunk processing (optional enhancement)
- Resume capability reduces data re-transmission

**Network Optimization:**

- Connection pooling for API requests
- Compression for metadata payloads
- Efficient file reading (buffered I/O)

### 13.2 Memory Management

**Large File Handling:**

- Stream video files instead of loading into memory
- Process chunks incrementally
- Release resources after each upload

**Estimated Memory Usage:**

- Base application: ~50MB
- Per upload session: ~20MB (chunk buffer)
- Maximum concurrent: 1 upload (configurable)

### 13.3 Scalability

**Current Design (Single User):**

- Sequential uploads
- Single authentication session
- Local file system

**Future Enhancements:**

- Multi-threaded uploads (respecting rate limits)
- Cloud storage integration (S3, GCS)
- Web-based UI
- Multi-user support with separate credential management

---

## 14. Testing Strategy

### 14.1 Unit Tests

**Components to Test:**

- Configuration parser (valid/invalid inputs)
- Metadata validation
- File validation
- Rate limiter logic
- Authentication flow mocking

### 14.2 Integration Tests

**End-to-End Scenarios:**

- Complete upload workflow with test video
- Playlist creation and video addition
- Resume interrupted upload
- Quota exceeded handling
- Network error recovery

### 14.3 Test Data

**Mock Objects:**

- Fake YouTube API responses
- Test video files (small size)
- Sample configuration files
- Test credentials (sandbox environment)

---

## 15. Deployment and Setup

### 15.1 Prerequisites

**User Requirements:**

1. Python 3.8+ installed
2. Google Cloud Project created
3. YouTube Data API v3 enabled
4. OAuth 2.0 credentials obtained
5. Sufficient disk space for videos

### 15.2 Installation Steps

```bash
# 1. Clone repository
git clone <repository-url>
cd youtube-uploader

# 2. Create virtual environment
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Create configuration directories
mkdir -p config videos logs data

# 5. Copy client secrets
cp path/to/client_secrets.json config/

# 6. Copy and edit configuration
cp config/config.json.example config/config.json
cp config/videos_metadata.json.example config/videos_metadata.json

# 7. First run (authentication)
python src/main.py
```

### 15.3 Configuration Steps

**Google Cloud Console:**

1. Create new project or select existing
2. Enable YouTube Data API v3
3. Create OAuth 2.0 credentials (Desktop app)
4. Download client_secrets.json
5. Add test users (if in testing mode)

**Application Setup:**

1. Place videos in `videos/` directory
2. Edit `videos_metadata.json` with video details
3. Adjust `config.json` settings as needed
4. Run application and complete OAuth flow

---

## 16. Monitoring and Observability

### 16.1 Metrics to Track

**Upload Metrics:**

- Total videos uploaded
- Success/failure rate
- Average upload duration
- Total bandwidth consumed

**API Metrics:**

- Quota usage per day
- API error rates
- Rate limit hits
- Authentication failures

**System Metrics:**

- Disk space usage
- Memory consumption
- CPU utilization during uploads

### 16.2 Health Checks

**Pre-Upload Validation:**

- Verify authentication is valid
- Check remaining API quota
- Validate configuration files
- Ensure sufficient disk space

**Post-Upload Verification:**

- Confirm video ID received
- Verify video status on YouTube
- Check playlist addition success
- Update upload history

---

## 17. Future Enhancements

### 17.1 Planned Features

**Phase 2 (Medium Priority):**

- Thumbnail upload support
- Scheduled publishing (publishAt parameter)
- Video category auto-detection
- Batch upload parallelization (within rate limits)
- Web-based configuration UI

**Phase 3 (Low Priority):**

- Video editing before upload (trimming, watermarks)
- Subtitle/caption file upload
- YouTube Analytics integration
- Multi-channel support
- Cloud storage integration (S3, Google Drive)

### 17.2 Technical Debt Considerations

**Code Quality:**

- Implement comprehensive type hints
- Increase test coverage to >80%
- Add docstrings to all public methods
- Implement code linting in CI/CD

**Architecture:**

- Consider plugin architecture for extensibility
- Refactor for dependency injection
- Implement event-driven architecture for scalability

---

## 18. Troubleshooting Guide

### 18.1 Common Issues

**Authentication Failures:**

- **Symptom**: "Invalid credentials" error
- **Solution**: Re-run OAuth flow, ensure client_secrets.json is valid

**Quota Exceeded:**

- **Symptom**: HTTP 403 with "quotaExceeded" error
- **Solution**: Wait for quota reset (midnight PT), or request quota increase

**Upload Failures:**

- **Symptom**: Upload times out or fails partway
- **Solution**: Check network connection, verify file isn't corrupted, resume upload

**Configuration Errors:**

- **Symptom**: "Config file not found" or "Invalid JSON"
- **Solution**: Verify file paths, validate JSON syntax

### 18.2 Debug Mode

**Enable Debug Logging:**

```json
{
  "logging": {
    "level": "DEBUG"
  }
}
```

**Verbose Output:**

- All API requests and responses logged
- Variable states at key checkpoints
- Detailed error stack traces

---

## 19. API Reference

### 19.1 YouTube Data API v3 Endpoints Used

**Videos.insert**

- Method: POST
- Endpoint: `https://www.googleapis.com/upload/youtube/v3/videos`
- Purpose: Upload video with metadata
- Quota Cost: 1,600 units

**Playlists.insert**

- Method: POST
- Endpoint: `https://www.googleapis.com/youtube/v3/playlists`
- Purpose: Create new playlist
- Quota Cost: 50 units

**PlaylistItems.insert**

- Method: POST
- Endpoint: `https://www.googleapis.com/youtube/v3/playlistItems`
- Purpose: Add video to playlist
- Quota Cost: 50 units

**Playlists.list**

- Method: GET
- Endpoint: `https://www.googleapis.com/youtube/v3/playlists`
- Purpose: List user's playlists
- Quota Cost: 1 unit

---

## 20. Conclusion and Design Summary

### 20.1 Architecture Highlights

**Modular Design:**

- Clear separation of concerns
- Independent, testable components
- Easy to extend and maintain

**Reliability:**

- Resumable uploads for large files
- Comprehensive error handling
- Upload state persistence
- Automatic retry with exponential backoff

**User-Friendly:**

- Simple JSON configuration
- Clear progress indicators
- Detailed logging
- Upload history tracking to prevent duplicates

**Best Practices:**

- OAuth 2.0 authentication
- Rate limiting and quota management
- Secure credential storage
- Comprehensive error handling

### 20.2 Design Principles Applied

1. **Single Responsibility**: Each component has one clear purpose
2. **Fail-Safe Defaults**: Private uploads, conservative rate limits
3. **Progressive Enhancement**: Basic features first, advanced features optional
4. **User-Centric**: Clear feedback, sensible defaults, helpful error messages
5. **Maintainability**: Clean code structure, comprehensive documentation

### 20.3 Key Design Decisions

| Decision                 | Rationale                                         |
| ------------------------ | ------------------------------------------------- |
| JSON configuration       | Easy to edit, widely supported, human-readable    |
| Sequential uploads       | Simplicity, easier to debug, respects rate limits |
| Alphabetical sorting     | Predictable, no external dependencies             |
| Upload history tracking  | Prevents duplicates, enables resume functionality |
| Resumable uploads        | Essential for large files, handles network issues |
| Default private privacy  | Safety first, user can change per video           |
| Local credential storage | No external dependencies, full user control       |

### 20.4 Success Criteria

The architecture successfully addresses all requirements:

- ✅ Sequential video uploads from folder
- ✅ Metadata configuration via JSON
- ✅ Playlist creation and management
- ✅ Default private privacy
- ✅ OAuth 2.0 authentication
- ✅ Resumable uploads for large files
- ✅ Rate limiting and quota management
- ✅ Comprehensive error handling
- ✅ Detailed logging
- ✅ User-friendly configuration

---

## Appendix A: Example CLI Output

```
YouTube Uploader v1.0.0
=======================

[INFO] Initializing system...
[INFO] Loading configuration from config/config.json
[INFO] Authenticating with YouTube API...
[INFO] Authentication successful! User: john@example.com

[INFO] Scanning videos directory: ./videos
[INFO] Found 3 videos to process

Processing Videos:
==================

[1/3] video001.mp4
  Title: Introduction to Python Programming
  Size: 150.5 MB
  Playlist: Python Tutorial Series

  Uploading... ████████████████████ 100% | 4m 37s | 150.5 MB

  ✓ Upload completed
  Video ID: dQw4w9WgXcQ
  Added to playlist: Python Tutorial Series

[2/3] video002.mp4
  Title: Advanced Python Concepts
  Size: 203.2 MB
  Playlist: Python Tutorial Series

  Uploading... ████████████████████ 100% | 6m 12s | 203.2 MB

  ✓ Upload completed
  Video ID: abc123XYZ
  Added to playlist: Python Tutorial Series

[3/3] video003.mp4
  Title: Python Best Practices
  Size: 178.9 MB
  Playlist: Python Tutorial Series

  Uploading... ████████████████████ 100% | 5m 28s | 178.9 MB

  ✓ Upload completed
  Video ID: xyz789ABC
  Added to playlist: Python Tutorial Series

Summary:
========
Total videos: 3
Successful: 3
Failed: 0
Total time: 16m 17s
Total data uploaded: 532.6 MB
Quota used: 5,250 / 10,000 units
Remaining quota: 4,750 units

All uploads completed successfully!
```

---

## Appendix B: Error Messages Reference

| Error Code  | Message                | Solution                                |
| ----------- | ---------------------- | --------------------------------------- |
| AUTH_001    | Invalid credentials    | Re-authenticate with OAuth              |
| AUTH_002    | Token expired          | Auto-refresh will be attempted          |
| UPLOAD_001  | File not found         | Verify file exists in videos directory  |
| UPLOAD_002  | Invalid video format   | Check supported formats (mp4, mov, avi) |
| UPLOAD_003  | File too large         | Max 256GB, consider compression         |
| API_001     | Quota exceeded         | Wait for reset or request increase      |
| API_002     | Rate limit exceeded    | Automatic retry with backoff            |
| CONFIG_001  | Invalid JSON           | Validate JSON syntax                    |
| CONFIG_002  | Missing required field | Check configuration schema              |
| NETWORK_001 | Connection timeout     | Check internet connection               |
| NETWORK_002 | Upload interrupted     | Will auto-resume                        |

---

**Document Version:** 1.0  
**Last Updated:** 2024-01-15  
**Status:** Architecture Design Complete - Ready for Implementation
