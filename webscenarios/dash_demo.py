from dash import Dash, html, dcc, Input, Output, State, MATCH, ALL, ctx
import dash_bootstrap_components as dbc
import attrs
import cattrs
import hashlib
import json
from typing import Dict, Any

# Settings classes with change detection
@attrs.define
class DesignSettings:
    x: float = 1.0
    y: float = 2.0
    
    def _hash(self) -> str:
        """Create hash for change detection"""
        data = attrs.asdict(self)
        return hashlib.md5(json.dumps(data, sort_keys=True).encode()).hexdigest()

@attrs.define  
class FinancialSettings:
    years: int = 10
    interest_annual: float = 0.05
    
    def _hash(self) -> str:
        """Create hash for change detection"""
        data = attrs.asdict(self)
        return hashlib.md5(json.dumps(data, sort_keys=True).encode()).hexdigest()

@attrs.define
class ScenarioSettings:
    design: DesignSettings = attrs.field(factory=DesignSettings)
    financial: FinancialSettings = attrs.field(factory=FinancialSettings)
    _design_hash: str = ""
    _financial_hash: str = ""
    
    def __attrs_post_init__(self):
        self._design_hash = self.design._hash()
        self._financial_hash = self.financial._hash()
    
    def check_updates(self) -> Dict[str, bool]:
        """Returns which groups have changed"""
        current_design_hash = self.design._hash()
        current_financial_hash = self.financial._hash()
        
        changes = {}
        if current_design_hash != self._design_hash:
            changes['design'] = True
            self._design_hash = current_design_hash
            
        if current_financial_hash != self._financial_hash:
            changes['financial'] = True  
            self._financial_hash = current_financial_hash
            
        return changes
    
    def to_json(self) -> str:
        """Export to JSON string"""
        data = attrs.asdict(self, filter=lambda attr, value: not attr.name.startswith('_'))
        return json.dumps(data, indent=2)
    
    @classmethod
    def from_json(cls, json_str: str) -> 'ScenarioSettings':
        """Load from JSON string"""
        data = json.loads(json_str)
        return cattrs.structure(data, cls)
    
    def copy(self) -> 'ScenarioSettings':
        """Create a deep copy"""
        return attrs.evolve(self)

# Computation
class OutputData:
    def __init__(self, performance=0.0, total_expense=0.0, monthly_payment=0.0):
        self.performance: float = performance
        self.total_expense: float = total_expense
        self.monthly_payment: float = monthly_payment

# Performance model
def performance_model(x, y):
    # In production this may take a long time to run the full design function.
    return x ** 1.2 + y ** 1.2

def financial_model(principal, years, interest_annual):
    periods = years * 12
    period_r = interest_annual / 12.0
    # guard: if interest = 0
    if period_r == 0:
        payment = principal / periods if periods > 0 else 0
    else:
        payment = principal * (period_r * (1 + period_r) ** periods) / ((1 + period_r) ** periods - 1)
    return payment

def modeling_pipeline(x, y, years, interest_annual, previous_output: OutputData | None, design_changed=True, financials_changed=True) -> OutputData:
    # Design variables: 
    if previous_output is None:
        previous_output = OutputData()

    if design_changed:
        performance = performance_model(x, y) # In production this may take a long time to run the full design function.
    else:
        performance = previous_output.performance

    # Financial model
    if financials_changed or design_changed:
        principal = x * y
        payment = financial_model(principal, years, interest_annual)
    else:
        principal = previous_output.total_expense
        payment = previous_output.monthly_payment

    # Result consolidation
    res = OutputData()
    res.performance = performance
    res.total_expense = principal
    res.monthly_payment = payment
    return res

# Dash app
app = Dash(__name__, external_stylesheets=[dbc.themes.BOOTSTRAP])
app.layout = html.Div([
    html.H2("Scenario Comparison with Collapsible Sections"),
    html.Button("Add scenario", id="add-scenario-btn", n_clicks=0),
    html.Div(id="scenarios-container", children=[]),
    # Hidden div to store scenario data
    dcc.Store(id="scenarios-state", data={})
])

