# Usage Guide

✅ Detailed user guide for preparing, configuring, and running the YouTube Uploader.

## Workflow overview

The typical workflow is:

- Prepare video files in [`videos/`](videos:1)
- Configure metadata in [`config/videos_metadata.json`](config/videos_metadata.json:1)
- Confirm settings in [`config/config.json`](config/config.json:1)
- Run the uploader: `python main.py`
- Monitor logs and upload history in [`config/upload_history.json`](config/upload_history.json:1)

## Video preparation guidelines

Supported formats:

- MP4 (H.264 video, AAC audio) — recommended
- MOV, MKV — supported but test compatibility

Recommended bitrate and encoding:

- Video codec: H.264
- Audio codec: AAC
- Container: .mp4

File size and duration:

- YouTube supports large files; resumable uploads allow interrupted transfers to continue.
- If you hit size limits, consider splitting or using higher quota.

File naming conventions:

- Keep relative paths in [`config/videos_metadata.json`](config/videos_metadata.json:1)
- Example:

```bash
# bash
videos/2025-11-12_my_tutorial.mp4
```

Verify file properties:

```bash
# bash
ffprobe -v error -show_entries format=duration,size -of default=noprint_wrappers=1 videos/my_video.mp4
```

## Metadata configuration examples

Minimal entry:

```json
{
  "filename": "videos/my_first_video.mp4",
  "title": "My First Video",
  "description": "Short description",
  "privacyStatus": "private"
}
```

Entry with tags and playlist:

```json
{
  "filename": "videos/tutorial.mp4",
  "title": "Python Tutorial",
  "description": "Step-by-step tutorial",
  "tags": ["python", "tutorial"],
  "playlist": "Python Tutorials",
  "privacyStatus": "unlisted"
}
```

Batch example (`config/videos_metadata.json` is an array of entries):

```json
[
  {
    "filename": "videos/a.mp4",
    "title": "A"
  },
  {
    "filename": "videos/b.mp4",
    "title": "B"
  }
]
```

Tips:

- Use absolute or relative paths consistently; relative to project root is recommended.
- If a field is missing, the uploader will use defaults from [`config/config.json`](config/config.json:1).

## Upload process (step-by-step)

When you run `python main.py` the script:

1. Loads configuration from [`config/config.json`](config/config.json:1) and [`config/videos_metadata.json`](config/videos_metadata.json:1).
2. Initializes OAuth flow via [`src/auth/authenticator.py`](src/auth/authenticator.py:1).
3. Validates each video file exists in the configured `videos_dir`.
4. For each video:
   - Starts a resumable upload session.
   - Uploads video data in chunks with retry/backoff.
   - Sets video metadata (title, description, tags, privacy).
   - Adds the video to or creates playlists via [`src/playlist/playlist_manager.py`](src/playlist/playlist_manager.py:1).
   - Records success/failure in [`config/upload_history.json`](config/upload_history.json:1).

## Monitoring uploads

Logs:

- Check `logs/` if present for detailed uploader logs.
- The script may also print progress to stdout.

Progress tracking:

- Each upload shows chunk progress and retries. Look for messages like "Uploading chunk" or "Upload complete".

Inspect upload history:

```bash
# bash
jq . config/upload_history.json
```

## Managing upload history

- `config/upload_history.json` stores mappings between local filenames and YouTube video IDs.
- Use it to avoid duplicate uploads; the uploader checks history before uploading.

Example snippet (history):

```json
{
  "videos/my_first_video.mp4": {
    "videoId": "abc123",
    "status": "uploaded",
    "uploadedAt": "2025-11-12T12:00:00Z"
  }
}
```

## Re-running failed uploads

Steps:

1. Fix the underlying issue (network, authentication, file corruption).
2. Option A: Remove or update the failed entry in [`config/upload_history.json`](config/upload_history.json:1) and re-run the uploader.
3. Option B: Edit [`config/videos_metadata.json`](config/videos_metadata.json:1) to re-include the video and run with `concurrency: 1`.

Resume behavior:

- Resumable uploads will continue from the last acknowledged byte when the session is intact.
- If the session token is lost, the uploader will start a new session and may re-upload parts.

## Playlist management tips

- If you provide a `playlist` name in the metadata, the uploader will try to find an existing playlist and create it if missing.
- To ensure order, set metadata playlist entries in the desired sequence before running batch uploads.
- For advanced playlist operations review [`src/playlist/playlist_manager.py`](src/playlist/playlist_manager.py:1).

## Advanced usage scenarios

- Parallel uploads: increase `concurrency` in [`config/config.json`](config/config.json:1) but watch quotas.
- Automated CI/CD: place sanitized `config/token.json` in a secure store and inject at runtime (do NOT commit tokens).
- Scheduled uploads: combine with cron or CI pipelines and use `videos/` and `config/videos_metadata.json` as the source of truth.

## Troubleshooting common issues

- Authentication errors:

  - Ensure `config/client_secrets.json` is the file downloaded from Google Cloud Console.
  - If token is invalid, delete `config/token.json` and reauthenticate.

- Quota errors:

  - Reduce concurrency or request higher quotas in Google Cloud Console.

- Slow uploads:
  - Check network connectivity and consider chunk size tuning (see `src/uploader/video_uploader.py`).

Security warnings:

- ⚠️ Never commit `config/client_secrets.json` or `config/token.json` to a public repository.
- ⚠️ Tokens grant upload access — treat them like passwords.

## Examples

Run a single upload (example):

```bash
# bash
python main.py
```

View upload history:

```bash
# bash
cat config/upload_history.json | jq .
```

## Helpful links

- Main docs: [`README.md`](README.md:1)
- Setup: [`SETUP.md`](SETUP.md:1)
- Architecture: [`ARCHITECTURE.md`](ARCHITECTURE.md:1)

End.
