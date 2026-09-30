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

### Read register values

```bash
python -m cli.get_registers_value --inverter-ip 10.0.0.50 --inverter-serial 1234567890 --registers soc load_power
```

### Log data to JSON files

```bash
python -m cli.run_logger --inverter-ip 10.0.0.50 --inverter-serial 1234567890
```

### Start the dashboard

```bash
python -m cli.run_dashboard --inverter-ip 10.0.0.50 --inverter-serial 1234567890
```

Open http://127.0.0.1:8050 in your browser.

## Project structure

```
cli/            Command-line tools
dashboard/      Dash web dashboard
solarman/       Inverter client and logger
utils/          Shared utilities
db/             Daily JSON data files
```