# ==============================================================
# dashboard.py — ThingsBoard-style Real-Time Sensor Dashboard
# ==============================================================
# Terminal 1 → python app_subscriber.py   (MQTT listener)
# Terminal 2 → python dashboard.py        (Dash web dashboard)
# ==============================================================

import os
import pandas as pd
import plotly.graph_objects as go
import dash
from dash import dcc, html, Input, Output, callback
import logging

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CSV_PATH = os.path.join(BASE_DIR, "sensor_data_room1.csv")

REFRESH_INTERVAL = 2_000
ROLLING_WINDOW   = 10

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

# ─── Palette ────────────────────────────────────────────────
C = {
    "page":      "#f4f6f9",
    "card":      "#ffffff",
    "border":    "#e8eaf0",
    "text":      "#1a2035",
    "muted":     "#8c9ab0",
    "temp_raw":  "rgba(98,116,242,0.30)",
    "temp_ma":   "#6274f2",               # indigo – temperature
    "humi_raw":  "rgba(30,200,160,0.30)",
    "humi_ma":   "#1ec8a0",               # teal – humidity
    "grid":      "#eef0f5",
    "plot_bg":   "#f9fafc",
}
LW = 2.0   # equal line width for raw & smooth


# ─── Helpers (defined BEFORE layout) ────────────────────────
def _legend_line(color: str, faded: bool):
    """Small horizontal line swatch for the custom legend row."""
    return html.Div(style={
        "width": "26px", "height": "2px",
        "background": color,
        "opacity": "0.38" if faded else "1",
        "borderRadius": "2px",
    })


def _legend_item(color: str, label: str, faded: bool = False):
    return html.Div(
        style={"display": "flex", "alignItems": "center", "gap": "7px"},
        children=[
            _legend_line(color, faded),
            html.Span(label, style={"fontSize": "0.75rem", "color": C["muted"]}),
        ],
    )


def _stat_card(label, value, unit, sub, icon, color):
    bg = color + "1a"   # ~10 % opacity
    return html.Div(
        style={
            "background": C["card"], "border": f"1px solid {C['border']}",
            "borderRadius": "10px", "padding": "16px 18px",
            "display": "flex", "alignItems": "center", "gap": "14px",
        },
        children=[
            html.Div(
                style={
                    "width": "48px", "height": "48px", "borderRadius": "50%",
                    "background": bg, "display": "flex",
                    "alignItems": "center", "justifyContent": "center",
                    "fontSize": "1.3rem", "flexShrink": "0",
                },
                children=icon,
            ),
            html.Div([
                html.P(label, style={
                    "fontSize": "0.70rem", "color": C["muted"], "fontWeight": "500",
                    "textTransform": "uppercase", "letterSpacing": "0.4px",
                    "marginBottom": "3px",
                }),
                html.Div(
                    style={"display": "flex", "alignItems": "baseline", "gap": "3px"},
                    children=[
                        html.Span(str(value), style={
                            "fontSize": "1.55rem", "fontWeight": "700",
                            "color": C["text"], "lineHeight": "1",
                        }),
                        html.Span(unit, style={"fontSize": "0.85rem", "color": C["muted"]}),
                    ],
                ),
                html.P(sub, style={"fontSize": "0.68rem", "color": C["muted"], "marginTop": "2px"}),
            ]),
        ],
    )


def _load_data():
    if not os.path.exists(CSV_PATH):
        return None
    try:
        df = pd.read_csv(CSV_PATH, parse_dates=["timestamp"])
        if df.empty or not {"temperature", "humidity", "timestamp"}.issubset(df.columns):
            return None
        df["temp_ma"] = df["temperature"].rolling(ROLLING_WINDOW).mean()
        df["humi_ma"] = df["humidity"].rolling(ROLLING_WINDOW).mean()
        return df
    except Exception as e:
        logging.warning("CSV error: %s", e)
        return None


