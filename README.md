# NDL STUDIOS

## Telugu Linear Streaming Channel Prototype

NDL STUDIOS is a Telugu entertainment-focused **linear streaming / FAST-style prototype**. It simulates a scheduled channel using authorized test media, a programme guide, audience polling and a small Flask administration layer.

> **Rights note:** This project does not provide or download pirated movies. Only original, public-domain, licensed, or otherwise verified content should be published.

## Features

- TV-style NDL STUDIOS live channel interface
- Simulated-linear playout based on programme durations
- Current programme / next programme / countdown
- EPG-style programme guide
- Audience poll with SQLite vote storage
- Basic protected admin panel
- Programme add/edit/delete controls
- Drag-and-drop programme reordering
- Content library metadata with rights-status tracking
- Admin content-record creation with rights validation
- Health endpoint
- SEO basics: description, Open Graph, robots.txt, sitemap.xml
- Responsive desktop/mobile UI
- Gunicorn + Render-ready configuration

## Technology

- Python + Flask
- HTML / CSS / JavaScript
- SQLite for prototype poll data
- JSON for lightweight channel/programme configuration
- Gunicorn for deployment

## Local setup — Windows / VS Code

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
$env:SECRET_KEY="change-this-local-secret"
$env:ADMIN_PASSWORD="change-this-admin-password"
python app.py
```

Open **http://127.0.0.1:5000**.

For Command Prompt, use `set SECRET_KEY=...` and `set ADMIN_PASSWORD=...` before `python app.py`.

The included `run_windows.bat` and `run_windows.ps1` scripts automate the basic setup.

## Admin

Open **http://127.0.0.1:5000/admin/login**.

The password comes from `ADMIN_PASSWORD`. If it is not set, the prototype falls back to `admin` for local development only. **Set a real password before any public deployment.**

## Project structure

```text
NDL_STUDIOS_Linear_Streaming_Channel/
├── app.py
├── requirements.txt
├── Procfile
├── render.yaml
├── .gitignore
├── .env.example
├── README.md
├── data/
│   ├── channel.json
│   ├── content.json
│   └── ndl_studios.db          # generated locally; ignored by Git
├── templates/
│   ├── index.html
│   ├── admin.html
│   ├── admin_login.html
│   └── sitemap.xml
└── static/
    ├── css/style.css
    ├── js/app.js
    └── media/ndl_broadcast_test.mp4
```

## How the simulated-live scheduler works

The server treats the programme list as a repeating linear schedule. Each programme has `duration_seconds`. The API calculates the current position in the cycle from server time, so refreshing the page does not reset the channel to programme 1.

This is intentionally a **simulation**, not a real broadcast/encoder system.

## Render deployment

1. Push this project to GitHub.
2. In Render, create a new **Web Service** from the repository.
3. Use the Python runtime.
4. Build command: `pip install -r requirements.txt`
5. Start command: `gunicorn app:app`
6. Add environment variables:
   - `SECRET_KEY` — a long random secret
   - `ADMIN_PASSWORD` — a strong admin password
   - `FLASK_DEBUG=0`
7. Deploy and open the Render-provided URL.

Do not hardcode a Render URL in the application.

### Free-tier limitation

A free web service is suitable for a **showcase/demo**, not for dependable 24/7 video broadcasting. Local SQLite and local filesystem writes are also not durable storage on ephemeral hosting. For a future public platform, move operational data to PostgreSQL and media to object storage/CDN or an external streaming service.

## Streaming architecture roadmap

```text
NDL STUDIOS Web App
        │
        ├── EPG / programme metadata
        ├── polls / analytics
        ├── admin / rights tracking
        │
        └── Live Player
              │
              ├── YouTube Live (prototype option)
              └── HLS + streaming server + CDN (future)
```

Flask should remain the application/control layer rather than becoming a large-scale video delivery server.

## Content and rights policy

Every programme should have a clear rights status before public playback. Suggested statuses:

- `ORIGINAL`
- `PUBLIC DOMAIN`
- `LICENSED`
- `VERIFIED`
- `PENDING REVIEW`
- `NOT CLEARED`

Being able to find a movie online does **not** establish NDL STUDIOS has permission to rebroadcast it.

## Future roadmap

1. Localhost pilot
2. Portfolio/showcase polish
3. Free public deployment
4. YouTube Live / HLS prototype
5. PostgreSQL + cloud media + CDN
6. Advertisement and sponsor management
7. Multi-channel EPG and analytics
8. Commercial licensing/distribution exploration

## Author

Ala Ganesh — NDL STUDIOS prototype
