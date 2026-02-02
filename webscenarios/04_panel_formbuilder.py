import json
import datetime as dt
import attrs
from copy import deepcopy
from panel.widgets.base import Widget

import panel as pn
import param

pn.extension()

@attrs.define
class DataModel:
    x: float = 1.0
    y: float = 2.0
    z: float = 3.0
    name: str = "Default"
    method: str = "mul"
    validate: bool = True

    def __attrs_post_init__(self):
        valid_methods = {"mul", "add", "sub"}
        if self.method not in valid_methods:
            raise ValueError(f"Invalid method '{self.method}'. Choose from {valid_methods}.")

    def compute(self) -> float:
        print(f"Computing with x={self.x}, y={self.y}, z={self.z}, method='{self.method}'")
        if self.validate:
            print("Validation is enabled.")
        if self.method == "mul":
            return self.x * self.y * self.z
        elif self.method == "add":
            return self.x + self.y + self.z
        elif self.method == "sub":
            return self.x - self.y - self.z
        else:
            raise ValueError(f"Unsupported method '{self.method}'.")

PANEL_CLASS_MAP = {
    "TextInput": pn.widgets.TextInput,
    "IntInput": pn.widgets.IntInput,
    "Checkbox": pn.widgets.Checkbox,
    "FloatInput": pn.widgets.FloatInput,
    "Select": pn.widgets.Select,
}

def build_widget_from_dict(input_dict: dict) -> pn.widgets.base.Widget:
    RESERVED_KEYS = {"input_field", "widget"}
    clean_params = {k: v for k, v in input_dict.items() if k not in RESERVED_KEYS}
    widget_type = input_dict.get("widget", None)
    if not widget_type:
        raise ValueError(f"Widget type must be specified in the input dictionary: input_dict={input_dict}")
    widget_class = PANEL_CLASS_MAP.get(widget_type)
    print(f"Building widget of type '{widget_type}' with params: {clean_params}")
    return widget_class(**clean_params)

name_input = pn.widgets.TextInput(name="Name", value="Alice")
x_input = pn.widgets.IntInput(name="X value", value=2, start=1, end=20)
y_input = pn.widgets.FloatInput(name="Y value", value=2, start=0, end=10, step=0.5)
validate_input = pn.widgets.Checkbox(name="Validate inputs?", value=True)
method_input = pn.widgets.Select(name="Computation Method", options=["mul", "add", "sub"], value="mul")

widgets = [
    dict(input_field="name", widget="TextInput", name="Name", value="Alice"),
    dict(input_field="x", widget="IntInput", name="X value", value=2, start=1, end=20),
    dict(input_field="y", widget="FloatInput", name="Y value", value=2, start=0, end=10, step=0.5),
    dict(input_field="z", widget="FloatInput", name="Z value", value=2, start=0, end=10, step=0.5),
    dict(input_field="validate", widget="Checkbox", name="Validate inputs?", value=True),
    dict(input_field="method", widget="Select", name="Computation Method", options=["mul", "add", "sub"], value="mul"),
]

widget_dict = {w["input_field"]: build_widget_from_dict(w) for w in widgets}
print("Constructed widget_dict:", widget_dict)

compute_btn = pn.widgets.Button(name="Compute", button_type="primary")
output_text = pn.widgets.StaticText(name="Output", value="")

def do_compute(event):
    print("Compute button clicked.")
    defaults = {"x": 1.0, "y": 2.0, "z": 3.0, "name": "Default", "method": "mul", "validate": True}
    input_values = deepcopy(defaults)
    print(widget_dict)
    for input_field, widget in widget_dict.items():
        input_values[input_field] = widget.value

    print(f"Building DataModel with inputs: {input_values}")
    model_instance = DataModel(**input_values)
    result = model_instance.compute()
    output_text.value = f"### Computation Result\nThe result of the computation is: **{result}**"
    return

compute_btn.on_click(do_compute)

pn.Column(
    *widget_dict.values(),
    compute_btn,
    output_text,
).servable()