def _empty_figure(msg="Menunggu data sensor…"):
    fig = go.Figure()
    fig.update_layout(
        annotations=[dict(text=msg, xref="paper", yref="paper", x=0.5, y=0.5,
                          showarrow=False, font=dict(size=15, color=C["muted"],
                          family="Roboto"))],
        plot_bgcolor=C["plot_bg"], paper_bgcolor="white",
        font=dict(family="Roboto"),
        height=390, margin=dict(l=55, r=55, t=15, b=40),
    )
    return fig


# ─── Dash App ────────────────────────────────────────────────
app = dash.Dash(__name__, title="AIoT Monitor", update_title=None)
app.index_string = """
<!DOCTYPE html>
<html>
  <head>
    {%metas%}
    <title>{%title%}</title>
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link href="https://fonts.googleapis.com/css2?family=Roboto:wght@300;400;500;700&display=swap" rel="stylesheet">
    {%favicon%}
    {%css%}
    <style>
      *, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }
      body { font-family: 'Roboto', sans-serif; background: #f4f6f9; color: #1a2035; }
    </style>
  </head>
  <body>
    {%app_entry%}
    <footer>{%config%}{%scripts%}{%renderer%}</footer>
  </body>
</html>
"""

# ─── Layout ─────────────────────────────────────────────────
app.layout = html.Div(
    style={"maxWidth": "1080px", "margin": "0 auto", "padding": "28px 20px"},
    children=[

        # ══ PAGE HEADER ═════════════════════════════════════
        html.Div(style={"marginBottom": "20px"}, children=[
            html.H1("AIoT Secure — Room 1 Monitor",
                    style={"fontSize": "1.35rem", "fontWeight": "500",
                           "color": C["text"]}),
            html.P(id="status-badge",
                   style={"fontSize": "0.78rem", "color": C["muted"], "marginTop": "3px"}),
        ]),

        # ══ STAT CARDS ══════════════════════════════════════
        html.Div(
            id="summary-cards",
            style={
                "display": "grid",
                "gridTemplateColumns": "repeat(4, 1fr)",
                "gap": "14px",
                "marginBottom": "20px",
            },
        ),

        # ══ CHART PANEL ═════════════════════════════════════
        html.Div(
            style={
                "background": C["card"],
                "border": f"1px solid {C['border']}",
                "borderRadius": "10px",
                "padding": "18px 18px 10px",
            },
            children=[
                # chart title + badge
                html.Div(
                    style={"display": "flex", "alignItems": "center",
                           "justifyContent": "space-between", "marginBottom": "2px"},
                    children=[
                        html.H2("Analisis Suhu & Kelembapan Real-Time: Raw vs Smooth",
                                style={"fontSize": "0.95rem", "fontWeight": "500",
                                       "color": C["text"]}),
                        html.Span(
                            f"MA window = {ROLLING_WINDOW}",
                            style={"fontSize": "0.72rem", "color": C["muted"],
                                   "background": C["page"],
                                   "border": f"1px solid {C['border']}",
                                   "borderRadius": "20px", "padding": "3px 10px"},
                        ),
                    ],
                ),

                # the main chart (single screen, dual Y)
                dcc.Graph(
                    id="live-chart",
                    config={"displayModeBar": False},
                    style={"marginLeft": "-6px"},
                ),

                # custom legend row below chart (like ThingsBoard)
                html.Div(
                    style={"display": "flex", "gap": "24px", "paddingBottom": "8px",
                           "paddingLeft": "6px", "flexWrap": "wrap"},
                    children=[
                        _legend_item(C["temp_ma"], "Raw Temperature",         faded=True),
                        _legend_item(C["temp_ma"], "Rolling Mean Suhu",       faded=False),
                        _legend_item(C["humi_ma"], "Raw Humidity",            faded=True),
                        _legend_item(C["humi_ma"], "Rolling Mean Kelembapan", faded=False),
                    ],
                ),
            ],
        ),

        dcc.Interval(id="auto-refresh", interval=REFRESH_INTERVAL, n_intervals=0),
    ],
)


