#!/usr/bin/env python3
"""
fetch.py — Main entry point.

Runs all available scrapers, then generates:
  - events.m3u8  : live events only
  - TV.m3u8      : base channels + live events (if base.m3u8 exists)
"""
import asyncio
import re
from pathlib import Path

from playwright.async_api import async_playwright

from scrapers import timstreams

# ── Add more scrapers here as you restore them ──────────────────────────────
# from scrapers import cdnlivetv, embedhd, ...
# ────────────────────────────────────────────────────────────────────────────

from scrapers.utils import get_logger, network

log = get_logger(__name__)

BASE_FILE = Path(__file__).parent / "base.m3u8"
EVENTS_FILE = Path(__file__).parent / "events.m3u8"
COMBINED_FILE = Path(__file__).parent / "TV.m3u8"

TVG_URL = (
    'url-tvg="https://raw.githubusercontent.com/'
    'YOUR_USERNAME/YOUR_REPO/refs/heads/main/TV.xml"'
)


def load_base() -> tuple[list[str], int]:
    """Load base.m3u8 and find the highest channel number in it."""
    if not BASE_FILE.exists():
        log.warning("base.m3u8 not found — combined TV.m3u8 will be skipped")
        return [], 0

    log.info("Fetching base M3U8")
    data = BASE_FILE.read_text(encoding="utf-8")
    pattern = re.compile(r'tvg-chno="(\d+)"')
    last_chnl_num = max(map(int, pattern.findall(data)), default=0)
    return data.splitlines(), last_chnl_num


def build_entry(
    event: str,
    info: dict,
    chno: int,
    ua: str,
) -> list[str]:
    """Return the EXTINF + VLC option lines for one event."""
    extinf = (
        f'#EXTINF:-1 tvg-chno="{chno}" tvg-id="{info["id"]}" '
        f'tvg-name="{event}" tvg-logo="{info["logo"]}" '
        f'group-title="Live Events",{event}'
    )
    vlc = [
        f'#EXTVLCOPT:http-referrer={info["base"]}',
        f'#EXTVLCOPT:http-origin={info["base"]}',
        f'#EXTVLCOPT:http-user-agent={info.get("UA", ua)}',
        info["url"],
    ]
    return ["\n" + extinf, *vlc]


async def main() -> None:
    log.info(f"{'=' * 10} Scraper Started {'=' * 10}")

    base_m3u8, tvg_chno = load_base()

    async with async_playwright() as p:
        try:
            # external browser (CDP) — used by timstreams
            ext_browser = await network.browser(p, external=True)

            # headless Firefox — used by playwright-based scrapers
            hdl_browser = await network.browser(p)

            pw_tasks = [
                asyncio.create_task(timstreams.scrape(ext_browser)),
                # asyncio.create_task(cdnlivetv.scrape(hdl_browser)),
                # asyncio.create_task(embedhd.scrape(hdl_browser)),
            ]

            httpx_tasks: list = [
                # asyncio.create_task(shark.scrape()),
                # asyncio.create_task(tvapp.scrape()),
            ]

            await asyncio.gather(*(pw_tasks + httpx_tasks))

        finally:
            await ext_browser.close()
            await hdl_browser.close()
            await network.client.aclose()

    # ── Merge all scraper url dicts ──────────────────────────────────────────
    additions = (
        timstreams.urls
        # | cdnlivetv.urls
        # | embedhd.urls
        # | shark.urls
    )

    if not additions:
        log.warning("No live events collected — M3U8 files will be empty")

    live_events: list[str] = []
    combined_channels: list[str] = []

    for i, (event, info) in enumerate(sorted(additions.items()), start=1):
        combined_channels.extend(
            build_entry(event, info, chno=tvg_chno + i, ua=network.UA)
        )
        live_events.extend(
            build_entry(event, info, chno=i, ua=network.UA)
        )

    # ── Write events.m3u8 ───────────────────────────────────────────────────
    EVENTS_FILE.write_text(
        f"#EXTM3U {TVG_URL}\n" + "\n".join(live_events),
        encoding="utf-8",
    )
    log.info(f"Events saved to {EVENTS_FILE.resolve()} ({len(additions)} event(s))")

    # ── Write TV.m3u8 (base + events) ───────────────────────────────────────
    if base_m3u8:
        COMBINED_FILE.write_text(
            "\n".join(base_m3u8 + combined_channels),
            encoding="utf-8",
        )
        log.info(f"Base + Events saved to {COMBINED_FILE.resolve()}")
    else:
        log.info("Skipping TV.m3u8 (no base.m3u8 found)")


if __name__ == "__main__":
    asyncio.run(main())

    for hndlr in log.handlers:
        hndlr.flush()
        hndlr.stream.write("\n")
