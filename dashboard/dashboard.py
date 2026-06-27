import dash
from dash import Dash, dcc, html
import dash_bootstrap_components as dbc

from dashboard.components.card import Card
from solarman.client import Client


class Dashboard:
    def __init__(
        self, inverter_ip: str, inverter_serial: int, polling_interval: int = 5
    ):
        self.inverter_ip = inverter_ip
        self.inverter_serial = inverter_serial
        self.polling_interval = polling_interval

        self.app = Dash(__name__, external_stylesheets=[dbc.themes.BOOTSTRAP])
        self.create_layout()

        self.inverter = Client(self.inverter_ip, self.inverter_serial)
        self.connection_retry_count = 0

    def create_layout(self):
        self.app.layout = html.Div(
            className="app-shell",
            children=[
                html.Div(
                    className="hero",
                    children=[
                        html.Div(
                            className="hero__eyebrow",
                            children="SolarStats",
                        ),
                        html.H1(children="Inverter Dashboard"),
                        html.P(
                            children=(
                                "Live register values from the inverter, refreshed "
                                f"every {self.polling_interval} seconds."
                            )
                        ),
                        html.Div(
                            className="hero__meta",
                            children=[
                                html.Span(f"IP {self.inverter_ip}"),
                            ],
                        ),
                    ],
                ),
                html.Div(id="inverter-info"),
                dcc.Interval(
                    id="interval-component",
                    interval=self.polling_interval * 1000,  # in milliseconds
                    n_intervals=0,
                ),
            ],
        )

        self.app.callback(
            dash.dependencies.Output("inverter-info", "children"),
            dash.dependencies.Input("interval-component", "n_intervals"),
        )(self.update_inverter_info)

    def update_inverter_info(self, n_intervals):
        try:
            inverter_data = self.inverter.read_registers(
                self.inverter.get_available_registers()
            )
        except Exception as e:
            self.connection_retry_count += 1
            if self.connection_retry_count > 3:
                self.inverter_ip, _ = self.inverter.search_inverter(
                    self.inverter_ip + "/24"
                )
                if self.inverter_ip == "":
                    return html.Div(
                        className="error-message",
                        children="Inverter not found on the network.",
                    )
            self.inverter = Client(self.inverter_ip, self.inverter_serial)
            inverter_data = self.inverter.read_registers(
                self.inverter.get_available_registers()
            )

        return html.Div(
            className="register-sections",
            children=[
                dbc.Row(
                    [
                        dbc.Col(Card("SOC", inverter_data["soc"], "%"), md=4),
                        dbc.Col(
                            Card("Load Power", inverter_data["load_power"], "W"), md=4
                        ),
                        dbc.Col(
                            Card(
                                "Solar Power",
                                inverter_data["pv1_power"] + inverter_data["pv2_power"],
                                "W",
                            ),
                            md=4,
                        ),
                    ]
                ),
                dbc.Row(
                    [
                        dbc.Col(
                            Card(
                                "Daily Production",
                                inverter_data["daily_production"] / 10.0,
                                "kWh",
                            ),
                            md=4,
                        ),
                        dbc.Col(
                            Card(
                                "Daily Consumption",
                                inverter_data["daily_consumption"] / 10.0,
                                "kWh",
                            ),
                            md=4,
                        ),
                        dbc.Col(
                            Card(
                                "Total Production",
                                inverter_data["total_production"] / 10.0,
                                "kWh",
                            ),
                            md=4,
                        ),
                    ]
                ),
            ],
        )

    def run(self, dashboard_host: str = "127.0.0.1"):
        self.app.run(
            host=dashboard_host,
            debug=True,
            use_reloader=False,
            dev_tools_hot_reload=False,
        )