# ─── Callback ────────────────────────────────────────────────
@callback(
    Output("live-chart",    "figure"),
    Output("status-badge",  "children"),
    Output("summary-cards", "children"),
    Input("auto-refresh",   "n_intervals"),
)
def update_dashboard(n):
    df = _load_data()

    if df is None:
        return _empty_figure(), f"⏳ Tick #{n} — belum ada data", []

    last_ts  = df["timestamp"].iloc[-1].strftime("%d %b %Y, %H:%M:%S")
    n_rows   = len(df)
    avg_temp = round(df["temperature"].mean(), 2)
    avg_humi = round(df["humidity"].mean(), 2)
    cur_temp = round(df["temperature"].iloc[-1], 2)
    cur_humi = round(df["humidity"].iloc[-1], 2)

    # ── Single figure, dual Y-axes ──────────────────────────
    fig = go.Figure()

    # — Temperature (left Y) —
    fig.add_trace(go.Scatter(
        x=df["timestamp"], y=df["temperature"],
        mode="lines", name="Raw Temp",
        line=dict(color=C["temp_raw"], width=LW),
        yaxis="y1", showlegend=False,
        hovertemplate="%{y:.2f}°C<extra>Raw Temp</extra>",
    ))
    fig.add_trace(go.Scatter(
        x=df["timestamp"], y=df["temp_ma"],
        mode="lines", name="Rolling Mean Suhu",
        line=dict(color=C["temp_ma"], width=LW),
        yaxis="y1", showlegend=False,
        hovertemplate="%{y:.2f}°C<extra>Smooth Temp</extra>",
    ))

    # — Humidity (right Y) —
    fig.add_trace(go.Scatter(
        x=df["timestamp"], y=df["humidity"],
        mode="lines", name="Raw Humi",
        line=dict(color=C["humi_raw"], width=LW),
        yaxis="y2", showlegend=False,
        hovertemplate="%{y:.1f}%<extra>Raw Humi</extra>",
    ))
    fig.add_trace(go.Scatter(
        x=df["timestamp"], y=df["humi_ma"],
        mode="lines", name="Rolling Mean Humi",
        line=dict(color=C["humi_ma"], width=LW),
        yaxis="y2", showlegend=False,
        hovertemplate="%{y:.1f}%<extra>Smooth Humi</extra>",
    ))

    fig.update_layout(
        height=390,
        plot_bgcolor=C["plot_bg"],
        paper_bgcolor="white",
        font=dict(family="Roboto", color=C["text"]),
        margin=dict(l=55, r=60, t=12, b=42),
        hovermode="x unified",
        hoverlabel=dict(font_family="Roboto", bgcolor="white",
                        bordercolor=C["border"]),
        xaxis=dict(
            gridcolor=C["grid"], linecolor=C["border"],
            tickfont=dict(size=10, color=C["muted"]),
        ),
        yaxis=dict(
            title=dict(text="Suhu (°C)", font=dict(size=11, color=C["temp_ma"])),
            gridcolor=C["grid"], linecolor=C["border"],
            tickfont=dict(size=10, color=C["temp_ma"]),
            side="left",
        ),
        yaxis2=dict(
            title=dict(text="Kelembapan (%)", font=dict(size=11, color=C["humi_ma"])),
            overlaying="y", side="right",
            gridcolor="rgba(0,0,0,0)",
            linecolor=C["border"],
            tickfont=dict(size=10, color=C["humi_ma"]),
        ),
        showlegend=False,
    )

    status = f"🔄 Update #{n}  ·  {last_ts}  ·  {n_rows} titik data"

    cards = [
        _stat_card("Suhu Rata-Rata", avg_temp, "°C", "Keseluruhan sesi",  "🌡", C["temp_ma"]),
        _stat_card("Suhu Terkini",   cur_temp, "°C", "Pembacaan terakhir","📍", "#f59e0b"),
        _stat_card("Humi Rata-Rata", avg_humi, "%",  "Keseluruhan sesi",  "💧", C["humi_ma"]),
        _stat_card("Humi Terkini",   cur_humi, "%",  "Pembacaan terakhir","📍", "#6366f1"),
    ]

    return fig, status, cards


if __name__ == "__main__":
    logging.info("Dashboard → http://127.0.0.1:8050")
    app.run(debug=False, host="0.0.0.0", port=8050)
