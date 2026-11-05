"""Search for a Solarman inverter on the local network."""
import argparse

from solarman.client import Client


def parse_args():
    """Parse and return command-line arguments."""
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--network",
        type=str,
        required=True,
        help="Network to search for the inverter (e.g., 10.0.0.0/24)",
    )

    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()

    result = Client.search_inverter(args.network)
    if not result:
        print("No inverter found on the network.")
    else:
        print(f"Found {len(result)} possible inverter(s) on the network:")
        for inverter_ip, inverter_serial in result:
            print(f"- IP: {inverter_ip}")
            print(f"  Serial: {inverter_serial}")