from dash import Dash, html, dcc, Input, Output, State, MATCH, ALL, ctx
import dash_bootstrap_components as dbc

# Computation
class OutputData:
    def __init__(self, total_expense=0.0, monthly_payment=0.0):
        self.total_expense = total_expense
        self.monthly_payment = monthly_payment

def myfun(x, y, years, interest_annual) -> OutputData:
    principal = x * y
    periods = years * 12
    period_r = interest_annual / 12.0
    # guard: if interest = 0
    if period_r == 0:
        payment = principal / periods if periods > 0 else 0
    else:
        payment = principal * (period_r * (1 + period_r) ** periods) / ((1 + period_r) ** periods - 1)
    res = OutputData()
    res.total_expense = principal
    res.monthly_payment = payment
    return res

# Dash app
app = Dash(__name__, external_stylesheets=[dbc.themes.BOOTSTRAP])
app.layout = html.Div([
    html.H2("Scenario Comparison with Collapsible Sections"),
    html.Button("Add scenario", id="add-scenario-btn", n_clicks=0),
    html.Div(id="scenarios-container", children=[])
])

# Callback to add scenario UI
@app.callback(
    Output("scenarios-container", "children"),
    Input("add-scenario-btn", "n_clicks"),
    State("scenarios-container", "children"),
    prevent_initial_call=False,
)
def add_scenario(n_clicks, existing_children):
    idx = str(n_clicks)
    # Build a collapsible block for design and financial sections
    block = html.Div([
        html.H4(f"Scenario {idx}"),
        # Button to toggle design section
        dbc.Button("Design variables (x, y)", id={"type": "btn-toggle-design", "index": idx}, color="secondary", size="sm"),
        dbc.Collapse(
            dbc.Card(dbc.CardBody([
                dcc.Input(
                    id={"type": "input-x", "index": idx},
                    type="number",
                    placeholder="x",
                    value=1.0,
                    style={"width": "80px"}
                ),
                dcc.Input(
                    id={"type": "input-y", "index": idx},
                    type="number",
                    placeholder="y",
                    value=2.0,
                    style={"width": "80px", "marginLeft": "10px"}
                ),
            ])),
            id={"type": "collapse-design", "index": idx},
            is_open=False,
        ),
        html.Br(),
        # Button to toggle financial section
        dbc.Button("Financial model (years, interest)", id={"type": "btn-toggle-fin", "index": idx}, color="secondary", size="sm"),
        dbc.Collapse(
            dbc.Card(dbc.CardBody([
                dcc.Input(
                    id={"type": "input-years", "index": idx},
                    type="number",
                    placeholder="years",
                    value=10,
                    style={"width": "80px"}
                ),
                dcc.Input(
                    id={"type": "input-interest", "index": idx},
                    type="number",
                    placeholder="annual interest",
                    value=0.05,
                    step=0.001,
                    style={"width": "80px", "marginLeft": "10px"}
                ),
            ])),
            id={"type": "collapse-fin", "index": idx},
            is_open=False,
        ),
        html.Br(),
        html.Button("Run", id={"type": "run-btn", "index": idx}, n_clicks=0),
        html.Div(id={"type": "output-div", "index": idx}, style={"marginTop": "10px"})
    ],
    style={
        "display": "inline-block",
        "verticalAlign": "top",
        "padding": "10px",
        "border": "1px solid #888",
        "margin": "5px",
        "minWidth": "240px"
    })
    existing_children.append(block)
    return existing_children

# Callback to toggle design collapse
@app.callback(
    Output({"type": "collapse-design", "index": MATCH}, "is_open"),
    Input({"type": "btn-toggle-design", "index": MATCH}, "n_clicks"),
    State({"type": "collapse-design", "index": MATCH}, "is_open"),
)
def toggle_design(n_clicks, is_open):
    if n_clicks:
        return not is_open
    return is_open

# Callback to toggle financial collapse
@app.callback(
    Output({"type": "collapse-fin", "index": MATCH}, "is_open"),
    Input({"type": "btn-toggle-fin", "index": MATCH}, "n_clicks"),
    State({"type": "collapse-fin", "index": MATCH}, "is_open"),
)
def toggle_fin(n_clicks, is_open):
    if n_clicks:
        return not is_open
    return is_open

# Callback to run scenario
@app.callback(
    Output({"type": "output-div", "index": MATCH}, "children"),
    Input({"type": "run-btn", "index": MATCH}, "n_clicks"),
    State({"type": "input-x", "index": MATCH}, "value"),
    State({"type": "input-y", "index": MATCH}, "value"),
    State({"type": "input-years", "index": MATCH}, "value"),
    State({"type": "input-interest", "index": MATCH}, "value"),
    prevent_initial_call=True,
)
def run_scenario(n_clicks, x_val, y_val, years, interest):
    if None in (x_val, y_val, years, interest):
        return "Please fill in all inputs."
    out = myfun(x_val, y_val, years, interest)
    return html.Div([
        html.Div(f"Total expense (principal) = {out.total_expense:.3f}"),
        html.Div(f"Monthly payment = {out.monthly_payment:.3f}")
    ])

if __name__ == "__main__":
    app.run(debug=True)