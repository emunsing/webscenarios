from dash import Dash, html, dcc, Input, Output, State, MATCH, ALL, ctx
import dash_bootstrap_components as dbc
import attrs
import cattrs
import hashlib
import json
from typing import Dict, Any, Optional

# Computation
@attrs.define
class OutputData:
    performance: float = 0.0
    total_expense: float = 0.0
    monthly_payment: float = 0.0

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
    _previous_output: Optional[OutputData] = attrs.field(default=None)
    
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
        # Remove _previous_output from export since it's runtime-only
        if '_previous_output' in data:
            del data['_previous_output']
        return json.dumps(data, indent=2)
    
    @classmethod
    def from_json(cls, json_str: str) -> 'ScenarioSettings':
        """Load from JSON string"""
        data = json.loads(json_str)
        return cattrs.structure(data, cls)
    
    def copy(self) -> 'ScenarioSettings':
        """Create a deep copy"""
        return attrs.evolve(self)

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

    # Result consolidation using attrs constructor
    return OutputData(
        performance=performance,
        total_expense=principal,
        monthly_payment=payment
    )

# Dash app
app = Dash(__name__, external_stylesheets=[dbc.themes.BOOTSTRAP])
app.layout = html.Div([
    html.H2("Scenario Comparison with Collapsible Sections"),
    html.Button("Add scenario", id="add-scenario-btn", n_clicks=0),
    html.Div(id="scenarios-container", children=[]),
    # Hidden div to store scenario data
    dcc.Store(id="scenarios-state", data={}),
    # Hidden download component for exports
    dcc.Download(id="download-dataframe-csv")
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
    # Serialize without _previous_output to avoid None issues
    scenario_dict = attrs.asdict(new_scenario, filter=lambda attr, value: attr.name != '_previous_output')
    scenarios_dict[idx] = scenario_dict
    
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
        html.Button("Copy", id={"type": "copy-btn", "index": idx}, n_clicks=0,
                   style={"marginLeft": "10px", "backgroundColor": "#007bff", "color": "white", 
                         "border": "none", "borderRadius": "4px", "padding": "4px 8px"}),
        html.Button("Export", id={"type": "export-btn", "index": idx}, n_clicks=0,
                   style={"marginLeft": "10px", "backgroundColor": "#28a745", "color": "white", 
                         "border": "none", "borderRadius": "4px", "padding": "4px 8px"}),
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

# Callback to update scenario state when run is clicked
@app.callback(
    Output("scenarios-state", "data", allow_duplicate=True),
    Input({"type": "run-btn", "index": ALL}, "n_clicks"),
    [State("scenarios-state", "data"),
     State({"type": "input-x", "index": ALL}, "value"),
     State({"type": "input-y", "index": ALL}, "value"),
     State({"type": "input-years", "index": ALL}, "value"),
     State({"type": "input-interest", "index": ALL}, "value")],
    prevent_initial_call=True,
)
def update_scenario_on_run(n_clicks_list, scenarios_data, x_values, y_values, years_values, interest_values):
    # Check if any run button was actually clicked (n_clicks > 0)
    if not any(n_clicks > 0 for n_clicks in n_clicks_list):
        return scenarios_data
    
    # Find which button was clicked
    if not ctx.triggered:
        return scenarios_data
    
    triggered_prop = ctx.triggered[0]["prop_id"]
    if "run-btn" not in triggered_prop:
        return scenarios_data
    
    # Extract the index of the scenario that was run
    idx = triggered_prop.split('"index":')[1].split(',')[0].strip('"')
    
    # Get the corresponding input values
    button_index = int(idx)
    if button_index >= len(x_values):
        return scenarios_data
    
    x_val = x_values[button_index]
    y_val = y_values[button_index]
    years = years_values[button_index]
    interest = interest_values[button_index]
    
    if None in (x_val, y_val, years, interest):
        return scenarios_data
    
    # Update the scenario in the store
    scenarios_dict = scenarios_data if scenarios_data else {}
    
    if idx not in scenarios_dict:
        scenario = ScenarioSettings()
    else:
        scenario = cattrs.structure(scenarios_dict[idx], ScenarioSettings)
    
    # Update scenario with current input values
    scenario.design.x = x_val
    scenario.design.y = y_val
    scenario.financial.years = years
    scenario.financial.interest_annual = interest
    
    # Update the cache
    scenario.check_updates()
    
    # Store updated scenario (without _previous_output for serialization)
    scenario_dict = attrs.asdict(scenario, filter=lambda attr, value: attr.name != '_previous_output')
    scenarios_dict[idx] = scenario_dict
    
    return scenarios_dict

# Callback to run scenario and show results
@app.callback(
    Output({"type": "output-div", "index": MATCH}, "children"),
    [Input({"type": "run-btn", "index": MATCH}, "n_clicks"),
     Input("scenarios-state", "data")],
    [State({"type": "input-x", "index": MATCH}, "value"),
     State({"type": "input-y", "index": MATCH}, "value"),
     State({"type": "input-years", "index": MATCH}, "value"),
     State({"type": "input-interest", "index": MATCH}, "value"),
     State({"type": "run-btn", "index": MATCH}, "id")],
    prevent_initial_call=True,
)
def run_scenario(n_clicks, scenarios_data, x_val, y_val, years, interest, button_id):
    if None in (x_val, y_val, years, interest):
        return "Please fill in all inputs."
    
    # For now, let's simplify and just run the computation
    # We'll add back the change detection once the basic functionality is working
    out = modeling_pipeline(x_val, y_val, years, interest, None, True, True)
    
    output_content = [
        html.Div(f"Total expense (principal) = {out.total_expense:.3f}"),
        html.Div(f"Monthly payment = {out.monthly_payment:.3f}"),
        html.Div("Note: Change detection temporarily disabled", 
                style={"color": "orange", "fontSize": "12px", "marginTop": "5px"})
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

# Callback to copy scenario
@app.callback(
    [Output("scenarios-container", "children", allow_duplicate=True),
     Output("scenarios-state", "data", allow_duplicate=True)],
    Input({"type": "copy-btn", "index": ALL}, "n_clicks"),
    [State("scenarios-container", "children"),
     State("scenarios-state", "data")],
    prevent_initial_call=True,
)
def copy_scenario(n_clicks_list, existing_children, scenarios_data):
    # Check if any copy button was actually clicked (n_clicks > 0)
    if not any(n_clicks > 0 for n_clicks in n_clicks_list):
        return existing_children, scenarios_data
    
    # Check which copy button was clicked
    if not ctx.triggered:
        return existing_children, scenarios_data
    
    triggered_prop = ctx.triggered[0]["prop_id"]
    if "copy-btn" not in triggered_prop:
        return existing_children, scenarios_data
    
    # Extract the index of the scenario to copy
    idx = triggered_prop.split('"index":')[1].split(',')[0].strip('"')
    
    # Get the scenario data to copy
    scenarios_dict = scenarios_data if scenarios_data else {}
    if idx not in scenarios_dict:
        return existing_children, scenarios_data
    
    # Create a copy of the scenario
    original_scenario = cattrs.structure(scenarios_dict[idx], ScenarioSettings)
    copied_scenario = original_scenario.copy()
    
    # Generate new index for the copy
    new_idx = str(len(existing_children))
    # Serialize without _previous_output to avoid None issues
    scenario_dict = attrs.asdict(copied_scenario, filter=lambda attr, value: attr.name != '_previous_output')
    scenarios_dict[new_idx] = scenario_dict
    
    # Create new scenario block with copied values
    copied_block = html.Div([
        html.H4(f"Scenario {new_idx} (copy of {idx})"),
        # Button to toggle design section
        dbc.Button("Design variables (x, y)", id={"type": "btn-toggle-design", "index": new_idx}, color="secondary", size="sm"),
        dbc.Collapse(
            dbc.Card(dbc.CardBody([
                dcc.Input(
                    id={"type": "input-x", "index": new_idx},
                    type="number",
                    placeholder="x",
                    value=copied_scenario.design.x,
                    style={"width": "80px"}
                ),
                dcc.Input(
                    id={"type": "input-y", "index": new_idx},
                    type="number",
                    placeholder="y",
                    value=copied_scenario.design.y,
                    style={"width": "80px", "marginLeft": "10px"}
                ),
            ])),
            id={"type": "collapse-design", "index": new_idx},
            is_open=False,
        ),
        html.Br(),
        # Button to toggle financial section
        dbc.Button("Financial model (years, interest)", id={"type": "btn-toggle-fin", "index": new_idx}, color="secondary", size="sm"),
        dbc.Collapse(
            dbc.Card(dbc.CardBody([
                dcc.Input(
                    id={"type": "input-years", "index": new_idx},
                    type="number",
                    placeholder="years",
                    value=copied_scenario.financial.years,
                    style={"width": "80px"}
                ),
                dcc.Input(
                    id={"type": "input-interest", "index": new_idx},
                    type="number",
                    placeholder="annual interest",
                    value=copied_scenario.financial.interest_annual,
                    step=0.001,
                    style={"width": "80px", "marginLeft": "10px"}
                ),
            ])),
            id={"type": "collapse-fin", "index": new_idx},
            is_open=False,
        ),
        html.Br(),
        html.Button("Run", id={"type": "run-btn", "index": new_idx}, n_clicks=0),
        html.Button("Copy", id={"type": "copy-btn", "index": new_idx}, n_clicks=0,
                   style={"marginLeft": "10px", "backgroundColor": "#007bff", "color": "white", 
                         "border": "none", "borderRadius": "4px", "padding": "4px 8px"}),
        html.Button("Export", id={"type": "export-btn", "index": new_idx}, n_clicks=0,
                   style={"marginLeft": "10px", "backgroundColor": "#28a745", "color": "white", 
                         "border": "none", "borderRadius": "4px", "padding": "4px 8px"}),
        html.Button("Remove", id={"type": "remove-btn", "index": new_idx}, n_clicks=0, 
                   style={"marginLeft": "10px", "backgroundColor": "#dc3545", "color": "white", 
                         "border": "none", "borderRadius": "4px", "padding": "4px 8px"}),
        html.Div(id={"type": "output-div", "index": new_idx}, style={"marginTop": "10px"})
    ],
    id={"type": "scenario-block", "index": new_idx},
    style={
        "display": "inline-block",
        "verticalAlign": "top",
        "padding": "10px",
        "border": "1px solid #888",
        "margin": "5px",
        "minWidth": "240px"
    })
    
    # Add the copied block to existing children
    existing_children.append(copied_block)
    
    return existing_children, scenarios_dict

# Callback to export scenario
@app.callback(
    Output("download-dataframe-csv", "data"),
    Input({"type": "export-btn", "index": ALL}, "n_clicks"),
    State("scenarios-state", "data"),
    prevent_initial_call=True,
)
def export_scenario(n_clicks_list, scenarios_data):
    # Check if any export button was actually clicked (n_clicks > 0)
    if not any(n_clicks > 0 for n_clicks in n_clicks_list):
        return None
    
    # Check which export button was clicked
    if not ctx.triggered:
        return None
    
    triggered_prop = ctx.triggered[0]["prop_id"]
    if "export-btn" not in triggered_prop:
        return None
    
    # Extract the index of the scenario to export
    idx = triggered_prop.split('"index":')[1].split(',')[0].strip('"')
    
    # Get the scenario data to export
    scenarios_dict = scenarios_data if scenarios_data else {}
    if idx not in scenarios_dict:
        return None
    
    # Get the scenario and convert to JSON
    scenario = cattrs.structure(scenarios_dict[idx], ScenarioSettings)
    json_data = scenario.to_json()
    
    # Return the download data
    return dict(content=json_data, filename=f"scenario_{idx}_export.json")

if __name__ == "__main__":
    app.run(debug=True)