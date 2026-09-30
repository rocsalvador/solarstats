"""Live inverter monitoring dashboard using Dash and Plotly."""
from dash import Dash, dcc, html, Output, Input
import dash_bootstrap_components as dbc
import plotly.graph_objects as go

from dashboard.components.card import Card
from solarman.client import Client
from utils.log import log


class Dashboard:
    """Dash web application that displays live inverter register values and a history chart."""
    def __init__(
        self, inverter_ip: str, inverter_serial: int, polling_interval: int = 5
    ):
        self.inverter_ip = inverter_ip
        self.inverter_serial = inverter_serial
        self.polling_interval = polling_interval

        self.app = Dash(__name__, external_stylesheets=[dbc.themes.BOOTSTRAP])
        self.create_layout()

        self.inverter = Client(self.inverter_ip, self.inverter_serial)
        self.history_data = {
            "soc": [],
            "load_power": [],
            "pv_power": [],
        }

    def create_layout(self):
        """Build the Dash app layout with hero section, cards, graph, and interval."""
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
                html.Div(id="inverter-cards"),
                dcc.Graph(
                    id="inverter-graph",
                    className="graph-container",
                ),
                dcc.Interval(
                    id="interval-component",
                    interval=self.polling_interval * 1000,  # in milliseconds
                    n_intervals=0,
                ),
            ],
        )

        self.app.callback(
            output=[
                Output("inverter-cards", "children"),
                Output("inverter-graph", "figure"),
            ],
            inputs=Input("interval-component", "n_intervals"),
            running=[
                (Output("interval-component", "disabled"), True, False),
            ],
        )(self._update_dashboard)

    def _create_figure(self):
        """Build a Plotly figure with SOC and power traces."""
        trace_soc = go.Scatter(
            x=list(range(len(self.history_data["soc"]))),
            y=self.history_data["soc"],
            mode="lines",
            name="SOC",
            yaxis="y",
            line={"color": "#22C55E", "width": 3},
        )

        trace_load = go.Scatter(
            x=list(range(len(self.history_data["load_power"]))),
            y=self.history_data["load_power"],
            mode="lines",
            name="Load Power",
            yaxis="y2",
            line={"color": "#F51F0B", "width": 2},
        )

        trace_pv = go.Scatter(
            x=list(range(len(self.history_data["pv_power"]))),
            y=self.history_data["pv_power"],
            mode="lines",
            name="PV Power",
            yaxis="y2",
            line={"color": "#3B82F6", "width": 2},
        )

        power_range = [
            0,
            max(
                self.history_data["load_power"] + self.history_data["pv_power"],
                default=0,
            )
            * 1.1,
        ]

        layout = go.Layout(
            title="Inverter Data Over Time",
            xaxis={"title": "Time (intervals)", "showgrid": False},
            yaxis={
                "title": "SOC (%)",
                "side": "left",
                "range": [0, 100],
                "showgrid": False,
            },
            yaxis2={
                "title": "Power (W)",
                "side": "right",
                "overlaying": "y",
                "range": power_range,
                "showgrid": False,
            },
            legend={
                "orientation": "h",
                "yanchor": "bottom",
                "y": 1.02,
                "xanchor": "right",
                "x": 1,
            },
            plot_bgcolor="rgba(0,0,0,0)",
            paper_bgcolor="rgba(0,0,0,0)",
            font={"family": "inherit"},
        )

        figure = go.Figure(data=[trace_soc, trace_load, trace_pv], layout=layout)
        return figure

    def _read_inverter_data(self):
        """Read inverter registers and return the data dict, or None on failure."""
        return self.inverter.read_registers_with_retry(
            [
                "soc",
                "load_power",
                "pv1_power",
                "pv2_power",
                "daily_production",
                "daily_consumption",
                "total_production",
            ]
        )

    def _handle_read_failure(self):
        """Log failure, attempt re-discovery, and return an error card div."""
        log(
            f"Failed to read inverter data from {self.inverter_ip}. "
            "Searching for inverter on the network...",
            "DASHBOARD",
            "ERROR",
        )
        result = Client.search_inverter(self.inverter_ip + "/24")
        if result:
            new_ip, _ = result
            log(
                f"Found inverter at {new_ip}. Reconnecting...",
                "DASHBOARD",
                "INFO",
            )
            self.inverter.disconnect()
            self.inverter_ip = new_ip
            self.inverter = Client(self.inverter_ip, self.inverter_serial)
        return (
            html.Div(
                className="error-message",
                children=(
                    "Error reading inverter data. "
                    f"Retrying in {self.polling_interval} seconds..."
                ),
            ),
            go.Figure(),
        )

    def _update_dashboard(self, n_intervals):  # pylint: disable=unused-argument
        """Read inverter data and return updated cards and graph."""
        inverter_data = self._read_inverter_data()
        if inverter_data is None:
            return self._handle_read_failure()

        self.history_data["soc"].append(inverter_data["soc"])
        self.history_data["load_power"].append(inverter_data["load_power"])
        self.history_data["pv_power"].append(
            inverter_data["pv1_power"] + inverter_data["pv2_power"]
        )

        cards = html.Div(
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

        return cards, self._create_figure()

    def run(self, dashboard_host: str = "127.0.0.1"):
        """Start the Dash development server."""
        self.app.run(
            host=dashboard_host,
            debug=True,
            use_reloader=False,
            dev_tools_hot_reload=False,
        )
