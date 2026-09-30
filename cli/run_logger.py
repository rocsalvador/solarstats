"""Periodically log inverter data to JSON database files."""
import argparse

from solarman.logger import Logger


def parse_args():
    """Parse and return command-line arguments."""
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--inverter-ip",
        type=str,
        required=True,
        help="IP address of the inverter",
    )
    parser.add_argument(
        "--inverter-serial",
        type=int,
        required=True,
        help="Serial number of the inverter",
    )
    parser.add_argument(
        "--polling-interval",
        type=int,
        default=300,
        help="Polling interval in seconds for logging data",
    )
    parser.add_argument(
        "--db-prefix",
        type=str,
        default="solardb",
        help="Prefix for the log database files",
    )

    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()

    logger = Logger(
        inverter_ip=args.inverter_ip,
        inverter_serial=args.inverter_serial,
        db_prefix=args.db_prefix,
    )
    logger.run(polling_interval=args.polling_interval)
