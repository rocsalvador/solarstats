from dash import html
import dash_bootstrap_components as dbc


class Card(dbc.Card):
    def __init__(self, title: str, value, unit: str = "", **kwargs):
        class_name = kwargs.pop("className", "")
        kwargs["className"] = " ".join(
            part for part in ["register-card", class_name] if part
        )

        super().__init__(**kwargs)
        reading_children = [
            html.Span(str(value), className="register-card__value"),
        ]
        if unit:
            reading_children.append(html.Span(unit, className="register-card__unit"))

        self.children = dbc.CardBody(
            [
                html.Div(title, className="register-card__title"),
                html.Div(reading_children, className="register-card__reading"),
            ]
        )
