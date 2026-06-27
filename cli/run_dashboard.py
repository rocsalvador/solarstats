from dashboard import dashboard
import argparse


def parse_args():
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
    args = parser.parse_args()

    return args


if __name__ == "__main__":
    args = parse_args()

    dashboard_app = dashboard.Dashboard(
        inverter_ip=args.inverter_ip,
        inverter_serial=args.inverter_serial,
        polling_interval=args.polling_interval,
    )
    dashboard_app.run(dashboard_host=args.dashboard_host)
