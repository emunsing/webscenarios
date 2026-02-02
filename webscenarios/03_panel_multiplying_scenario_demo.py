import panel as pn
import attrs
import random

pn.extension(sizing_mode="stretch_width")


@attrs.define
class WebInputs:
    id: int | None = None
    x: float = 1.0
    optimize_sizing: bool = False
    n_scenarios_out: int = 1


@attrs.define
class WebOutputs:
    id: int | None = None
    x_squared: float | None = None


@attrs.define
class WebScenario:
    id: int
    inputs: WebInputs = attrs.field(default=WebInputs(id=id))
    outputs: WebOutputs = attrs.field(default=WebOutputs(id=id))

    def update_id(self, new_id: int) -> 'WebScenario':
        updated_inputs = attrs.evolve(self.inputs, id=new_id)
        updated_outputs = attrs.evolve(self.outputs, id=new_id)
        return attrs.evolve(self, id=new_id, inputs=updated_inputs, outputs=updated_outputs)


def compute_one_scenario(scenario_inputs: WebInputs) -> WebOutputs:
    x = scenario_inputs.x
    x_squared = x ** 2
    return WebOutputs(x_squared=x_squared, id=scenario_inputs.id)


def my_function(scenario_inputs: WebInputs) -> list[WebScenario]:
    if not scenario_inputs.optimize_sizing:
        # Single scenario computation
        outputs = compute_one_scenario(scenario_inputs)
        return [WebScenario(inputs=scenario_inputs, outputs=outputs, id=scenario_inputs.id)]
    else:
        # Optimization mode: create multiple scenarios with random x values
        results = []
        for i in range(scenario_inputs.n_scenarios_out):
            # Generate random x values between 0.1 and 10.0
            random_x = random.uniform(0.1, 10.0)
            random_inputs = attrs.evolve(scenario_inputs, x=random_x, id=scenario_inputs.id)
            outputs = compute_one_scenario(random_inputs)
            results.append(WebScenario(inputs=random_inputs, outputs=outputs, id=scenario_inputs.id))
        return results


def show_consolidated_results(all_outputs: list[WebOutputs]) -> str:
    """Generate a consolidated view of all scenario results"""
    if not all_outputs:
        return "No results available"

    results_text = "Consolidated Results:\n"
    for output in all_outputs:
        if output.x_squared is not None:
            results_text += f"Scenario {output.id}: x² = {output.x_squared:.4f}\n"
        else:
            results_text += f"Scenario {output.id}: Not computed\n"

    return results_text.strip()


