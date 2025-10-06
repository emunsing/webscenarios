import panel as pn
import attrs

pn.extension(sizing_mode="stretch_width")


def my_function(x):
    return x ** 2


@attrs.define
class WebInputs:
    x: float = 1.0


@attrs.define
class WebOutputs:
    x_squared: float | None = None


@attrs.define
class WebScenario:
    inputs: WebInputs = attrs.field(default=WebInputs())
    outputs: WebOutputs = attrs.field(default=WebOutputs())


# --- Scenario UI factory ---
def create_scenario(idx, scenario: WebScenario):
    inputs = scenario.inputs
    outputs = scenario.outputs

    x_input = pn.widgets.FloatInput(
        name=f"Scenario {idx} (x)", value=inputs.x, width=100
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
        output_x_squared,
        sizing_mode="fixed",
        styles={"border": "2px solid #888", "padding": "10px", "margin": "10px"},
    )

    def to_web_scenario():
        computed_value = None
        if output_x_squared.value != "Not computed" and not output_x_squared.value.startswith("Error"):
            try:
                computed_value = float(output_x_squared.value)
            except ValueError:
                computed_value = None

        web_inputs = WebInputs(x=x_input.value)
        web_outputs = WebOutputs(x_squared=computed_value)

        return WebScenario(inputs=web_inputs, outputs=web_outputs)

    # actions
    def do_compute(event):
        """Compute x**2 and display the result"""
        try:
            result = my_function(x_input.value)
            output_x_squared.value = str(result)
        except Exception as e:
            output_x_squared.value = f"Error: {str(e)}"

    def do_copy(event):
        max_idx = max(scenarios.keys()) if scenarios else 0
        # Copy both the input value and the computed output
        current_scenario_snapshot = to_web_scenario()
        add_scenario(max_idx + 1, current_scenario_snapshot)

    def do_remove(event):
        scenarios.pop(idx)
        refresh_scenarios()

    compute_btn.on_click(do_compute)
    copy_btn.on_click(do_copy)
    remove_btn.on_click(do_remove)

    return box


# --- Scenario registry and container ---
scenarios = {}
scenarios_container = pn.Row(styles={"overflow-x": "auto", "flex-wrap": "nowrap"})


def refresh_scenarios():
    """Rebuild the container from current scenario dict."""
    scenarios_container.objects = list(scenarios.values())


def add_scenario(idx, scenario: WebScenario):
    scenarios[idx] = create_scenario(idx, scenario)
    refresh_scenarios()


# --- "Add Scenario" button ---
add_btn = pn.widgets.Button(name="Add Scenario", button_type="success")


def do_add(event):
    next_idx = max(scenarios.keys()) + 1 if scenarios else 1
    default_scenario = WebScenario()
    add_scenario(next_idx, default_scenario)


add_btn.on_click(do_add)

# --- App Layout ---
app = pn.Column(
    "# MVP: Dynamic Scenarios with x²",
    add_btn,
    scenarios_container,
)

app.servable()

# Launch
if __name__ == "__main__":
    pn.serve(app, show=True)