"""Round-trip tests for demo 08 (`08_panel_datamodel_formbuilder.py`): build a layout through
the designer callbacks, serialize it to a JSON-ready dict, regenerate the designer from that
dict, and check that nothing is lost.

Demo 08 is a script that keeps all of its state in module globals, so every test loads a fresh
copy of the module. Run: `poetry run pytest tests/`.
(Added for energyoptimizer T051; the multitenant app ports this serialize/regenerate pattern.)
"""
import importlib.util
import itertools
import json
from pathlib import Path

import panel as pn
import pytest

DEMO = Path(__file__).resolve().parents[1] / "webscenarios" / "08_panel_datamodel_formbuilder.py"
_n = itertools.count()


@pytest.fixture
def fb(capsys):
    spec = importlib.util.spec_from_file_location(f"formbuilder08_{next(_n)}", DEMO)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def add_widget(fb, variable, name="", parent="Form"):
    fb.card_variable_input.value = variable
    fb.card_name_input.value = name
    fb.master_parent_container_dropdown.value = parent
    fb.create_new_widget_card(None)


def add_container(fb, kind, name):
    fb.container_type_dropdown.value = kind
    fb.container_name_input.value = name
    fb.create_new_container(None)


def card_for(fb, variable):
    return next(c for c, _, _ in fb.all_cards if not c._is_container and c._variable_name == variable)


def build_sample(fb):
    """Top-level widget, a Row with two widgets, a collapsible container with an Enum Select."""
    add_widget(fb, "x", "X value")
    add_container(fb, "Row", "R1")
    add_widget(fb, "y", parent="R1")
    add_widget(fb, "n_years", "Years", parent="R1")
    add_container(fb, "Collapsible Container", "Advanced")
    add_widget(fb, "method", "Method", parent="Advanced")
    add_widget(fb, "validate")
    card_for(fb, "x")._widget_config_fields["value"].value = 5.5
    card_for(fb, "n_years")._widget_config_fields["value"].value = 7
    return fb.serialize_layout()


def widgets_in(layout):
    out = []
    for child in layout.get("children", []):
        out.extend(widgets_in(child) if child["type"] == "container" else [child])
    return out


def test_designer_builds_expected_structure(fb):
    layout = build_sample(fb)
    assert layout["type"] == "container" and layout["container_type"] == "Form"
    kinds = [(c["type"], c.get("container_type"), c.get("input_field")) for c in layout["children"]]
    assert kinds == [("widget", None, "x"), ("container", "Row", None),
                     ("container", "Collapsible Container", None), ("widget", None, "validate")]
    assert [w["input_field"] for w in layout["children"][1]["children"]] == ["y", "n_years"]
    assert [w["input_field"] for w in layout["children"][2]["children"]] == ["method"]
    x = layout["children"][0]
    assert (x["widget"], x["name"], x["value"]) == ("FloatInput", "X value", 5.5)
    assert set(fb.available_input_fields).isdisjoint({"x", "y", "n_years", "method", "validate"})


def test_layout_is_json_ready(fb):
    layout = build_sample(fb)
    assert json.loads(json.dumps(layout)) == layout


def test_serialize_regenerate_serialize_is_stable(fb):
    layout = build_sample(fb)
    fb.deserialize_layout(json.loads(json.dumps(layout)))
    assert fb.serialize_layout() == layout
    # and once more from the regenerated designer
    fb.deserialize_layout(fb.serialize_layout())
    assert fb.serialize_layout() == layout


def test_regenerate_in_fresh_session(fb):
    """Upload path: a layout saved in one session regenerates in another."""
    layout = json.loads(json.dumps(build_sample(fb)))
    spec = importlib.util.spec_from_file_location(f"formbuilder08_{next(_n)}", DEMO)
    other = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(other)
    other.deserialize_layout(layout)
    assert other.serialize_layout() == layout
    used = {w["input_field"] for w in widgets_in(layout)}
    assert set(other.available_input_fields) == set(other.input_fields) - used
    assert set(other.card_variable_input.options) == set(other.available_input_fields)


@pytest.mark.xfail(strict=True, reason=(
    "Spike bug (harness NEEDS_USER N14): deserialize_card strips only 'Row: '/'Column: ' title prefixes, "
    "so a regenerated collapsible container is registered as 'Collapsible Container: Advanced' "
    "instead of 'Advanced'"))
def test_regenerated_containers_accept_new_widgets(fb):
    layout = build_sample(fb)
    fb.deserialize_layout(layout)
    assert {"R1", "Advanced"} <= set(fb.container_registry)
    add_widget(fb, "z", parent="R1")
    row = fb.serialize_layout()["children"][1]
    assert [w["input_field"] for w in row["children"]] == ["y", "n_years", "z"]


@pytest.mark.xfail(strict=True, raises=TypeError, reason=(
    "Spike bug (harness NEEDS_USER N14): a bool field's 'value' config is a Select, so serialize_card adds "
    "'options' and build_widget_from_dict calls pn.widgets.Checkbox(options=...) -> TypeError; any "
    "layout containing a bool widget renders as an error card"))
def test_rendered_form_matches_layout(fb):
    layout = build_sample(fb)
    form = fb.build_form_from_layout(layout)
    assert isinstance(form, pn.Column)
    x, row, card, validate = form.objects
    assert isinstance(x, pn.widgets.FloatInput) and x.value == 5.5 and x.name == "X value"
    assert isinstance(row, pn.Row) and [type(w) for w in row.objects] == [pn.widgets.FloatInput, pn.widgets.IntInput]
    assert row.objects[1].value == 7
    assert isinstance(card, pn.Card) and isinstance(card.objects[0], pn.widgets.Select)
    assert isinstance(validate, pn.widgets.Checkbox)


def test_rendered_form_without_bool_widgets(fb):
    layout = build_sample(fb)
    layout["children"] = [c for c in layout["children"] if c.get("input_field") != "validate"]
    x, row, card = fb.build_form_from_layout(layout).objects
    assert isinstance(x, pn.widgets.FloatInput) and x.value == 5.5 and x.name == "X value"
    assert isinstance(row, pn.Row) and [type(w) for w in row.objects] == [pn.widgets.FloatInput, pn.widgets.IntInput]
    assert row.objects[1].value == 7
    assert isinstance(card, pn.Card) and isinstance(card.objects[0], pn.widgets.Select)


def test_unknown_widget_and_field_are_rejected(fb):
    with pytest.raises(ValueError, match="Unknown widget type"):
        fb.build_widget_from_dict({"type": "widget", "widget": "os.system", "name": "x"})
    with pytest.raises(ValueError, match="Unknown input field"):
        fb.deserialize_card({"type": "widget", "input_field": "__class__", "name": "x"}, fb.cards_col)
