from solarman.client import Client
import argparse


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--network",
        type=str,
        required=True,
        help="Network to search for the inverter (e.g., 192.168.1.0/24)",
    )
    args = parser.parse_args()

    return args


if __name__ == "__main__":
    args = parse_args()

    inverter_ip, inverter_serial = Client.search_inverter(args.network)
    print(f"Inverter at IP: {inverter_ip}")
    if inverter_serial == 0:
        print("Inverter serial: not found")
    else:
        print(f"Inverter serial: {inverter_serial}")
