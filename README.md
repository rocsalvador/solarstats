# solarstats

Monitor a Solarman solar inverter from your local network.

## Setup

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Usage

### Find your inverter

```bash
python -m cli.search_inverter --network 10.0.0.0/24
```

Options:

```bash
usage: search_inverter.py [-h] --network NETWORK

options:
  -h, --help         show this help message and exit
  --network NETWORK  Network to search for the inverter (e.g., 10.0.0.0/24)
```

### Read register values

```bash
python -m cli.get_registers_value --inverter-ip 10.0.0.50 --inverter-serial 1234567890 --registers soc load_power
```

Options:

```bash
usage: get_registers_value.py [-h] [--inverter-network INVERTER_NETWORK] [--inverter-ip INVERTER_IP] [--inverter-serial INVERTER_SERIAL] [--registers REGISTERS [REGISTERS ...]] [--get-available-registers]

options:
  -h, --help            show this help message and exit
  --inverter-network INVERTER_NETWORK
                        Network to search for the inverter (e.g., 10.0.0.0/24)
  --inverter-ip INVERTER_IP
                        IP address of the inverter
  --inverter-serial INVERTER_SERIAL
                        Serial number of the inverter
  --registers REGISTERS [REGISTERS ...]
                        Registers to read from the inverter
  --get-available-registers
                        Get available registers
```

### Log data to JSON files

```bash
python -m cli.run_logger --inverter-ip 10.0.0.50 --inverter-serial 1234567890
```

Options:

```bash
usage: run_logger.py [-h] --inverter-ip INVERTER_IP --inverter-serial INVERTER_SERIAL [--polling-interval POLLING_INTERVAL] [--db-prefix DB_PREFIX]

options:
  -h, --help            show this help message and exit
  --inverter-ip INVERTER_IP
                        IP address of the inverter
  --inverter-serial INVERTER_SERIAL
                        Serial number of the inverter
  --polling-interval POLLING_INTERVAL
                        Polling interval in seconds for logging data
  --db-prefix DB_PREFIX
                        Prefix for the log database files
```

### Start the dashboard

```bash
python -m cli.run_dashboard --inverter-ip 10.0.0.50 --inverter-serial 1234567890
```

Options:

```bash
usage: run_dashboard.py [-h] --inverter-ip INVERTER_IP --inverter-serial INVERTER_SERIAL [--polling-interval POLLING_INTERVAL] [--dashboard-host DASHBOARD_HOST] [--db-prefix DB_PREFIX]

options:
  -h, --help            show this help message and exit
  --inverter-ip INVERTER_IP
                        IP address of the inverter
  --inverter-serial INVERTER_SERIAL
                        Serial number of the inverter
  --polling-interval POLLING_INTERVAL
                        Polling interval in seconds for updating the dashboard
  --dashboard-host DASHBOARD_HOST
                        Host address for the dashboard
  --db-prefix DB_PREFIX
                        Prefix for the log database files shown in the history section
```

Open http://127.0.0.1:8050 in your browser.



## Project structure

```
cli/            Command-line tools
dashboard/      Dash web dashboard
solarman/       Inverter client and logger
utils/          Shared utilities
```