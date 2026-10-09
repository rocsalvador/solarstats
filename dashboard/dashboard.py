"""Live inverter monitoring dashboard using Dash and Plotly."""
from __future__ import annotations

import datetime
import threading


import dash
from dash import Dash, dcc, html, Output, Input, State, callback_context
import dash_bootstrap_components as dbc
import plotly.graph_objects as go

from dashboard.components.card import Card
from dashboard.history import HistoryStore
from dashboard.i18n import I18n, Lang
from solarman.client import Client
from utils.log import log


class Dashboard:
    """Dash web application that displays live inverter register values and history charts."""
    def __init__(
        self,
        inverter_ip: str,
        inverter_serial: int,
        polling_interval: int = 5,
        db_prefix: str | None = None,
        default_lang: Lang = "ca",
    ):
        self.inverter_ip = inverter_ip
        self.inverter_serial = inverter_serial
        self.polling_interval = polling_interval
        self.db_prefix = db_prefix
        self._default_lang = default_lang

        self.history_store = HistoryStore(db_prefix) if db_prefix else None
        self.history_ranges = [
            {"label": "", "value": "24h"},
            {"label": "", "value": "7d"},
            {"label": "", "value": "30d"},
            {"label": "", "value": "all"},
            {"label": "", "value": "custom"},
        ]

        page_title = I18n(self._default_lang)("page.title")
        self.app = Dash(__name__, title=page_title, external_stylesheets=[dbc.themes.BOOTSTRAP])
        self.app.index_string = """<!DOCTYPE html>
<html>
    <head>
        {%metas%}
        <title>{%title%}</title>
        <link rel="icon" href="/assets/favicon.svg" type="image/svg+xml"/>
        {%css%}
    </head>
    <body>
        {%app_entry%}
        <footer>
            {%config%}
            {%scripts%}
            {%renderer%}
        </footer>
    </body>
</html>"""
        self.create_layout()
        self._register_callbacks()

        self.inverter = Client(self.inverter_ip, self.inverter_serial)
        self._inverter_lock = threading.Lock()
        self.history_data = {
            "soc": [],
            "load_power": [],
            "pv_power": [],
        }
        self._last_inverter_search = None

    def create_layout(self):
        """Build the Dash app layout with hero section, cards, graph, and interval."""
        t = I18n(self._default_lang)
        self.app.layout = html.Div(
            className="app-shell",
            children=[
                # Hidden stores.
                dcc.Store(id="lang-store", data=self._default_lang),
                dcc.Store(id="page-title-trigger", data=self._default_lang),

                html.Div(
                    className="hero",
                    children=[
                        html.Div(
                            className="hero__row",
                            children=[
                                html.Div(
                                    className="hero__logo",
                                    children=html.Img(
                                        src="/assets/favicon.svg",
                                        className="hero__logo-img",
                                    ),
                                ),
                                html.Div(
                                    className="hero__eyebrow",
                                    children="SolarStats",
                                ),
                                html.Div(
                                    className="lang-switcher",
                                    id="lang-switcher",
                                    children=[
                                        html.Span(
                                            "EN",
                                            className="lang-switcher__option",
                                            id="lang-en",
                                        ),
                                        html.Span(
                                            "CA",
                                            className=(
                                                "lang-switcher__option "
                                                "lang-switcher__option--active"
                                            ),
                                            id="lang-ca",
                                        ),
                                    ],
                                ),
                            ],
                        ),
                        html.H1(id="hero-title", children=t("hero.title")),
                        html.P(id="hero-subtitle", children=t("hero.subtitle")),
                        html.Div(
                            className="hero__meta",
                            children=[
                                html.Span(f"IP {self.inverter_ip}"),
                                html.Div(
                                    id="inverter-status",
                                    children=self._create_status_indicator(
                                        "connecting", t
                                    ),
                                ),
                            ],
                        ),
                    ],
                ),
                html.Div(
                    className="live-section",
                    children=[
                        html.Div(
                            className="section-heading",
                            children=[
                                html.H2(id="live-heading", children=t("live.heading")),
                                html.P(
                                    id="live-description",
                                    children=t(
                                        "live.description",
                                        seconds=self.polling_interval,
                                    ),
                                ),
                            ],
                        ),
                        html.Div(id="inverter-cards", className="live-cards"),
                        dcc.Graph(
                            id="inverter-graph",
                            className="graph-container",
                        ),
                    ],
                ),
                self._create_history_section(t),
                dcc.Interval(
                    id="interval-component",
                    interval=self.polling_interval * 1000,  # in milliseconds
                    n_intervals=0,
                ),
            ],
        )

    def _register_callbacks(self):
        """Register all Dash callbacks."""
        # ── Live update callback ──────────────────────────────────────────
        self.app.callback(
            output=[
                Output("inverter-cards", "children"),
                Output("inverter-graph", "figure"),
                Output("inverter-status", "children"),
            ],
            inputs=[
                Input("interval-component", "n_intervals"),
                Input("lang-store", "data"),
            ],
            running=[
                (Output("interval-component", "disabled"), True, False),
            ],
        )(self._update_dashboard)

        # ── History callback ──────────────────────────────────────────────
        if self.history_store is not None:
            self.app.callback(
                output=[
                    Output("history-cards", "children"),
                    Output("history-graph", "figure"),
                    Output("history-custom-range", "style"),
                ],
                inputs=[
                    Input("history-range", "value"),
                    Input("history-date-range", "start_date"),
                    Input("history-date-range", "end_date"),
                    Input("history-interval", "n_intervals"),
                    Input("lang-store", "data"),
                ],
            )(self._update_history)

        # ── Language switcher callback ────────────────────────────────────
        self.app.callback(
            output=[
                Output("lang-store", "data"),
                Output("hero-title", "children"),
                Output("hero-subtitle", "children"),
                Output("live-heading", "children"),
                Output("live-description", "children"),
                Output("history-heading", "children"),
                Output("history-description", "children"),
                Output("history-range", "options"),
                Output("history-custom-range-label", "children"),
                Output("history-start-logger-msg", "children"),
                Output("lang-en", "className"),
                Output("lang-ca", "className"),
            ],
            inputs=[Input("lang-en", "n_clicks"), Input("lang-ca", "n_clicks")],
            state=[State("lang-store", "data")],
            prevent_initial_call=True,
        )(self._switch_language)

        # ── Dynamic page title ─────────────────────────────────────────────
        self.app.clientside_callback(
            """function(lang) {
                const titles = {"en": "Inverter Dashboard", "ca": "Panell de l'inversor"};
                document.title = titles[lang] || "SolarStats";
                return window.dash_clientside.no_update;
            }""",
            Output("page-title-trigger", "data"),
            Input("lang-store", "data"),
        )

    def _create_history_section(self, t: I18n):
        """Build the historic section, or a notice when no prefix is set."""
        has_store = self.history_store is not None

        if has_store:
            bounds = self.history_store.bounds()
            if bounds:
                min_date = bounds[0].date()
                max_date = bounds[1].date()
            else:
                min_date = max_date = datetime.date.today()
        else:
            min_date = max_date = datetime.date.today()

        # Build range options with translated labels.
        range_options = [
            {"label": t("range.24h"), "value": "24h"},
            {"label": t("range.7d"), "value": "7d"},
            {"label": t("range.30d"), "value": "30d"},
            {"label": t("range.all"), "value": "all"},
            {"label": t("range.custom"), "value": "custom"},
        ]

        # Subtitle depends on whether history is available.
        description = t("history.description") if has_store else t("history.unavailable")

        return html.Div(
            className="history-section",
            children=[
                html.Div(
                    className="section-heading",
                    children=[
                        html.H2(id="history-heading", children=t("history.heading")),
                        html.P(
                            id="history-description",
                            children=description,
                        ),
                    ],
                ),
                # Range controls — only visible when history_store exists.
                html.Div(
                    className="history-controls",
                    id="history-controls-wrapper",
                    style={"display": "flex" if has_store else "none"},
                    children=[
                        dcc.RadioItems(
                            id="history-range",
                            options=range_options,
                            value="24h",
                            inline=True,
                            className="history-range",
                        ),
                        html.Div(
                            id="history-custom-range",
                            className="history-custom-range",
                            style={"display": "none"},
                            children=[
                                html.Span(
                                    id="history-custom-range-label",
                                    className="history-custom-range__label",
                                    children=t("range.label"),
                                ),
                                dcc.DatePickerRange(
                                    id="history-date-range",
                                    min_date_allowed=min_date,
                                    max_date_allowed=max_date,
                                    start_date=min_date,
                                    end_date=max_date,
                                    display_format="YYYY-MM-DD",
                                    updatemode="bothdates",
                                    className="history-date-range",
                                ),
                            ],
                        ),
                    ],
                ),
                # Unavailable message — only visible when history_store is None.
                html.Div(
                    className="history-message",
                    id="history-unavailable-wrapper",
                    style={"display": "block" if not has_store else "none"},
                    children=html.P(
                        id="history-start-logger-msg",
                        children=t("history.start_logger"),
                    ),
                ),
                html.Div(id="history-cards", className="history-cards"),
                dcc.Graph(
                    id="history-graph",
                    className="graph-container",
                ),
                dcc.Interval(
                    id="history-interval",
                    interval=60 * 1000,  # in milliseconds
                    n_intervals=0,
                ),
            ],
        )

    @staticmethod
    def _build_figure(
        x, soc_values, load_values, pv_values, t, *, hovermode=None, empty=False
    ):
        """Build a Plotly figure with SOC and power traces (light theme).

        Parameters
        ----------
        x : list
            X-axis values (indices or datetimes).
        soc_values, load_values, pv_values : list
            Y-axis data for each trace.
        t : I18n
            Translator instance for trace names.
        hovermode : str or None
            Pass ``"x unified"`` to enable unified hover (history view).
        empty : bool
            When true, adds a "no data" annotation (history view).
        """
        trace_soc = go.Scatter(
            x=x,
            y=soc_values,
            mode="lines",
            name=t("card.soc"),
            yaxis="y",
            line={"color": "#198b43", "width": 2},
        )
        trace_load = go.Scatter(
            x=x,
            y=load_values,
            mode="lines",
            name=t("card.load_power"),
            yaxis="y2",
            line={"color": "#b82d35", "width": 2},
        )
        trace_pv = go.Scatter(
            x=x,
            y=pv_values,
            mode="lines",
            name=t("card.solar_power"),
            yaxis="y2",
            line={"color": "#3b5cf6", "width": 2},
        )

        power_values = [
            v for v in load_values + pv_values if v is not None
        ]
        power_range = [0, max(power_values, default=0) * 1.1]

        layout = go.Layout(
            xaxis={
                "showgrid": True,
                "gridcolor": "#0000001a",
                "gridwidth": 1,
                "zeroline": False,
                "title": None,
                "tickfont": {"size": 12, "color": "#5c5c5c"},
            },
            yaxis={
                "title": "SOC (%)",
                "side": "left",
                "range": [0, 100],
                "showgrid": True,
                "gridcolor": "#0000001a",
                "gridwidth": 1,
                "zeroline": False,
                "tickfont": {"size": 12, "color": "#5c5c5c"},
            },
            yaxis2={
                "title": "Power (W)",
                "side": "right",
                "overlaying": "y",
                "range": power_range,
                "showgrid": False,
                "tickfont": {"size": 12, "color": "#5c5c5c"},
            },
            legend={
                "orientation": "h",
                "yanchor": "bottom",
                "y": 1.02,
                "xanchor": "right",
                "x": 1,
                "font": {"size": 12, "color": "#161616"},
            },
            plot_bgcolor="#ffffff",
            paper_bgcolor="#ffffff",
            font={"family": '"IBM Plex Mono", ui-monospace, monospace', "size": 12},
            margin={"t": 40, "b": 40, "l": 60, "r": 60},
        )
        if hovermode:
            layout.hovermode = hovermode

        figure = go.Figure(data=[trace_soc, trace_load, trace_pv], layout=layout)
        if empty:
            figure.add_annotation(
                text=t("history.no_data"),
                showarrow=False,
                xref="paper",
                yref="paper",
                x=0.5,
                y=0.5,
                font={"size": 14, "color": "#5c5c5c"},
            )
        return figure

    @staticmethod
    def _parse_date(value):
        """Parse an ISO date string (YYYY-MM-DD) into a datetime, or return None."""
        if not value:
            return None
        try:
            return datetime.datetime.strptime(str(value)[:10], "%Y-%m-%d")
        except ValueError:
            return None

    def _resolve_history_range(self, range_value, start_date, end_date):
        """Translate the selected timespan option into (start, end) datetimes.

        A ``None`` bound means "unbounded" and is used by the "All time" option.
        """
        now = datetime.datetime.now()
        if range_value == "24h":
            return now - datetime.timedelta(hours=24), now
        if range_value == "7d":
            return now - datetime.timedelta(days=7), now
        if range_value == "30d":
            return now - datetime.timedelta(days=30), now
        if range_value == "all":
            return None, None

        start = self._parse_date(start_date)
        end = self._parse_date(end_date)
        if start is None or end is None:
            return None, None
        if start > end:
            start, end = end, start
        # Make the end date inclusive of the whole day.
        end = end + datetime.timedelta(days=1) - datetime.timedelta(seconds=1)
        return start, end

    @staticmethod
    def _create_history_figure(points, t: I18n):
        """Build a Plotly figure from aggregated historic points (light theme)."""
        timestamps = [point["timestamp"] for point in points]
        soc_values = [point["soc"] for point in points]
        load_values = [point["load_power"] for point in points]
        pv_values = [point["pv_power"] for point in points]

        return Dashboard._build_figure(
            timestamps,
            soc_values,
            load_values,
            pv_values,
            t,
            hovermode="x unified",
            empty=not points,
        )

    def _create_history_cards(self, totals, t: I18n):
        """Build the metric cards summarising energy over the history range."""
        return html.Div(
            className="register-sections",
            children=[
                dbc.Row(
                    [
                        dbc.Col(
                            Card(
                                t("history.energy_production"),
                                f"{totals['energy_solar']:,.1f}",
                                "kWh",
                            ),
                            md=6,
                        ),
                        dbc.Col(
                            Card(
                                t("history.energy_consumption"),
                                f"{totals['energy_used']:,.1f}",
                                "kWh",
                            ),
                            md=6,
                        ),
                    ]
                ),
            ],
        )

    def _update_history(
        self, range_value, start_date, end_date, n_intervals, lang
    ):  # pylint: disable=unused-argument
        """Refresh the historic cards and graph, and toggle the date pickers."""
        t = I18n(lang)
        custom_style = (
            {"display": "flex"} if range_value == "custom" else {"display": "none"}
        )
        start, end = self._resolve_history_range(range_value, start_date, end_date)
        points = self.history_store.series(start, end)
        totals = self.history_store.energy_totals(start, end)
        return (
            self._create_history_cards(totals, t),
            self._create_history_figure(points, t),
            custom_style,
        )

    @staticmethod
    def _create_status_indicator(state: str, t: I18n):
        """Build the pill indicating whether the inverter is live or unreachable.

        ``state`` is one of ``"live"``, ``"offline"`` or ``"connecting"``.
        """
        labels = {
            "live": t("status.live"),
            "offline": t("status.offline"),
            "connecting": t("status.connecting"),
        }
        label = labels.get(state, labels["connecting"])
        return html.Div(
            className=f"status-pill status-pill--{state}",
            children=label,
        )

    def _read_inverter_data(self):
        """Read inverter registers and return the data dict, or None on failure."""
        with self._inverter_lock:
            return self._read_inverter_data_impl()

    def _read_inverter_data_impl(self):
        """Unlocked implementation of _read_inverter_data."""
        if not self.inverter.is_reachable():
            log(
                f"Inverter at {self.inverter_ip} is not reachable.",
                "DASHBOARD",
                "WARNING",
            )
            return None
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

    def _find_inverter(self):
        """Search the local network for the inverter, tolerating scan errors."""
        try:
            return Client.search_inverter(self.inverter_ip + "/24")
        # pylint: disable=broad-exception-caught
        except Exception as e:
            log(f"Inverter re-discovery failed: {e}", "DASHBOARD", "WARNING")
            return None

    def _handle_read_failure(self, t: I18n):
        """Log failure, attempt re-discovery, and return an error card div."""
        log(
            f"Failed to read inverter data from {self.inverter_ip}.",
            "DASHBOARD",
            "ERROR",
        )
        with self._inverter_lock:
            now = datetime.datetime.now()
            search_due = (
                self._last_inverter_search is None
                or (now - self._last_inverter_search).total_seconds() >= 60
            )
            if search_due:
                self._last_inverter_search = now
                log(
                    "Searching for inverter on the network...", "DASHBOARD", "INFO"
                )
                result = self._find_inverter()
            else:
                result = None
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
                children=t("error.reading", seconds=self.polling_interval),
            ),
            go.Figure(),
            self._create_status_indicator("offline", t),
        )

    def _update_dashboard(self, n_intervals, lang):  # pylint: disable=unused-argument
        """Read inverter data and return updated cards, graph, and status."""
        t = I18n(lang)
        inverter_data = self._read_inverter_data()
        if inverter_data is None:
            return self._handle_read_failure(t)

        self.history_data["soc"].append(inverter_data["soc"])
        self.history_data["load_power"].append(inverter_data["load_power"])
        self.history_data["pv_power"].append(
            inverter_data["pv1_power"] + inverter_data["pv2_power"]
        )
        if len(self.history_data["soc"]) > 100:
            self.history_data["soc"].pop(0)
            self.history_data["load_power"].pop(0)
            self.history_data["pv_power"].pop(0)

        cards = html.Div(
            className="register-sections",
            children=[
                dbc.Row(
                    [
                        dbc.Col(Card(t("card.soc"), inverter_data["soc"], "%"), md=4),
                        dbc.Col(
                            Card(t("card.load_power"), inverter_data["load_power"], "W"), md=4
                        ),
                        dbc.Col(
                            Card(
                                t("card.solar_power"),
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
                                t("card.daily_production"),
                                inverter_data["daily_production"] / 10.0,
                                "kWh",
                            ),
                            md=4,
                        ),
                        dbc.Col(
                            Card(
                                t("card.daily_consumption"),
                                inverter_data["daily_consumption"] / 10.0,
                                "kWh",
                            ),
                            md=4,
                        ),
                        dbc.Col(
                            Card(
                                t("card.total_production"),
                                inverter_data["total_production"] / 10.0,
                                "kWh",
                            ),
                            md=4,
                        ),
                    ]
                ),
            ],
        )

        return cards, self._build_figure(
            list(range(len(self.history_data["soc"]))),
            self.history_data["soc"],
            self.history_data["load_power"],
            self.history_data["pv_power"],
            t,
        ), self._create_status_indicator("live", t)

    def _switch_language(self, en_clicks, ca_clicks, current_lang):  # pylint: disable=unused-argument
        """Handle language-switcher clicks and update all translatable text."""
        ctx = callback_context
        if not ctx.triggered:
            raise dash.exceptions.PreventUpdate

        button_id = ctx.triggered[0]["prop_id"].split(".")[0]
        new_lang: Lang = "en" if button_id == "lang-en" else "ca"

        if new_lang == current_lang:
            raise dash.exceptions.PreventUpdate

        t = I18n(new_lang)

        range_options = [
            {"label": t("range.24h"), "value": "24h"},
            {"label": t("range.7d"), "value": "7d"},
            {"label": t("range.30d"), "value": "30d"},
            {"label": t("range.all"), "value": "all"},
            {"label": t("range.custom"), "value": "custom"},
        ]

        active_class = "lang-switcher__option lang-switcher__option--active"
        base_class = "lang-switcher__option"
        en_class = active_class if new_lang == "en" else base_class
        ca_class = active_class if new_lang == "ca" else base_class

        return (
            new_lang,
            t("hero.title"),
            t("hero.subtitle"),
            t("live.heading"),
            t("live.description", seconds=self.polling_interval),
            t("history.heading"),
            t("history.description") if self.history_store else t("history.unavailable"),
            range_options,
            t("range.label"),
            t("history.start_logger"),
            en_class,
            ca_class,
        )

    def run(self, dashboard_host: str = "127.0.0.1"):
        """Start the Dash development server."""
        self.app.run(
            host=dashboard_host,
            debug=False,
            use_reloader=False,
            dev_tools_hot_reload=False,
        )
