"""Solarman V5 data-logging stick client."""
import socket
import struct
import time

import nmap
import pysolarmanv5

from utils.log import log


class Client:
    """Client for communicating with a Solarman V5 data-logging stick."""

    def __init__(self, address: str, serial: int):
        self.address = address
        self.serial = serial
        self.inverter = None
        self._connect()

        self.deye_hybrid_registers = {
            "soc": 0x00B8,
            "load_power": 0x00AF,
            "pv1_power": 0x00BA,
            "pv2_power": 0x00BB,
            "daily_production": 0x006C,
            "daily_consumption": 0x0054,
            "total_production": 0x0060,
        }

    def _connect(self) -> bool:
        """Create the underlying PySolarmanV5 connection.

        Returns ``True`` on success. Connection failures are tolerated so that
        callers (e.g. the dashboard) can start up and surface the offline state
        instead of crashing.
        """
        try:
            self.inverter = pysolarmanv5.PySolarmanV5(
                self.address, self.serial, auto_reconnect=True, socket_timeout=10
            )
            return True
        except (pysolarmanv5.NoSocketAvailableError, OSError) as e:
            log(
                f"Could not connect to inverter at {self.address}: {e}",
                "CLIENT",
                "ERROR",
            )
            self.inverter = None
            return False

    def _ensure_connected(self):
        """Ensure an active connection, raising if one cannot be established."""
        if self.inverter is None and not self._connect():
            raise pysolarmanv5.NoSocketAvailableError(
                f"No socket available for {self.address}"
            )

    def disconnect(self):
        """Cleanly disconnect from the inverter."""
        try:
            self.inverter.disconnect()
        except (AttributeError, OSError, pysolarmanv5.NoSocketAvailableError):
            pass

    def is_reachable(self, timeout: float = 2.0) -> bool:
        """Quickly check whether the data logger accepts TCP connections.

        Returns ``False`` when the host is unreachable or refuses port 8899.
        This lets the dashboard surface an offline state immediately instead
        of waiting for the much longer register-read timeout and retries.
        """
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(timeout)
        try:
            sock.connect((self.address, 8899))
            return True
        except OSError:
            return False
        finally:
            sock.close()

    @staticmethod
    def get_inverter_serial(ip: str) -> int:
        """Discover the serial number of the Solarman data logging stick
        at the given IP using the V5 TCP protocol on port 8899.

        Sends a minimal V5 frame with serial=0; the data logger responds
        with its real serial number embedded in bytes 7-10 of the reply.
        """
        return Client._get_serial_via_tcp(ip)

    @staticmethod
    def _get_serial_via_tcp(ip: str) -> int:
        """Discover the logger serial via the V5 TCP protocol on port 8899."""
        mb_request = bytes.fromhex("010300000001840a")

        seq = 0x01
        v5_payload = (
            b"\xA5"
            + struct.pack("<H", 15 + len(mb_request))
            + struct.pack("<H", 0x4510)
            + struct.pack("<H", seq)
            + struct.pack("<I", 0)
            + b"\x02"
            + b"\x00\x00"
            + b"\x00\x00\x00\x00"
            + b"\x00\x00\x00\x00"
            + b"\x00\x00\x00\x00"
            + mb_request
        )
        checksum = sum(v5_payload) & 0xFF
        v5_frame = v5_payload + bytes([checksum, 0x15])

        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(5.0)
        try:
            sock.connect((ip, 8899))
            sock.sendall(v5_frame)
            data = sock.recv(4096)
            if len(data) >= 11:
                return struct.unpack("<I", data[7:11])[0]
        except (OSError, socket.timeout, struct.error) as e:
            log(f"TCP serial discovery failed for {ip}: {e}", "CLIENT", "WARNING")
        finally:
            try:
                sock.close()
            except OSError:
                pass

        return 0

    @staticmethod
    def search_inverter(broadcast_ip: str) -> tuple[str, int] | None:
        """Scan the network for a Solarman data logging stick.

        Uses nmap to find hosts with TCP port 8899 open, then attempts
        UDP discovery on each candidate to retrieve the serial number.
        Returns the first responder as ``(ip, serial)``, or ``None`` if
        no inverter data logger was found.
        """
        port_scanner = nmap.PortScanner()
        port_scanner.scan(hosts=broadcast_ip, arguments="-sT -p 8899 --open")
        for candidate_ip in port_scanner.all_hosts():
            if (
                port_scanner[candidate_ip].has_tcp(8899)
                and port_scanner[candidate_ip]["tcp"][8899]["state"] == "open"
            ):
                serial = Client.get_inverter_serial(candidate_ip)
                if serial:
                    return (candidate_ip, serial)
        return None

    def get_available_registers(self) -> list[str]:
        """Return the list of named register keys this client can read."""
        return list(self.deye_hybrid_registers.keys())

    def read_register(self, register_key: str):
        """Read a single register by name (e.g. 'soc') or hex address (e.g. '0x3100')."""
        self._ensure_connected()
        if register_key in self.deye_hybrid_registers:
            register_address = self.deye_hybrid_registers[register_key]
        else:
            register_address = int(register_key, 0)
        register_value = self.inverter.read_holding_registers(
            register_address, quantity=1
        )[0]
        return register_value

    def read_registers(self, register_keys: list[str]) -> dict[str, int]:
        """Read multiple registers and return a dict mapping key to value."""
        registers_value = {}
        for register_key in register_keys:
            registers_value[register_key] = self.read_register(register_key)
        return registers_value

    def read_registers_with_retry(
        self, registers: list[str], max_retries: int = 3, retry_delay: int = 1
    ) -> dict[str, int] | None:
        """Read registers with exponential-backoff retry on recoverable errors.

        Returns the register dict on success, or *None* after all attempts fail.
        """
        last_error = None
        for attempt in range(1 + max_retries):
            try:
                return self.read_registers(registers)
            except (
                pysolarmanv5.NoSocketAvailableError,
                pysolarmanv5.V5FrameError,
                TimeoutError,
                OSError,
            ) as e:
                last_error = e
                log(
                    f"Failed to read registers from inverter at {self.address} "
                    f"(attempt {attempt + 1}/{1 + max_retries}): {e}",
                    "CLIENT",
                    "ERROR",
                )
                if attempt < max_retries:
                    sleep_time = retry_delay * (2**attempt)
                    log(
                        f"Reconnecting and retrying in {sleep_time}s...",
                        "CLIENT",
                        "INFO",
                    )
                    self._reconnect()
                    time.sleep(sleep_time)
            # pylint: disable=broad-exception-caught
            except Exception as e:
                last_error = e
                log(
                    f"Unexpected error reading registers from inverter at "
                    f"{self.address} (attempt {attempt + 1}/{1 + max_retries}): {e}",
                    "CLIENT",
                    "ERROR",
                )
                if attempt < max_retries:
                    time.sleep(retry_delay)

        log(
            f"All {1 + max_retries} attempts failed. Last error: {last_error}",
            "CLIENT",
            "ERROR",
        )
        return None

    def _reconnect(self):
        """Reconnect to the inverter by creating a fresh PySolarmanV5 instance."""
        if self.inverter is not None:
            try:
                self.inverter.disconnect()
            except (OSError, pysolarmanv5.NoSocketAvailableError):
                pass
        self._connect()
