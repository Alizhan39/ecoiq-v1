"""
plotly_visual_intelligence/services/theme.py — the one EcoIQ chart theme
every chart in this app uses. Colors are the EXACT existing design-system
tokens (static/css/ecoiq-institutional.css), not invented — a chart and a
badge for the same concept (e.g. "human review required") must always be
the same color across the whole platform.

Also centralizes the "meaning is never color-only" accessibility rule:
CATEGORY_SYMBOLS gives every semantic category (verified/estimated/warning/
danger/info) a marker symbol as well as a color, and every chart-building
function in charts.py is expected to put the same information in hover text
and/or an axis label too.
"""
IQ_BG = '#070b0f'
IQ_BG2 = '#0d1117'
IQ_BORDER = 'rgba(255,255,255,.10)'
IQ_TEXT = '#e2e8f0'
IQ_MUTED = '#64748b'
IQ_ACCENT = '#00e89a'     # verified / good / high confidence
IQ_WARN = '#f4a261'       # needs review / medium
IQ_DANGER = '#e63946'     # blocked / high risk / low confidence
IQ_INFO = '#58a6ff'       # neutral informational
IQ_PURPLE = '#a855f7'     # analytics / clustering
IQ_CYAN = '#06b6d4'       # evidence / secondary

CATEGORICAL_SEQUENCE = [IQ_ACCENT, IQ_INFO, IQ_WARN, IQ_PURPLE, IQ_CYAN, IQ_DANGER]

# Semantic color + marker symbol pairs — never color alone.
CATEGORY_STYLE = {
    'verified':  {'color': IQ_ACCENT, 'symbol': 'circle'},
    'estimated': {'color': IQ_WARN, 'symbol': 'diamond'},
    'warning':   {'color': IQ_WARN, 'symbol': 'triangle-up'},
    'danger':    {'color': IQ_DANGER, 'symbol': 'x'},
    'info':      {'color': IQ_INFO, 'symbol': 'circle'},
    'neutral':   {'color': IQ_MUTED, 'symbol': 'circle-open'},
}

FONT_FAMILY = "-apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif"


def base_layout(title=None, height=360, showlegend=True):
    """The one shared Plotly layout dict — every chart function starts from
    this via `go.Figure(layout=base_layout(...))` and only overrides what it
    genuinely needs (axis titles, chart-specific annotations)."""
    return {
        'template': 'plotly_dark',
        'paper_bgcolor': 'rgba(0,0,0,0)',
        'plot_bgcolor': 'rgba(0,0,0,0)',
        'font': {'family': FONT_FAMILY, 'color': IQ_TEXT, 'size': 12},
        'title': {'text': title, 'font': {'size': 14, 'color': '#fff'}} if title else None,
        'height': height,
        'margin': {'l': 60, 'r': 30, 't': 40 if title else 20, 'b': 40},
        'showlegend': showlegend,
        'legend': {'bgcolor': 'rgba(0,0,0,0)', 'font': {'color': IQ_MUTED, 'size': 11}},
        'xaxis': {'gridcolor': IQ_BORDER, 'zerolinecolor': IQ_BORDER, 'color': IQ_MUTED},
        'yaxis': {'gridcolor': IQ_BORDER, 'zerolinecolor': IQ_BORDER, 'color': IQ_MUTED},
        'hoverlabel': {'bgcolor': IQ_BG2, 'font': {'color': IQ_TEXT, 'family': FONT_FAMILY}, 'bordercolor': IQ_BORDER},
    }


def confidence_color(confidence):
    """One shared rule for what counts as low/medium/high confidence, used
    by every chart that colors a point/bar by confidence — so a company
    plotted red on the risk/opportunity matrix and red in the score chart
    means the same thing both places."""
    if confidence is None:
        return IQ_MUTED
    if confidence >= 70:
        return IQ_ACCENT
    if confidence >= 50:
        return IQ_WARN
    return IQ_DANGER


def to_html_fragment(fig, div_id):
    """Every chart is embedded via this — include_plotlyjs=False because
    plotly.min.js is loaded exactly once per page (see _styles.html), not
    once per chart."""
    return fig.to_html(full_html=False, include_plotlyjs=False, div_id=div_id, config={'displaylogo': False, 'responsive': True})
