# Setup Guide

✅ This document walks you step-by-step through getting the YouTube Uploader ready to run.

---

## 1) Google Cloud Console — create credentials (step-by-step)

1. Sign in to Google Cloud Console: https://console.cloud.google.com
2. Create a new project:
   - Console → Select Project → New Project → give it a name (e.g., "yt-uploader")
3. Enable the YouTube Data API v3:
   - Navigation menu → APIs & Services → Library → search "YouTube Data API v3" → Enable
4. Create OAuth 2.0 credentials:
   - APIs & Services → Credentials → Create Credentials → OAuth client ID
   - Application type: Desktop app
   - Name: "YT Uploader - Desktop"
   - Click Create → Download the JSON
   - Rename the downloaded file to `client_secrets.json`
   - Place it in the repository: `config/client_secrets.json`

Example:

```bash
# from project root
cp ~/Downloads/client_secret_*.json config/client_secrets.json
```

⚠️ Security warning: never commit `config/client_secrets.json` to source control. Add it to `.gitignore` if not already present.

Tip: if you don't see "OAuth consent screen" steps, follow the guided flow to configure the consent screen (choose External if you're not part of an organization). For desktop apps you generally only need a name and email.

---

## 2) Directory structure setup

Create folders the uploader expects (videos, data, logs). From project root:

```bash
# bash
mkdir -p videos data logs
```

Recommended layout (project root):

- [`config/config.json`](config/config.json:1) — main settings
- [`config/videos_metadata.json`](config/videos_metadata.json:1) — per-video metadata
- `videos/` — place video files here (e.g., `videos/my_video.mp4`)
- `data/` — optional: for auxiliary files or exported metadata
- `logs/` — uploader logs

Example: place your video

```bash
cp /path/to/my_video.mp4 videos/my_video.mp4
```

---

## 3) Install Python and dependencies

Prerequisite: Python 3.8+

Create a virtual environment (recommended) and install dependencies:

```bash
# bash
python -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

If your OS uses `python3` as the binary, replace `python` with `python3`.

---

## 4) Configure OAuth and token paths

Open [`config/config.json`](config/config.json:1) and confirm or edit these keys:

- `client_secrets_path` — default `config/client_secrets.json`
- `token_path` — where OAuth tokens are stored (e.g., `config/token.json`)
- `videos_dir` — default `videos`
- `concurrency` — number of simultaneous uploads (use 1 to avoid quota issues)
- `default_privacy` — `"private" | "unlisted" | "public"`

Example snippet in [`config/config.json`](config/config.json:1):

```json
{
  "client_secrets_path": "config/client_secrets.json",
  "token_path": "config/token.json",
  "videos_dir": "videos",
  "concurrency": 1,
  "default_privacy": "private"
}
```

If you used the example client secrets file, copy it and fill values:

```bash
cp config/client_secrets.json.example config/client_secrets.json
# edit config/client_secrets.json with the downloaded credentials
```

⚠️ Warning: Protect your token file `config/token.json` as it grants upload access to your account.

---

## 5) Configure videos metadata

Edit [`config/videos_metadata.json`](config/videos_metadata.json:1). Each entry should minimally contain:

- `filename` (relative path, e.g., `videos/my_video.mp4`)
- `title`
- `description`
- optional: `tags`, `playlist`, `privacyStatus`

Example:

```json
[
  {
    "filename": "videos/my_first_video.mp4",
    "title": "My First Video",
    "description": "Short description here",
    "tags": ["tutorial", "example"],
    "privacyStatus": "private"
  }
]
```

---

## 6) Add sensitive files to .gitignore

Ensure these entries exist in `.gitignore`:

```
# OAuth and tokens
/config/client_secrets.json
/config/token.json
```

If `.gitignore` doesn't exist or needs updating, add the lines above.

---

## 7) Test the installation (first run / authentication flow)

From project root, run:

```bash
# bash
python main.py
```

What to expect on first run:

- The script reads `config/config.json` and `config/videos_metadata.json`.
- If `config/token.json` is missing or expired, it will prompt you to authenticate:
  - A browser window or a URL will open.
  - Sign in with the Google account that owns the target YouTube channel.
  - Approve requested scopes (upload, manage playlists, etc.).
  - The script stores a token at the `token_path` configured.

If everything is set up correctly the script will start processing videos from `videos/`.

Troubleshooting quick checks:

- If the browser does not open, copy the provided URL into a browser manually.
- If you receive `invalid_grant`, check system clock and ensure client ID/secret are correct.

---

## 8) Logs and verification

- Check `logs/` for upload logs (if the project writes logs there).
- Check `config/upload_history.json` (if present) for recorded upload IDs and outcomes.

Example: view last lines of a log

```bash
# bash
tail -n 200 logs/uploader.log
```

---

## 9) Security best practices

- ✅ Do not commit `config/client_secrets.json` or `config/token.json` to git.
- ✅ Limit access to the Google Cloud project and rotate credentials if compromised.
- ✅ Use least privilege: create OAuth credentials only with required scopes.
- ✅ When running on shared machines, remove `config/token.json` after use or use environment isolation.
- 🔒 Consider using a secrets manager in production (GCP Secret Manager, AWS Secrets Manager).

---

## 10) Next steps

- Read the main user guide: [`README.md`](README.md:1)
- Read the usage patterns and examples: [`USAGE.md`](USAGE.md:1)
- Review architecture and code references: [`ARCHITECTURE.md`](ARCHITECTURE.md:1) and main source files like [`main.py`](main.py:1), [`src/auth/authenticator.py`](src/auth/authenticator.py:1), [`src/uploader/video_uploader.py`](src/uploader/video_uploader.py:1)

---

End of setup. ✅
