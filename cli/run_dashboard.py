"""Launch the inverter monitoring dashboard."""
import argparse

from dashboard import dashboard


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
        default=5,
        help="Polling interval in seconds for updating the dashboard",
    )
    parser.add_argument(
        "--dashboard-host",
        type=str,
        default="127.0.0.1",
        help="Host address for the dashboard",
    )
    parser.add_argument(
        "--db-prefix",
        type=str,
        default=None,
        help=(
            "Prefix for the log database files shown in the history section. "
            "If omitted, the history section is disabled."
        ),
    )
    parser.add_argument(
        "--lang",
        type=str,
        default="ca",
        choices=["en", "ca"],
        help="Default language for the dashboard (en = English, ca = Català)",
    )

    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()

    dashboard_app = dashboard.Dashboard(
        inverter_ip=args.inverter_ip,
        inverter_serial=args.inverter_serial,
        polling_interval=args.polling_interval,
        db_prefix=args.db_prefix,
        default_lang=args.lang,
    )
    dashboard_app.run(dashboard_host=args.dashboard_host)
