#!/usr/bin/env python3
"""ASTRA space-weather collector. Poll 5 NASA/NOAA feeds every 30s.

Install: python3 -m pip install requests
Run: NASA_API_KEY='your-key' python3 astra_space_weather.py
Snapshot: astra_space_weather.json
"""
import json
import logging
import os
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

import requests

INTERVAL_SECONDS = 30
OUTPUT_FILE = Path(os.getenv('ASTRA_WEATHER_FILE', 'astra_space_weather.json'))


def hide_key(text):
    """Error messages contain the full web address, which includes the API key. Hide it."""
    text = str(text)
    return text.replace(NASA_KEY, '***') if NASA_KEY and NASA_KEY != 'DEMO_KEY' else text


def load_nasa_key():
    """Key order: NASA_API_KEY environment variable, then nasa_api_key.txt next to this
    script, then the shared DEMO_KEY. Keeping the key in its own file keeps it out of the
    code, so you can share or submit the code without sharing the key."""
    key = os.getenv('NASA_API_KEY')
    if key:
        return key.strip()
    try:
        key = Path(__file__).with_name('nasa_api_key.txt').read_text(encoding='utf-8').strip()
    except OSError:
        key = ''
    return key or 'DEMO_KEY'


NASA_KEY = load_nasa_key()
# How often to ask NASA's DONKI for flares and CMEs (2 requests per round).
#  - With a personal key (api.nasa.gov): 1,000 requests per hour allowed. Every 30 seconds
#    (once per round, about 240 per hour) is the fastest that is useful, since the data does
#    not change faster than that. Going faster would not give fresher data.
#  - With the shared DEMO_KEY: only 30 per hour and 50 per day are allowed, so every 4.5 minutes
#    (about 28 per hour). That uses up the 50-per-day limit in about 2 hours.
# The NOAA feeds need no key, so they stay on the 30-second INTERVAL_SECONDS above.
NASA_FEED_SECONDS = 270 if NASA_KEY == 'DEMO_KEY' else INTERVAL_SECONDS
FEED_INTERVALS = {'solar_flares': NASA_FEED_SECONDS, 'cmes': NASA_FEED_SECONDS}
SESSION = requests.Session()
SESSION.headers.update({'User-Agent': 'ASTRA-SpaceApps-2026/1.0'})

FEEDS = {
    'proton_flux': 'https://services.swpc.noaa.gov/json/goes/primary/integral-protons-plot-6-hour.json',
    'solar_flares': 'https://api.nasa.gov/DONKI/FLR',
    'cmes': 'https://api.nasa.gov/DONKI/CME',
    'solar_wind': 'https://services.swpc.noaa.gov/json/rtsw/rtsw_wind_1m.json',
    'geomagnetic_kp': 'https://services.swpc.noaa.gov/products/noaa-planetary-k-index.json',
}


def utc_now():
    return datetime.now(timezone.utc).isoformat(timespec='seconds')


def feed_is_empty(name, resp):
    return name in ('solar_flares', 'cmes') and not resp.text.strip()


def fetch(name):
    params = None
    if name in ('solar_flares', 'cmes'):
        today = datetime.now(timezone.utc).date()
        params = {
            'startDate': (today - timedelta(days=7)).isoformat(),
            'endDate': today.isoformat(),
            'api_key': NASA_KEY,
        }
    resp = SESSION.get(FEEDS[name], params=params, timeout=12)
    resp.raise_for_status()
    if feed_is_empty(name, resp):
        return []            # NASA DONKI sends an empty reply (not "[]") when there were no events
    data = resp.json()
    if not isinstance(data, list):
        raise ValueError(f'Unexpected {name} payload: expected JSON list')
    return data


def most_recent(feed, data):
    """Keep raw responses, and expose a useful last record for the UI.

    NOAA Kp is a header row followed by value rows; other feeds return object lists.
    """
    if feed == 'geomagnetic_kp':
        if data and isinstance(data[-1], dict):          # newer NOAA format: a list of records
            return data[-1]
        if len(data) < 2 or not isinstance(data[0], list):
            return None
        headers = data[0]                                # older format: a header row, then rows
        return dict(zip(headers, data[-1]))
    return data[-1] if data else None


def load_previous():
    try:
        return json.loads(OUTPUT_FILE.read_text(encoding='utf-8'))['feeds']
    except (FileNotFoundError, ValueError, KeyError, OSError):
        return {}


def write_snapshot(feeds):
    record = {'polled_at_utc': utc_now(), 'poll_interval_seconds': INTERVAL_SECONDS, 'feeds': feeds}
    temp = OUTPUT_FILE.with_suffix(OUTPUT_FILE.suffix + '.tmp')
    temp.write_text(json.dumps(record, indent=2), encoding='utf-8')
    temp.replace(OUTPUT_FILE)


def main():
    logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')
    if NASA_KEY == 'DEMO_KEY':
        logging.warning('No personal NASA key found; using rate-limited public DEMO_KEY')
    else:
        logging.info('Using personal NASA API key (%d characters)', len(NASA_KEY))
    feeds = load_previous()
    last_fetch = {}
    logging.info('ASTRA collector started. Snapshot: %s', OUTPUT_FILE.resolve())
    try:
        while True:
            start = time.monotonic()
            for name in FEEDS:
                if time.monotonic() - last_fetch.get(name, -1e9) < FEED_INTERVALS.get(name, INTERVAL_SECONDS):
                    continue
                last_fetch[name] = time.monotonic()
                previous = feeds.get(name, {})
                try:
                    data = fetch(name)
                    feeds[name] = {
                        'status': 'ok',
                        'last_success_utc': utc_now(),
                        'record_count': len(data) - 1 if name == 'geomagnetic_kp' and data and isinstance(data[0], list) else len(data),
                        'latest': most_recent(name, data),
                        'data': data,
                        'error': None,
                    }
                    logging.info('%-17s OK records=%s', name, feeds[name]['record_count'])
                except (requests.RequestException, ValueError) as exc:
                    feeds[name] = {**previous, 'status': 'stale' if 'data' in previous else 'error', 'error': hide_key(exc)}
                    logging.warning('%-17s %s', name, hide_key(exc))
            write_snapshot(feeds)
            time.sleep(max(0, INTERVAL_SECONDS - (time.monotonic() - start)))
    except KeyboardInterrupt:
        logging.info('Collector stopped.')
    finally:
        SESSION.close()


if __name__ == '__main__':
    main()
