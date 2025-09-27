import panel as pn

pn.extension(sizing_mode="stretch_width")

# --- Scenario UI factory ---
def create_scenario(idx, value=1.0):
    x_input = pn.widgets.FloatInput(
        name=f"Scenario {idx} (x)", value=value, width=100
    )
    copy_btn = pn.widgets.Button(name="Copy", button_type="primary", width=70)
    remove_btn = pn.widgets.Button(name="Remove", button_type="danger", width=70)

    # container for this scenario
    box = pn.Column(
        pn.Row(x_input, copy_btn, remove_btn),
        sizing_mode="fixed",
        styles={"border": "2px solid #888", "padding": "10px", "margin": "10px"},
    )

    # actions
    def do_copy(event):
        max_idx = max(scenarios.keys()) if scenarios else 0
        add_scenario(max_idx + 1, x_input.value)

    def do_remove(event):
        scenarios.pop(idx)
        refresh_scenarios()

    copy_btn.on_click(do_copy)
    remove_btn.on_click(do_remove)

    return box

# --- Scenario registry and container ---
scenarios = {}
scenarios_container = pn.Row(styles={"overflow-x": "auto", "flex-wrap": "nowrap"})

def refresh_scenarios():
    """Rebuild the container from current scenario dict."""
    scenarios_container.objects = list(scenarios.values())


def add_scenario(idx, value=1.0):
    scenarios[idx] = create_scenario(idx, value)
    refresh_scenarios()

# --- "Add Scenario" button ---
add_btn = pn.widgets.Button(name="Add Scenario", button_type="success")

def do_add(event):
    next_idx = max(scenarios.keys()) + 1 if scenarios else 1
    add_scenario(next_idx, 1.0)

add_btn.on_click(do_add)

# --- App Layout ---
app = pn.Column(
    "# MVP: Dynamic Scenarios with x²",
    add_btn,
    scenarios_container,
)

# Launch
if __name__ == "__main__":
    pn.serve(app, show=True)