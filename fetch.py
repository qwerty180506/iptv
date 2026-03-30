#!/usr/bin/env python3
"""
fetch.py — Main entry point.

Runs all available scrapers, then generates:
  - events.m3u8 : live events only
"""
import asyncio
from pathlib import Path

from playwright.async_api import async_playwright

from scrapers import timstreams

# ── Add more scrapers here as you restore them ──────────────────────────────
# from scrapers import cdnlivetv, embedhd, ...
# ────────────────────────────────────────────────────────────────────────────

from scrapers.utils import get_logger, network

log = get_logger(__name__)

EVENTS_FILE = Path(__file__).parent / "events.m3u8"

TVG_URL = (
    'url-tvg="https://raw.githubusercontent.com/'
    'YOUR_USERNAME/YOUR_REPO/refs/heads/main/TV.xml"'
)


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

    async with async_playwright() as p:
        ext_browser = None
        hdl_browser = None
        try:
            ext_browser = await network.browser(p, external=True)
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
            if ext_browser:
                await ext_browser.close()
            if hdl_browser:
                await hdl_browser.close()
            await network.client.aclose()

    additions = (
        timstreams.urls
        # | cdnlivetv.urls
        # | shark.urls
    )

    if not additions:
        log.warning("No live events collected — events.m3u8 will be empty")

    live_events: list[str] = []

    for i, (event, info) in enumerate(sorted(additions.items()), start=1):
        live_events.extend(
            build_entry(event, info, chno=i, ua=network.UA)
        )

    EVENTS_FILE.write_text(
        f"#EXTM3U {TVG_URL}\n" + "\n".join(live_events),
        encoding="utf-8",
    )

    log.info(f"Events saved to {EVENTS_FILE.resolve()} ({len(additions)} event(s))")


if __name__ == "__main__":
    asyncio.run(main())

    for hndlr in log.handlers:
        hndlr.flush()
        hndlr.stream.write("\n")
