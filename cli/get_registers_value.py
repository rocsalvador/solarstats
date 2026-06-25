from solarman.client import Client
import argparse


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--inverter-network",
        type=str,
        help="Network to search for the inverter (e.g., 192.168.1.0/24)",
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
    args = parse_args()

    if not args.inverter_ip:
        inverter_ip, inverter_serial = Client.search_inverter(args.inverter_network)
        if args.inverter_serial:
            inverter_serial = args.inverter_serial
        elif not args.inverter_serial and inverter_serial == 0:
            raise ValueError(
                "Inverter serial not found. Please provide --inverter-serial."
            )
    else:
        inverter_ip = args.inverter_ip
        if args.inverter_serial:
            inverter_serial = args.inverter_serial
        else:
            inverter_serial = Client.get_inverter_serial(inverter_ip)

    client = Client(inverter_ip, inverter_serial)

    if args.get_available_registers:
        available_registers = client.get_available_registers()
        print(available_registers)
    else:
        registers_value = client.read_registers(args.registers)
        print(registers_value)