# --- Scenario UI factory ---
def create_scenario(scenario_idx: int, scenario: WebScenario):
    inputs = scenario.inputs
    outputs = scenario.outputs

    x_input = pn.widgets.FloatInput(
        name=f"Scenario {scenario.id} (x)", value=inputs.x, width=100
    )

    # Optimization controls
    optimize_checkbox = pn.widgets.Checkbox(
        name="Optimize Sizing", value=inputs.optimize_sizing, width=120
    )
    n_scenarios_input = pn.widgets.IntInput(
        name="N Scenarios", value=inputs.n_scenarios_out, width=80,
        disabled=not inputs.optimize_sizing
    )

    compute_btn = pn.widgets.Button(name="Compute", button_type="primary", width=70)
    copy_btn = pn.widgets.Button(name="Copy", button_type="primary", width=70)
    remove_btn = pn.widgets.Button(name="Remove", button_type="danger", width=70)

    # Output field to display computation results
    output_x_squared = pn.widgets.StaticText(
        name=f"Output (x²)",
        value=str(outputs.x_squared) if outputs.x_squared is not None else "Not computed",
        width=120
    )

    # container for this scenario
    box = pn.Column(
        pn.Row(x_input, compute_btn, copy_btn, remove_btn),
        pn.Row(optimize_checkbox, n_scenarios_input),
        output_x_squared,
        sizing_mode="fixed",
        styles={"border": "2px solid #888", "padding": "10px", "margin": "10px"},
    )

    def collect_inputs() -> WebInputs:
        return WebInputs(
            x=x_input.value,
            id=scenario.id,
            optimize_sizing=optimize_checkbox.value,
            n_scenarios_out=n_scenarios_input.value
        )

    def collect_outputs() -> WebOutputs:
        computed_value = None
        if output_x_squared.value != "Not computed" and not output_x_squared.value.startswith("Error"):
            try:
                computed_value = float(output_x_squared.value)
            except ValueError:
                computed_value = None
        return WebOutputs(x_squared=computed_value, id=scenario.id)

    def to_web_scenario():
        scenario_inputs = collect_inputs()
        scenario_outputs = collect_outputs()
        return WebScenario(inputs=scenario_inputs, outputs=scenario_outputs, id=scenario.id)

    # Callback for optimize checkbox
    def on_optimize_change(event):
        n_scenarios_input.disabled = not optimize_checkbox.value

    # actions
    def do_compute(event):
        """Compute x**2 and display the result"""
        try:
            scenario_inputs = collect_inputs()
            results = my_function(scenario_inputs)

            # Update current scenario with first result
            updated_self = results[0]
            output_x_squared.value = str(updated_self.outputs.x_squared)
            scenario_outputs[scenario.id] = updated_self.outputs

            # If multiple results, create new scenarios for results[1:]
            if len(results) >= 1:
                max_idx = max(scenarios.keys()) if scenarios else 0
                for i, result_scenario in enumerate(results[1:], 1):
                    new_idx = max_idx + i
                    new_scenario = result_scenario.update_id(new_idx)
                    add_scenario(new_idx, new_scenario)
                    scenario_outputs[new_idx] = result_scenario.outputs

            # Update consolidated results
            update_consolidated_results()

        except Exception as e:
            output_x_squared.value = f"Error: {str(e)}"

    def do_copy(event):
        max_idx = max(scenarios.keys()) if scenarios else 0
        # Copy both the input value and the computed output
        current_scenario_snapshot = to_web_scenario()
        copied_scenario = current_scenario_snapshot.update_id(max_idx + 1)
        add_scenario(max_idx + 1, copied_scenario)

    def do_remove(event):
        scenarios.pop(scenario_idx)
        scenario_outputs.pop(scenario_idx, None)  # Remove from outputs registry
        refresh_scenarios()

    # Set up checkbox callback using param.watch
    optimize_checkbox.param.watch(on_optimize_change, 'value')
    compute_btn.on_click(do_compute)
    copy_btn.on_click(do_copy)
    remove_btn.on_click(do_remove)

    return box


# --- Scenario registry and container ---
scenarios = {}
scenario_outputs = {}  # Global registry to track outputs by scenario ID
scenarios_container = pn.Row(styles={"overflow-x": "auto", "flex-wrap": "nowrap"})

# Consolidated results display
consolidated_results_display = pn.widgets.StaticText(
    name="Consolidated Results",
    value="No results available",
    width=400,
    height=200,
    styles={"white-space": "pre-wrap", "font-family": "monospace"}
)


def update_consolidated_results():
    """Update the consolidated results display"""
    all_outputs = list(scenario_outputs.values())

    if all_outputs:
        results_text = show_consolidated_results(all_outputs)
        consolidated_results_display.value = results_text
    else:
        consolidated_results_display.value = "No results available"


def refresh_scenarios():
    """Rebuild the container from current scenario dict."""
    scenarios_container.objects = list(scenarios.values())
    update_consolidated_results()


def add_scenario(scenario_idx: int, scenario: WebScenario):
    scenarios[scenario_idx] = create_scenario(scenario_idx, scenario)
    refresh_scenarios()


# --- "Add Scenario" button ---
add_btn = pn.widgets.Button(name="Add Scenario", button_type="success")


def do_add(event):
    next_idx = max(scenarios.keys()) + 1 if scenarios else 1
    default_scenario = WebScenario(id=next_idx)
    add_scenario(scenario_idx=next_idx, scenario=default_scenario)


add_btn.on_click(do_add)

# --- App Layout ---
app = pn.Column(
    "# MVP: Dynamic Scenarios with x²",
    add_btn,
    scenarios_container,
    "## Consolidated Results",
    consolidated_results_display,
)

app.servable()

# Launch
if __name__ == "__main__":
    pn.serve(app, show=True)