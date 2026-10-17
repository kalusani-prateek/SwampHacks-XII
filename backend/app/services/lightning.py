"""Lightning near job sites from NOAA's GOES Geostationary Lightning Mapper (GLM).

NOAA publishes a GLM file (product GLM-L2-LCFA, NetCDF4) every 20 seconds in
its public AWS bucket. Each poll reads the files that arrived since the last
poll, pulls out flash locations with pyfive (a pure-Python HDF5 reader) and
keeps flashes within 30 miles of a site. GLM sees all lightning (in-cloud and
cloud-to-ground) to about 8 km, which suits the 10-mile stop-work rule.
Bandwidth: ~1 MB per minute per satellite.
"""
import io
import logging
import re
from datetime import datetime, timedelta, timezone

import numpy as np
import pyfive

from .http import get

log = logging.getLogger(__name__)
BUCKET = "https://noaa-{satellite}.s3.amazonaws.com"
PRODUCT = "GLM-L2-LCFA"
STORE_RADIUS_MILES = 30
MAX_FILES_PER_POLL = 12  # 4 minutes of data; older backlog is skipped
_KEY = re.compile(r"<Key>([^<]+)</Key>")


class GlmPoller:
    """Remembers the newest file processed per satellite between polls."""

    def __init__(self):
        self.last_key = {}

    def new_keys(self, satellite, now):
        """Keys newer than the last one processed (only the last minute on the first poll)."""
        hours = [now - timedelta(hours=1), now] if now.minute < 5 else [now]
        keys = []
        for hour in hours:
            prefix = f"{PRODUCT}/{hour:%Y}/{hour.timetuple().tm_yday:03d}/{hour:%H}/"
            response = get(BUCKET.format(satellite=satellite), params={"list-type": 2, "prefix": prefix}, timeout=30)
            response.raise_for_status()
            keys.extend(_KEY.findall(response.text))
        keys.sort()
        last = self.last_key.get(satellite)
        fresh = [k for k in keys if last is None or k > last]
        if last is None:
            fresh = fresh[-3:]
        return fresh[-MAX_FILES_PER_POLL:]

    def poll(self, sites, satellites):
        """New flashes near sites: [(site_id, observed_at naive UTC, distance miles)]."""
        now = datetime.now(timezone.utc)
        flashes = []
        for satellite in satellites:
            for key in self.new_keys(satellite, now):
                response = get(f"{BUCKET.format(satellite=satellite)}/{key}", timeout=60)
                response.raise_for_status()
                flashes.extend(read_flashes(response.content))
                self.last_key[satellite] = key
        return match_sites(sites, flashes)


def read_flashes(data):
    """[(lat, lon, time)] from one GLM file's bytes."""
    f = pyfive.File(io.BytesIO(data))
    lat = np.asarray(f["flash_lat"][()], dtype=float)
    lon = np.asarray(f["flash_lon"][()], dtype=float)
    offsets = f["flash_time_offset_of_first_event"]
    raw = np.asarray(offsets[()]).astype(np.uint16)  # stored as int16 with _Unsigned = "true"
    scale = float(np.ravel(offsets.attrs.get("scale_factor", [1.0]))[0])
    add = float(np.ravel(offsets.attrs.get("add_offset", [0.0]))[0])
    units = offsets.attrs.get("units", b"")
    units = units.decode() if isinstance(units, bytes) else str(units)
    base = datetime.strptime(units.replace("seconds since ", "")[:19], "%Y-%m-%d %H:%M:%S")
    seconds = raw * scale + add
    return [(la, lo, base + timedelta(seconds=float(s))) for la, lo, s in zip(lat, lon, seconds)]


def match_sites(sites, flashes):
    """Flashes within STORE_RADIUS_MILES of each site."""
    if not flashes or not sites:
        return []
    arr = np.array([(la, lo) for la, lo, _ in flashes])
    times = [t for _, _, t in flashes]
    # Rough bounding box around all sites first (GLM covers the whole hemisphere).
    lats, lngs = [s.lat for s in sites], [s.lng for s in sites]
    box = (arr[:, 0] > min(lats) - 1) & (arr[:, 0] < max(lats) + 1) & (arr[:, 1] > min(lngs) - 1) & (arr[:, 1] < max(lngs) + 1)
    idx = np.nonzero(box)[0]
    if idx.size == 0:
        return []
    flash = np.radians(arr[idx])
    matches = []
    for site in sites:
        lat, lng = np.radians(site.lat), np.radians(site.lng)
        a = np.sin((flash[:, 0] - lat) / 2) ** 2 + np.cos(lat) * np.cos(flash[:, 0]) * np.sin((flash[:, 1] - lng) / 2) ** 2
        miles = 3958.8 * 2 * np.arcsin(np.sqrt(a))
        for j in np.nonzero(miles <= STORE_RADIUS_MILES)[0]:
            matches.append((site.id, times[idx[j]], round(float(miles[j]), 1)))
    return matches
