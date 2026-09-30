"""Read register values from a Solarman inverter."""
import argparse

from solarman.client import Client


def parse_args():
    """Parse and return command-line arguments."""
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--inverter-network",
        type=str,
        help="Network to search for the inverter (e.g., 10.0.0.0/24)",
    )
    parser.add_argument("--inverter-ip", type=str, help="IP address of the inverter")
    parser.add_argument(
        "--inverter-serial", type=int, help="Serial number of the inverter"
    )
    parser.add_argument(
        "--registers",
        type=str,
        nargs="+",
        help="Registers to read from the inverter",
    )
    parser.add_argument(
        "--get-available-registers", action="store_true", help="Get available registers"
    )

    args = parser.parse_args()

    if not args.inverter_network and not args.inverter_ip:
        parser.error("Either --inverter-network or --inverter-ip must be provided.")

    if not args.registers and not args.get_available_registers:
        parser.error(
            "Either --registers or --get-available-registers must be provided."
        )

    return args


if __name__ == "__main__":
    cli_args = parse_args()

    if not cli_args.inverter_ip:
        result = Client.search_inverter(cli_args.inverter_network)
        if result is None:
            raise ValueError(
                "No inverter found on the network. "
                "Provide --inverter-ip and --inverter-serial."
            )
        inverter_ip, inverter_serial = result
        if cli_args.inverter_serial:
            inverter_serial = cli_args.inverter_serial
        elif not cli_args.inverter_serial and inverter_serial == 0:
            raise ValueError(
                "Inverter serial not found. Please provide --inverter-serial."
            )
    else:
        inverter_ip = cli_args.inverter_ip
        if cli_args.inverter_serial:
            inverter_serial = cli_args.inverter_serial
        else:
            inverter_serial = Client.get_inverter_serial(inverter_ip)

    client = Client(inverter_ip, inverter_serial)

    try:
        if cli_args.get_available_registers:
            available_registers = client.get_available_registers()
            print(available_registers)
        else:
            registers_value = client.read_registers_with_retry(cli_args.registers)
            if registers_value is None:
                print("Failed to read registers from inverter.")
            else:
                print(registers_value)
    finally:
        client.disconnect()
