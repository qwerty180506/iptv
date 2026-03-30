# iptv-scraper

Scrapes live sports streams and generates M3U8 playlists, updated hourly via GitHub Actions.

## Output files

| File | Description |
|---|---|
| `events.m3u8` | Live events only (numbered from 1) |
| `TV.m3u8` | Your `base.m3u8` channels + live events appended |

## Setup

### 1. Clone & install

```bash
git clone https://github.com/YOUR_USERNAME/YOUR_REPO.git
cd iptv-scraper

python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate

pip install -e ".[dev]"
playwright install firefox chromium --with-deps
```

### 2. Add your base channel list (optional)

Place your existing M3U8 as `base.m3u8` in the repo root. The scraper will
append live events to it and write the result to `TV.m3u8`. If `base.m3u8` is
absent, only `events.m3u8` is written.

### 3. Run locally

```bash
# Start a Chromium CDP instance first (used by timstreams scraper)
chromium --remote-debugging-port=9222 --headless=new --no-sandbox &

# Then run
python fetch.py
```

### 4. GitHub Actions (automatic hourly updates)

1. Push this repo to GitHub.
2. Go to **Settings → Actions → General** and set *Workflow permissions* to **Read and write**.
3. The workflow in `.github/workflows/scrape.yml` runs every hour, commits the
   updated `.m3u8` files, and pushes them back to `main`.

You can then point your IPTV player at the **raw GitHub URL** of `events.m3u8`:

```
https://raw.githubusercontent.com/YOUR_USERNAME/YOUR_REPO/main/events.m3u8
```

## Adding more scrapers

1. Drop your scraper module into `scrapers/` (it needs a top-level `urls` dict and a `scrape()` coroutine).
2. Import it in `fetch.py` and add it to `pw_tasks` / `httpx_tasks`.
3. Merge its `urls` into `additions`.

## Project layout

```
iptv-scraper/
├── fetch.py                  # entry point
├── base.m3u8                 # (optional) your base channel list
├── events.m3u8               # generated — live events
├── TV.m3u8                   # generated — base + live events
├── caches/                   # JSON cache files (committed to speed up CI)
├── logs/                     # rotating log files (git-ignored)
├── scrapers/
│   ├── __init__.py
│   ├── timstreams.py
│   └── utils/
│       ├── __init__.py
│       ├── caching.py
│       ├── config.py
│       ├── leagues.json
│       ├── logger.py
│       ├── webwork.py
│       ├── stealth.js        # add your own
│       └── easylist.txt      # add your own
├── .github/
│   └── workflows/
│       └── scrape.yml
└── pyproject.toml
```
