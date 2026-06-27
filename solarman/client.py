from pysolarmanv5 import PySolarmanV5
import nmap
import socket


class Client:
    def __init__(self, address: str, serial: int):
        self.address = address
        self.serial = serial

        self.inverter = PySolarmanV5(address, serial)

        self.deye_hybrid_registers = {
            "soc": 0x00B8,
            "load_power": 0x00AF,
            "pv1_power": 0x00BA,
            "pv2_power": 0x00BB,
            "daily_production": 0x006C,
            "daily_consumption": 0x0054,
            "total_production": 0x0060,
        }

    @staticmethod
    def get_inverter_serial(ip: str) -> int:
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        sock.settimeout(1.0)

        request = "WIFIKIT-214028-READ"
        address = (ip, 48899)

        sock.sendto(request.encode(), address)
        while True:
            try:
                data = sock.recv(1024)
            except socket.timeout:
                break
            keys = dict.fromkeys(["ipaddress", "mac", "serial"])
            values = data.decode().split(",")
            result = dict(zip(keys, values))
            return int(result["serial"])

        return 0

    @staticmethod
    def search_inverter(broadcast_ip: str) -> tuple[str, int]:
        port_scanner = nmap.PortScanner()
        port_scanner.scan(hosts=broadcast_ip, arguments="-sT -p 8899 --open")
        inverter_ip = ""
        for candidate_ip in port_scanner.all_hosts():
            if (
                port_scanner[candidate_ip].has_tcp(8899)
                and port_scanner[candidate_ip]["tcp"][8899]["state"] == "open"
            ):
                inverter_ip = candidate_ip
                inverter_serial = Client.get_inverter_serial(inverter_ip)
                if inverter_serial:
                    return inverter_ip, inverter_serial

        return inverter_ip, 0

    def get_available_registers(self) -> list[str]:
        return list(self.deye_hybrid_registers.keys())

    def read_register(self, register_key: str):
        register_address = self.deye_hybrid_registers[register_key]
        register_value = self.inverter.read_holding_registers(
            register_address, quantity=1
        )[0]
        return register_value

    def read_registers(self, register_keys: list[str]) -> dict[str, int]:
        registers_value = {}
        for register_key in register_keys:
            registers_value[register_key] = self.read_register(register_key)
        return registers_value
