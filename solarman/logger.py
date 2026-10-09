"""Periodic data logging to JSON database files."""
import datetime
import json
import os
import time

from solarman.client import Client
from utils.log import log


class Logger:
    """Periodically reads inverter registers and saves them to daily JSON files."""

    INSTANT_REGISTERS = ["soc", "load_power", "pv1_power", "pv2_power"]
    DAILY_REGISTERS = ["daily_production", "daily_consumption", "total_production"]

    def __init__(
        self,
        inverter_ip: str,
        inverter_serial: int,
        db_prefix: str = "solardb",
    ):
        self.inverter_ip = inverter_ip
        self.inverter_serial = inverter_serial
        self.db_prefix = db_prefix

        self.inverter = Client(self.inverter_ip, self.inverter_serial)

        self._consecutive_failures = 0
        self._max_consecutive_failures = 3

        db_dir = os.path.dirname(self.db_prefix)
        if db_dir and not os.path.exists(db_dir):
            os.makedirs(db_dir)

    def _save_to_db(self, registers_value: dict, db_type: str):
        """Save register values to the daily JSON database file."""
        current_day = time.strftime("%Y-%m-%d")
        current_db_file = f"{self.db_prefix}_{current_day}.json"
        if os.path.exists(current_db_file):
            with open(current_db_file, "r", encoding="utf-8") as db_file:
                db_data = json.load(db_file)
        else:
            db_data = {}

        with open(current_db_file, "w", encoding="utf-8") as db_file:
            if db_type == "instant":
                timestamp = int(time.time())
                if "instant" not in db_data:
                    db_data["instant"] = []
                db_data["instant"].append(
                    {"timestamp": timestamp, "values": registers_value}
                )
            elif db_type == "daily":
                db_data["daily"] = {"values": registers_value}
            json.dump(db_data, db_file, indent=4)

    def _search_and_reconnect(self):
        """Search for the inverter on the network and reconnect if found."""
        log(
            "Searching for inverter on the network...",
            "LOGGER",
            "INFO",
        )
        result = Client.search_inverter(self.inverter_ip + "/24")
        if result:
            new_ip, _ = result
            log(
                f"Found inverter at {new_ip}. Reconnecting...",
                "LOGGER",
                "INFO",
            )
            self.inverter.disconnect()
            self.inverter_ip = new_ip
            self.inverter = Client(self.inverter_ip, self.inverter_serial)
            self._consecutive_failures = 0
            return True
        return False

    def _handle_read_failure(self, context: str):
        """Log a read failure, increment counter, and re-connect if threshold exceeded."""
        log(
            f"Failed to read {context} registers from inverter at {self.inverter_ip}.",
            "LOGGER",
            "ERROR",
        )
        self._consecutive_failures += 1
        if self._consecutive_failures >= self._max_consecutive_failures:
            log(
                f"{self._consecutive_failures} consecutive failures. "
                "Searching for inverter on the network...",
                "LOGGER",
                "WARNING",
            )
            if self._search_and_reconnect():
                self._consecutive_failures = 0

    def log_current_values(self):
        """Read instant registers and save them to the daily JSON database."""
        log(
            f"Logging current registers value from inverter at {self.inverter_ip}...",
            "LOGGER",
            "INFO",
        )
        registers_value = self.inverter.read_registers_with_retry(
            self.INSTANT_REGISTERS
        )
        if registers_value is None:
            self._handle_read_failure("instant")
            return

        self._consecutive_failures = 0
        self._save_to_db(registers_value, "instant")

    def log_daily_values(self):
        """Read daily accumulation registers and save them to the JSON database."""
        log(
            f"Logging daily registers value from inverter at {self.inverter_ip}...",
            "LOGGER",
            "INFO",
        )
        registers_value = self.inverter.read_registers_with_retry(self.DAILY_REGISTERS)
        if registers_value is None:
            self._handle_read_failure("daily")
            return

        self._consecutive_failures = 0
        self._save_to_db(registers_value, "daily")

    def run(self, polling_interval: int = 300):
        """Continuously log registers at the given polling interval (seconds).

        At the end of each day, daily accumulation registers are also logged.
        Unexpected errors are caught so the loop continues running.
        """
        while True:
            try:
                self.log_current_values()
                if (
                    datetime.datetime.now().timestamp() + polling_interval
                    >= datetime.datetime.combine(
                        datetime.datetime.now().date() + datetime.timedelta(days=1),
                        datetime.time.min,
                    ).timestamp()
                ):
                    self.log_daily_values()
            # pylint: disable=broad-exception-caught
            except Exception as e:
                log(
                    f"Unexpected error in logger loop: {e}",
                    "LOGGER",
                    "ERROR",
                )
                self._consecutive_failures += 1
                if self._consecutive_failures >= self._max_consecutive_failures:
                    log(
                        f"{self._consecutive_failures} consecutive failures. "
                        "Searching for inverter on the network...",
                        "LOGGER",
                        "WARNING",
                    )
                    if self._search_and_reconnect():
                        self._consecutive_failures = 0
            time.sleep(polling_interval)
