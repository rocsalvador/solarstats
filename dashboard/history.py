"""Load historic inverter data from the logger JSON database files."""
import datetime
import glob
import json
import os

from utils.log import log


class HistoryStore:
    """Read and aggregate historic data from logger daily JSON files.

    The logger writes one file per day named ``{db_prefix}_YYYY-MM-DD.json``,
    each containing an ``instant`` list of timestamped register readings. This
    class merges every matching file into a single time-ordered series and
    aggregates it into fixed-size buckets so long timespans stay cheap to plot.
    """

    FIELDS = ("soc", "load_power", "pv1_power", "pv2_power")

    # (maximum span, bucket size) used to downsample the series for plotting.
    BUCKETS = (
        (datetime.timedelta(days=2), datetime.timedelta(minutes=15)),
        (datetime.timedelta(days=8), datetime.timedelta(hours=1)),
        (datetime.timedelta(days=32), datetime.timedelta(hours=6)),
        (datetime.timedelta(days=400), datetime.timedelta(days=1)),
    )
    DEFAULT_BUCKET = datetime.timedelta(days=1)

    # Intervals longer than this are skipped when integrating energy so that
    # logging downtime is not counted as consumed/produced energy.
    ENERGY_MAX_GAP = datetime.timedelta(hours=1)

    def __init__(self, db_prefix: str = "solardb"):
        self.db_prefix = db_prefix
        self._records = []
        self._signature = None

    def _db_files(self) -> list[str]:
        """Return the sorted list of logger database files for this prefix."""
        return sorted(glob.glob(f"{self.db_prefix}_*.json"))

    def _current_signature(self) -> tuple:
        """Return a fingerprint of the database files used to detect changes."""
        signature = []
        for path in self._db_files():
            try:
                signature.append((path, os.path.getmtime(path)))
            except OSError:
                continue
        return tuple(signature)

    def _load(self) -> list[tuple]:
        """Load and cache all records, reloading only when the files change."""
        signature = self._current_signature()
        if signature == self._signature:
            return self._records

        records = []
        for path in self._db_files():
            records.extend(self._read_file(path))
        records.sort(key=lambda item: item[0])

        self._records = records
        self._signature = signature
        return records

    @staticmethod
    def _read_file(path: str) -> list[tuple]:
        """Read one database file and return its (datetime, values) records."""
        try:
            with open(path, "r", encoding="utf-8") as db_file:
                db_data = json.load(db_file)
        except (OSError, ValueError) as e:
            log(f"Failed to read history file {path}: {e}", "DASHBOARD", "ERROR")
            return []

        records = []
        for entry in db_data.get("instant", []):
            try:
                timestamp = datetime.datetime.fromtimestamp(int(entry["timestamp"]))
                values = entry["values"]
            except (KeyError, TypeError, ValueError, OSError, OverflowError):
                continue
            records.append((timestamp, values))
        return records

    def bounds(self):
        """Return the (earliest, latest) datetimes in the history, or None."""
        records = self._load()
        if not records:
            return None
        return records[0][0], records[-1][0]

    def _pick_bucket(self, span: datetime.timedelta) -> datetime.timedelta:
        """Choose a bucket size that keeps the number of plotted points small."""
        for max_span, bucket in self.BUCKETS:
            if span <= max_span:
                return bucket
        return self.DEFAULT_BUCKET

    def series(self, start=None, end=None) -> list[dict]:
        """Return aggregated points between *start* and *end* (inclusive).

        Each point contains a bucket ``timestamp`` plus the averaged register
        values, along with a derived ``pv_power`` (pv1 + pv2). Missing values
        are reported as ``None``.
        """
        records = self._load()
        if not records:
            return []

        if start is None:
            start = records[0][0]
        if end is None:
            end = records[-1][0]

        bucket = self._pick_bucket(end - start)
        bucket_seconds = bucket.total_seconds()
        if bucket_seconds <= 0:
            bucket_seconds = self.DEFAULT_BUCKET.total_seconds()

        buckets = {}
        for timestamp, values in records:
            if timestamp < start or timestamp > end:
                continue
            index = int(timestamp.timestamp() // bucket_seconds)
            accumulator = buckets.get(index)
            if accumulator is None:
                accumulator = {field: [0.0, 0] for field in self.FIELDS}
                buckets[index] = accumulator
            for field in self.FIELDS:
                value = values.get(field)
                if isinstance(value, (int, float)):
                    accumulator[field][0] += value
                    accumulator[field][1] += 1

        points = []
        for index in sorted(buckets):
            accumulator = buckets[index]
            timestamp = datetime.datetime.fromtimestamp(index * bucket_seconds)
            point = {"timestamp": timestamp}
            for field in self.FIELDS:
                total, count = accumulator[field]
                point[field] = total / count if count else None
            pv_values = [
                point[field]
                for field in ("pv1_power", "pv2_power")
                if point[field] is not None
            ]
            point["pv_power"] = sum(pv_values) if pv_values else None
            points.append(point)
        return points

    @staticmethod
    def _numeric(values: dict, field: str, default: float = 0.0) -> float:
        """Return a numeric register value, or *default* when missing."""
        value = values.get(field)
        if isinstance(value, (int, float)):
            return float(value)
        return default

    def _pv_power(self, values: dict) -> float:
        """Return the combined PV power (pv1 + pv2) for a reading."""
        return self._numeric(values, "pv1_power") + self._numeric(
            values, "pv2_power"
        )

    def _energy_intervals(self, start, end):
        """Yield ``(timestamp, energy_used_kwh, energy_solar_kwh)`` per interval.

        The power readings are integrated over time using the trapezoidal rule;
        intervals longer than :attr:`ENERGY_MAX_GAP` are skipped so logging
        downtime does not inflate the totals. Energy is attributed to the
        interval start.
        """
        records = self._load()
        if len(records) < 2:
            return

        if start is None:
            start = records[0][0]
        if end is None:
            end = records[-1][0]

        selected = [
            (timestamp, values)
            for timestamp, values in records
            if start <= timestamp <= end
        ]
        if len(selected) < 2:
            return

        max_gap = self.ENERGY_MAX_GAP.total_seconds()
        for (time_a, values_a), (time_b, values_b) in zip(selected, selected[1:]):
            seconds = (time_b - time_a).total_seconds()
            if seconds <= 0 or seconds > max_gap:
                continue
            hours = seconds / 3600.0
            used_avg = (
                self._numeric(values_a, "load_power")
                + self._numeric(values_b, "load_power")
            ) / 2.0
            solar_avg = (self._pv_power(values_a) + self._pv_power(values_b)) / 2.0
            yield time_a, used_avg * hours / 1000.0, solar_avg * hours / 1000.0

    def energy_totals(self, start=None, end=None) -> dict:
        """Integrate power over the range to estimate total energy in kWh.

        Returns ``{"energy_used": kWh, "energy_solar": kWh}``.
        """
        totals = {"energy_used": 0.0, "energy_solar": 0.0}
        for _, used, solar in self._energy_intervals(start, end):
            totals["energy_used"] += used
            totals["energy_solar"] += solar
        return totals

    def energy_by_period(self, start=None, end=None, period: str = "day") -> list[dict]:
        """Integrate energy into per-``"day"`` or per-``"month"`` buckets.

        Returns ``[{"label": str, "energy_used": kWh, "energy_solar": kWh}]``,
        ordered by time, for the bar plots shown on long history ranges.
        """
        date_format = "%Y-%m" if period == "month" else "%Y-%m-%d"
        buckets: dict[str, dict] = {}
        for timestamp, used, solar in self._energy_intervals(start, end):
            bucket = buckets.setdefault(
                timestamp.strftime(date_format),
                {"energy_used": 0.0, "energy_solar": 0.0},
            )
            bucket["energy_used"] += used
            bucket["energy_solar"] += solar
        return [{"label": label, **buckets[label]} for label in sorted(buckets)]
