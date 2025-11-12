# YouTube Uploader

✅ Lightweight, configurable Python tool to batch-upload videos to YouTube using the YouTube Data API v3.

## Features

- ✅ OAuth 2.0 authentication
- ✅ Resumable uploads (retries and resume on interruption)
- ✅ Playlist management (create/update playlists)
- ✅ Config-driven metadata and batch uploads
- ✅ Upload history and idempotency
- ✅ Rate limiting and exponential backoff

## Prerequisites

- Python 3.8 or newer
- A Google Cloud Console account and a Google project with YouTube Data API v3 enabled
- A YouTube channel associated with the Google account you will upload from

## Installation

1. Clone the repo:

```bash
git clone https://github.com/yourname/ytube.git
cd ytube
```

2. Install dependencies:

```bash
python -m pip install -r requirements.txt
```

3. Set up OAuth credentials (see the Setup guide in [`SETUP.md`](SETUP.md:1)).

## Configuration

The uploader uses two primary configuration files:

- Metadata and upload settings: [`config/config.json`](config/config.json:1)
- Per-video metadata list: [`config/videos_metadata.json`](config/videos_metadata.json:1)

🔧 Example `config/config.json` (short):

```json
{
  "client_secrets_path": "config/client_secrets.json",
  "token_path": "config/token.json",
  "videos_dir": "videos",
  "concurrency": 1,
  "default_privacy": "private"
}
```

🔧 Example `config/videos_metadata.json` (short):

```json
[
  {
    "filename": "videos/my_first_video.mp4",
    "title": "My First Upload",
    "description": "Description here",
    "tags": ["example", "upload"],
    "playlist": "My Playlist",
    "privacyStatus": "public"
  }
]
```

### How to obtain OAuth credentials

Follow the full step-by-step instructions in [`SETUP.md`](SETUP.md:1). Briefly:

1. Create a Google Cloud project.
2. Enable YouTube Data API v3.
3. Create OAuth 2.0 Client ID (Desktop app).
4. Download the JSON and place it as `config/client_secrets.json`.

⚠️ Keep your OAuth client secret and token files private — do NOT commit them to source control.

## Usage

- Basic run:

```bash
python main.py
```

- First run will open a browser window (or provide a URL) to authorize the application. After authorization the script will store a token at the path set in [`config/config.json`](config/config.json:1).

### Command-line arguments

The script reads settings from [`config/config.json`](config/config.json:1). If the project includes CLI args, see [`main.py`](main.py:1) for details.

### What happens during upload

1. The script loads configuration and metadata.
2. Authenticates using OAuth; obtains/refreshes tokens.
3. Validates video files exist under the configured `videos_dir`.
4. For each video entry, performs a resumable upload, sets metadata, and adds to playlists as configured.
5. Records upload result to [`config/upload_history.json`](config/upload_history.json:1).

## Supported video formats

The uploader recognizes common video file extensions. Supported formats include:

- .mp4, .avi, .mov, .wmv, .flv, .webm, .mkv, **.ts** (MPEG transport stream), .mpeg, .mpg, .m4v, .3gp

Note: MPEG transport stream files (`.ts`) are now explicitly supported by the uploader — place `.ts` files in your configured `videos_dir` and they will be detected and validated prior to upload.

## Project structure

- [`main.py`](main.py:1) — entry point
- [`src/auth/authenticator.py`](src/auth/authenticator.py:1) — OAuth handling
- [`src/uploader/video_uploader.py`](src/uploader/video_uploader.py:1) — upload logic
- [`src/playlist/playlist_manager.py`](src/playlist/playlist_manager.py:1) — playlist helpers
- [`config/`](config:1) — configuration and sample files

See [`ARCHITECTURE.md`](ARCHITECTURE.md:1) for a detailed architecture overview.

## Troubleshooting

- ⚠️ "invalid_grant" on token exchange: ensure system clock is correct and client secrets match.
- ⚠️ Permission errors: verify the OAuth client has the correct scopes and the YouTube Data API is enabled.
- ⚠️ Quota exceeded: check Google Cloud Console quota usage (see "YouTube API Quota" below).
- ✅ Uploads fail or stall: ensure network is stable; resumable uploads will retry automatically.

## YouTube API Quota

- Each operation consumes quota units. Uploads and certain metadata updates are expensive.
- Monitor quotas in Google Cloud Console → APIs & Services → Dashboard → YouTube Data API.
- Implement conservative concurrency in [`config/config.json`](config/config.json:1) if you hit quota limits.

## Security & Privacy

- ⚠️ Never commit `config/client_secrets.json` or `config/token.json` to version control.
- Add these to `.gitignore` (see existing [`config/client_secrets.json.example`](config/client_secrets.json.example:1)).

## License

This project is released under the MIT License. See LICENSE file (suggested).

---

For detailed setup instructions, see [`SETUP.md`](SETUP.md:1). For usage patterns and advanced workflows, see [`USAGE.md`](USAGE.md:1).