# Callback to add scenario UI
@app.callback(
    [Output("scenarios-container", "children"),
     Output("scenarios-state", "data")],
    Input("add-scenario-btn", "n_clicks"),
    [State("scenarios-container", "children"),
     State("scenarios-state", "data")],
    prevent_initial_call=False,
)
def add_scenario(n_clicks, existing_children, scenarios_data):
    idx = str(n_clicks)
    
    # Create new scenario settings
    new_scenario = ScenarioSettings()
    
    # Convert scenarios data back to dict if needed
    scenarios_dict = scenarios_data if scenarios_data else {}
    scenarios_dict[idx] = cattrs.unstructure(new_scenario)
    
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
        html.Button("Remove", id={"type": "remove-btn", "index": idx}, n_clicks=0, 
                   style={"marginLeft": "10px", "backgroundColor": "#dc3545", "color": "white", 
                         "border": "none", "borderRadius": "4px", "padding": "4px 8px"}),
        html.Div(id={"type": "output-div", "index": idx}, style={"marginTop": "10px"})
    ],
    id={"type": "scenario-block", "index": idx},
    style={
        "display": "inline-block",
        "verticalAlign": "top",
        "padding": "10px",
        "border": "1px solid #888",
        "margin": "5px",
        "minWidth": "240px"
    })
    existing_children.append(block)
    return existing_children, scenarios_dict

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

# Callback to run scenario and show results
@app.callback(
    Output({"type": "output-div", "index": MATCH}, "children"),
    Input({"type": "run-btn", "index": MATCH}, "n_clicks"),
    [State({"type": "input-x", "index": MATCH}, "value"),
     State({"type": "input-y", "index": MATCH}, "value"),
     State({"type": "input-years", "index": MATCH}, "value"),
     State({"type": "input-interest", "index": MATCH}, "value")],
    prevent_initial_call=True,
)
def run_scenario(n_clicks, x_val, y_val, years, interest):
    if None in (x_val, y_val, years, interest):
        return "Please fill in all inputs."
    
    # For now, let's just run the computation without change detection
    # We'll add that back once we get the basic functionality working
    out = modeling_pipeline(x_val, y_val, years, interest)
    
    output_content = [
        html.Div(f"Total expense (principal) = {out.total_expense:.3f}"),
        html.Div(f"Monthly payment = {out.monthly_payment:.3f}")
    ]
    
    return html.Div(output_content)

# Callback to remove scenario
@app.callback(
    [Output("scenarios-container", "children", allow_duplicate=True),
     Output("scenarios-state", "data", allow_duplicate=True)],
    Input({"type": "remove-btn", "index": ALL}, "n_clicks"),
    [State("scenarios-container", "children"),
     State("scenarios-state", "data")],
    prevent_initial_call=True,
)
def remove_scenario(n_clicks_list, existing_children, scenarios_data):
    # Check if any remove button was actually clicked (n_clicks > 0)
    if not any(n_clicks > 0 for n_clicks in n_clicks_list):
        return existing_children, scenarios_data
    
    # Check which remove button was clicked
    if not ctx.triggered:
        return existing_children, scenarios_data
    
    triggered_prop = ctx.triggered[0]["prop_id"]
    if "remove-btn" not in triggered_prop:
        return existing_children, scenarios_data
    
    # Extract the index of the scenario to remove
    idx = triggered_prop.split('"index":')[1].split(',')[0].strip('"')
    
    # Remove from UI - filter out the scenario block with matching index
    new_children = []
    for child in existing_children:
        # Check if this is the scenario block we want to remove
        # Since child is a dict (serialized component), check for 'props' and 'id'
        if isinstance(child, dict) and 'props' in child:
            child_props = child['props']
            if 'id' in child_props:
                child_id = child_props['id']
                if isinstance(child_id, dict) and child_id.get('type') == 'scenario-block' and child_id.get('index') == idx:
                    continue  # Skip this scenario block
        new_children.append(child)
    
    # Remove from scenarios data
    scenarios_dict = scenarios_data if scenarios_data else {}
    if idx in scenarios_dict:
        del scenarios_dict[idx]
    
    return new_children, scenarios_dict

if __name__ == "__main__":
    app.run(debug=True)