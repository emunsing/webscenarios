from dash import Dash, html, dcc, Input, Output, State, MATCH, ALL, ctx
import dash
import uuid

# Your computation function
class OutputData:
    def __init__(self, res_1=0.0, res_2=0.0):
        self.res_1 = res_1
        self.res_2 = res_2

def myfun(x, y) -> OutputData:
    out = OutputData()
    out.res_1 = x * y
    out.res_2 = x - y
    return out

# Create the Dash app
app = Dash(__name__, suppress_callback_exceptions=True)

# Layout: button to add scenario, container div to hold scenario columns
app.layout = html.Div(
    [
        html.H2("Scenario Comparison Demo"),
        html.Button("Add scenario", id="add-scenario-btn", n_clicks=0),
        html.Div(id="scenarios-container", children=[]),
    ]
)

# Callback to add a new scenario UI block when the button is clicked
@app.callback(
    Output("scenarios-container", "children"),
    Input("add-scenario-btn", "n_clicks"),
    State("scenarios-container", "children"),
    prevent_initial_call=False,
)
def add_scenario(n_clicks, existing_children):
    # Each scenario gets a unique index (we can use n_clicks or uuid)
    idx = str(n_clicks)  # or str(uuid.uuid4())
    # Build a UI block (column) for this scenario
    new_block = html.Div(
        children=[
            html.H4(f"Scenario {idx}"),
            dcc.Input(
                id={"type": "input-x", "index": idx},
                type="number",
                placeholder="x",
                value=1,
                style={"width": "80px"},
            ),
            dcc.Input(
                id={"type": "input-y", "index": idx},
                type="number",
                placeholder="y",
                value=2,
                style={"width": "80px", "marginLeft": "10px"},
            ),
            html.Button(
                "Run",
                id={"type": "run-btn", "index": idx},
                n_clicks=0,
                style={"marginLeft": "10px"},
            ),
            html.Div(id={"type": "output-div", "index": idx}, style={"marginTop": "10px"}),
        ],
        style={
            "display": "inline-block",
            "verticalAlign": "top",
            "padding": "10px",
            "border": "1px solid #888",
            "margin": "5px",
        },
    )
    existing_children.append(new_block)
    return existing_children

# Callback to compute outputs when a scenario's “Run” button is clicked
@app.callback(
    Output({"type": "output-div", "index": MATCH}, "children"),
    Input({"type": "run-btn", "index": MATCH}, "n_clicks"),
    State({"type": "input-x", "index": MATCH}, "value"),
    State({"type": "input-y", "index": MATCH}, "value"),
    prevent_initial_call=True,
)
def run_one_scenario(n_clicks, x_val, y_val):
    # If x or y is None, do nothing
    if x_val is None or y_val is None:
        return "Please set x and y"
    # Compute
    out = myfun(x_val, y_val)
    # Return e.g. an HTML snippet
    return html.Div([
        html.Div(f"res_1 = {out.res_1:.3f}"),
        html.Div(f"res_2 = {out.res_2:.3f}")
    ])

if __name__ == "__main__":
    app.run(debug=True)