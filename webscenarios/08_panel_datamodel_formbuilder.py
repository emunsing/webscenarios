from operator import mul
import panel as pn
import attrs
from enum import Enum
import pandas as pd
import numpy as np
import operator
import json
from pandas.core.generic import NDFrame


class Method(Enum):
    ADD = "add"
    MUL = "mul"
    SUB = "sub"

@attrs.define
class ModelOutputs:
    base_cost: float = 0.0
    total_cost: float = 0.0
    annual_totals: pd.Series | None = None
    product_annual_totals: pd.DataFrame | None = None
    raw_product_series: pd.Series | None = None

@attrs.define
class ModelInputs:
    x: float = 1.0
    y: float = 2.0
    z: int = 3
    annual_inflation: float = 0.02
    n_years: int = 10
    name: str = "Alice"
    product_types: list[str] = ["A", "B", "C"]
    method: Method = Method.MUL
    validate: bool = True

def run_model(inputs: ModelInputs) -> ModelOutputs:
    math_operation = getattr(operator, inputs.method.value)
    base_cost = math_operation(inputs.x, inputs.y) ** inputs.z
    year_1_costs = [(base_cost + i) / 12 for i in range(len(inputs.product_types))]
    monthly_interest_rate = (1 + inputs.annual_inflation) ** (1/12)
    monthly_adders = [monthly_interest_rate ** i for i in range(inputs.n_years * 12)]

    raw_product_df = pd.DataFrame(np.outer(monthly_adders, year_1_costs),
                                    index=pd.date_range(start='2020-01-01', 
                                                        freq='1MS',
                                                        periods=inputs.n_years * 12),
                                columns=inputs.product_types)
    product_annual_totals = raw_product_df.groupby(raw_product_df.index.year).sum()
    return ModelOutputs(base_cost=base_cost,
                        total_cost=raw_product_df.sum().sum(),
                        annual_totals=product_annual_totals.sum(axis=1),
                        product_annual_totals=product_annual_totals,
                        raw_product_series=raw_product_df)


## CLASS TEMPLATING

# USER DEFINED
default_input_instance = ModelInputs()
data_result = run_model(default_input_instance)  # This may need to handle class/instance methods

# AUTO-GENERATED
output_data_class = type(data_result)
output_data_attributes = attrs.fields(output_data_class)

@attrs.define
class InputFieldInfo:
    name: str
    dtype: type
    default_value: any

@attrs.define
class OutputFieldInfo:
    name: str
    dtype: type
    datetime_index: bool = False
    index_names: list[str] = []
    datetime_columns: bool = False
    column_names: list[str] = []

# Build a collection of *input* fields from the data input
input_fields = {}
input_data_attributes = attrs.fields(type(default_input_instance))
for attribute in input_data_attributes:
    field_info = InputFieldInfo(
        name=attribute.name,
        dtype=attribute.type,
        default_value=attribute.default
    )
    input_fields[attribute.name] = field_info

available_input_fields = list(input_fields.keys())

# Build a collection of *output* fields from the data output
displayable_output_fields = {}

for attribute in output_data_attributes:
    field_value = data_result.__getattribute__(attribute.name)
    if not isinstance(field_value, NDFrame):
        continue
    field_info = OutputFieldInfo(
        name=attribute.name,
        dtype=type(field_value),
        datetime_index=isinstance(field_value.index, pd.DatetimeIndex),
        index_names=list(field_value.index.names),
        datetime_columns=False if isinstance(field_value, pd.Series) else isinstance(field_value.columns, pd.DatetimeIndex),
        column_names=[None] if isinstance(field_value, pd.Series) else list(field_value.columns.names)    
    )
    displayable_output_fields[attribute.name] = field_info

# 
PANEL_CLASS_MAP = {
    "TextInput": pn.widgets.TextInput,  # Apply this to all `str` inputs. Expose: `value` (string TextInput), `description` (string TextInput)
    "IntInput": pn.widgets.IntInput,  # Apply this to all `int` inputs. Expose: `value` (int IntInput), `start` (int IntInput), `end` (int IntInput), , `description` (string TextInput)
    "Checkbox": pn.widgets.Checkbox,  # Apply this to all `bool` inputs. Expose: `value` (true/false Select), `description` (string TextInput)
    "FloatInput": pn.widgets.FloatInput,  # Apply this to all `float` inputs. Expose: `value` (float FloatInput), `start` (float FloatInput), `end` (float FloatInput), `step` (float FloatInput) , `description` (string TextInput)
    "Select": pn.widgets.Select,  # Apply this to all `Enum` subclass inputs. Expose: `value` (Select of all Enum values), `description` (string TextInput)
}

## PANEL TOOLING

CARD_MARGIN = (7, 7, 7, 7)  # top, right, bottom, left
WIDGET_MARGIN = (5, 5, 5, 5)  # top, right, bottom, left

def get_panel_widget_type(field_type: type) -> str:
    """Determine which Panel widget type to use based on Python type"""
    if field_type == str:
        return "TextInput"
    elif field_type == int:
        return "IntInput"
    elif field_type == bool:
        return "Checkbox"
    elif field_type == float:
        return "FloatInput"
    elif isinstance(field_type, type) and issubclass(field_type, Enum):
        return "Select"
    else:
        # Default to TextInput for unknown types
        return "TextInput"

def create_widget_config_fields(field_info: InputFieldInfo, widget_type: str) -> dict:
    """
    Create configuration input fields for a widget based on its type.
    Returns a dictionary mapping field names to Panel widget objects.
    """
    config_fields = {}
    default_value = field_info.default_value
    
    if widget_type == "TextInput":
        config_fields["value"] = pn.widgets.TextInput(
            name="Default Value",
            value=str(default_value) if default_value is not None else "",
            width=300,
            margin=WIDGET_MARGIN
        )
        config_fields["description"] = pn.widgets.TextInput(
            name="Additional Description",
            value="",
            width=300,
            margin=WIDGET_MARGIN
        )
    
    elif widget_type == "IntInput":
        config_fields["value"] = pn.widgets.IntInput(
            name="Default Value",
            value=int(default_value) if default_value is not None else 0,
            width=300,
            margin=WIDGET_MARGIN
        )
        config_fields["description"] = pn.widgets.TextInput(
            name="Additional Description",
            value="",
            width=300,
            margin=WIDGET_MARGIN
        )
        config_fields["start"] = pn.widgets.IntInput(
            name="Start",
            value=None,
            width=300,
            margin=WIDGET_MARGIN
        )
        config_fields["end"] = pn.widgets.IntInput(
            name="End",
            value=None,
            width=300,
            margin=(5, 0, 5, 0)
        )

    
    elif widget_type == "Checkbox":
        config_fields["value"] = pn.widgets.Select(
            name="Default Value",
            options=[True, False],
            value=bool(default_value) if default_value is not None else False,
            width=300,
            margin=WIDGET_MARGIN
        )
        config_fields["description"] = pn.widgets.TextInput(
            name="Additional Description",
            value="",
            width=300,
            margin=WIDGET_MARGIN
        )
    
    elif widget_type == "FloatInput":
        config_fields["value"] = pn.widgets.FloatInput(
            name="Default Value",
            value=float(default_value) if default_value is not None else 0.0,
            width=300,
            margin=WIDGET_MARGIN
        )
        config_fields["description"] = pn.widgets.TextInput(
            name="Additional Description",
            value="",
            width=300,
            margin=WIDGET_MARGIN
        )
        config_fields["start"] = pn.widgets.FloatInput(
            name="Start",
            value=None,
            width=300,
            margin=WIDGET_MARGIN
        )
        config_fields["end"] = pn.widgets.FloatInput(
            name="End",
            value=None,
            width=300,
            margin=WIDGET_MARGIN
        )
        config_fields["step"] = pn.widgets.FloatInput(
            name="Step",
            value=None,
            width=300,
            margin=WIDGET_MARGIN
        )
    
    elif widget_type == "Select":
        # Get Enum values from the field type
        enum_values = [e.value for e in field_info.dtype]
        config_fields["value"] = pn.widgets.Select(
            name="Default Value",
            options=enum_values,
            value=default_value.value if isinstance(default_value, Enum) else enum_values[0] if enum_values else None,
            width=300,
            margin=WIDGET_MARGIN
        )
        config_fields["description"] = pn.widgets.TextInput(
            name="Additional Description",
            value="",
            width=300,
            margin=WIDGET_MARGIN
        )
    
    return config_fields

# Global registry mapping container names to Panel container objects
container_registry = {
    "Form": None  # Will be set when cards_col is created
}

# Global list to track all cards and their metadata
all_cards = []  # List of tuples: (card, is_container, container_obj)

# New widget block
add_card_button = pn.widgets.Button(
    name="➕ Add New Widget", 
    button_type="primary", 
    width=150,
    disabled=len(available_input_fields) == 0
)

card_name_input = pn.widgets.TextInput(
    name="Display Name",
    value="",
    width=200,
    margin=WIDGET_MARGIN
)

card_variable_input = pn.widgets.Select(
    name="Variable",
    options=available_input_fields if available_input_fields else [],
    value=available_input_fields[0] if available_input_fields else None,
    width=200,
    margin=WIDGET_MARGIN
)

master_parent_container_dropdown = pn.widgets.Select(
    name="Initial Parent",
    options=list(container_registry.keys()),
    value="Form",
    width=200,
    margin=WIDGET_MARGIN
)

def update_all_dropdowns():
    """Update all parent_container_dropdown widgets with current container options"""
    container_names = list(container_registry.keys())
    # Update master dropdown
    if 'master_parent_container_dropdown' in globals():
        master_parent_container_dropdown.options = container_names
        # Ensure current value is still valid
        if master_parent_container_dropdown.value not in container_names:
            master_parent_container_dropdown.value = "Form"
    # Update all card dropdowns
    for card, _, _ in all_cards:
        if hasattr(card, '_parent_container_dropdown'):
            card._parent_container_dropdown.options = container_names

def update_available_input_fields_dropdown():
    """Update the available input fields dropdown and button state"""

    print(f"Updating available input fields dropdown with: {available_input_fields}")
    card_variable_input.options = available_input_fields.copy() if available_input_fields else [""]
    card_variable_input.value = available_input_fields[0] if available_input_fields else ""
    add_card_button.disabled = len(available_input_fields) == 0

def update_card_title(card, custom_name: str, variable_name: str):
    """Update card title and header markdown based on custom name and variable name"""
    title = f"{custom_name.strip() if custom_name.strip() else variable_name} [{variable_name}]"
    card.title = title
    # Update the header markdown
    for obj in card.header.objects:
        if isinstance(obj, pn.pane.Markdown):
            obj.object = f"**{title}**"
            break

def move(container, idx: int, delta: int):
    objs = list(container.objects)
    j = idx + delta
    if j < 0 or j >= len(objs):
        return
    objs[idx], objs[j] = objs[j], objs[idx]
    container.objects = objs  # triggers re-render

def update_delete_button_state_for_card_helper(card_to_update, container_obj):
    """Helper to update delete button state for a specific card"""
    if container_obj is None:
        return
    has_children = len(container_obj.objects) > 0
    if hasattr(card_to_update, 'header') and hasattr(card_to_update.header, 'objects'):
        for obj in card_to_update.header.objects:
            if isinstance(obj, pn.widgets.Button) and obj.name == "🗑️":
                obj.disabled = has_children

def make_reorderable_card(title: str, body, parent_container, is_container: bool = False, container_name: str = None, variable_name: str = None, custom_name: str = None):
    """Create a reorderable card. For widget cards, variable_name and custom_name are used to generate the title."""
    up = pn.widgets.Button(name="▲", width=32, button_type="light")
    down = pn.widgets.Button(name="▼", width=32, button_type="light")
    
    delete = pn.widgets.Button(name="🗑️", width=32, button_type="light")
    
    # Find the current parent container name
    current_parent_name = None
    for name, container_obj in container_registry.items():
        if container_obj is parent_container:
            current_parent_name = name
            break
    
    if current_parent_name is None:
        current_parent_name = "Form"
    
    parent_container_dropdown = pn.widgets.Select(
        name="Parent", 
        options=list(container_registry.keys()), 
        value=current_parent_name
    )

    if not isinstance(body, list):
        body = [body]
    
    # For widget cards (not containers), add configuration fields
    name_edit_widget = None
    widget_config_fields = {}
    if not is_container and variable_name is not None:
        # Get field info to determine widget type and create config fields
        field_info = input_fields.get(variable_name)
        if field_info:
            widget_type = get_panel_widget_type(field_info.dtype)
            widget_config_fields = create_widget_config_fields(field_info, widget_type)
            
            # Create text input for custom name editing
            current_custom_name = custom_name if custom_name else ""
            name_edit_widget = pn.widgets.TextInput(
                name="Display Name",
                value=current_custom_name,
                width=300,
                margin=WIDGET_MARGIN
            )
            
            def on_name_change(event):
                """Handle custom name change"""
                new_custom_name = event.new
                card._custom_name = new_custom_name
                update_card_title(card, new_custom_name, variable_name)
                # Update rendered form
                update_rendered_form()
            
            name_edit_widget.param.watch(on_name_change, 'value')
            
            # Build body with: name field, then all config fields, then original body
            config_field_list = [name_edit_widget] + list(widget_config_fields.values())
            body = config_field_list + body

    header = pn.Row(
        pn.pane.Markdown(f"**{title}**", margin=(6, 8, 0, 8)),
        pn.Spacer(),
        parent_container_dropdown,
        pn.Spacer(),
        up,
        down,
        delete,
        sizing_mode="stretch_width",
        margin=(0, 0, 0, 0),
    )

    # Create the container object if this is a container
    container_obj = None
    if is_container:
        if container_name:
            # Create Row or Column based on container_name
            if container_name.startswith("Row:"):
                container_obj = pn.Row(sizing_mode="stretch_width")
            else:  # Column
                container_obj = pn.Column(sizing_mode="stretch_width")
        else:
            container_obj = pn.Column(sizing_mode="stretch_width")
        # Add the container_obj to the body so children are visible when expanded
        body = body + [container_obj]
    
    card = pn.Card(
        *body,
        header=header,
        title=title,
        collapsible=True,
        sizing_mode="stretch_width",
        margin=CARD_MARGIN,
    )
    
    # Store references for later access
    card._parent_container_dropdown = parent_container_dropdown
    card._is_container = is_container
    card._container_obj = container_obj
    card._current_parent = parent_container
    if not is_container and variable_name is not None:
        card._variable_name = variable_name
        card._custom_name = custom_name if custom_name else ""
        card._name_edit_widget = name_edit_widget
        card._widget_config_fields = widget_config_fields
        # Store field info and widget type for later use
        field_info = input_fields.get(variable_name)
        if field_info:
            card._widget_type = get_panel_widget_type(field_info.dtype)
            card._field_info = field_info
    
    def update_delete_button_state():
        """Update delete button state based on whether container has children"""
        if is_container and container_obj is not None:
            has_children = len(container_obj.objects) > 0
            delete.disabled = has_children
        else:
            delete.disabled = False
    
    def on_up(_):
        current_parent = card._current_parent
        if card in current_parent.objects:
            idx = current_parent.objects.index(card)
            move(current_parent, idx, -1)
            # Update rendered form
            update_rendered_form()
    
    def on_down(_):
        current_parent = card._current_parent
        if card in current_parent.objects:
            idx = current_parent.objects.index(card)
            move(current_parent, idx, +1)
            # Update rendered form
            update_rendered_form()
    
    def on_delete(_):
        current_parent = card._current_parent
        objs = list(current_parent.objects)
        if card in objs:
            objs.remove(card)
            current_parent.objects = objs
            
            # Re-add variable to available_input_fields if this is a widget card
            if not is_container and hasattr(card, '_variable_name') and card._variable_name:
                if card._variable_name not in available_input_fields:
                    available_input_fields.append(card._variable_name)
                    update_available_input_fields_dropdown()
            
            # Remove from registry if it's a container
            if is_container and container_obj is not None:
                container_name_to_remove = None
                for name, obj in container_registry.items():
                    if obj is container_obj:
                        container_name_to_remove = name
                        break
                if container_name_to_remove and container_name_to_remove != "Form":
                    del container_registry[container_name_to_remove]
                    update_all_dropdowns()
            
            # Remove from all_cards tracking
            all_cards[:] = [(c, ic, co) for c, ic, co in all_cards if c is not card]
            
            # Update all delete buttons since parent relationships may have changed
            for other_card, other_is_container, other_container_obj in all_cards:
                if other_is_container and other_container_obj is not None:
                    update_delete_button_state_for_card_helper(other_card, other_container_obj)
            
            # Update rendered form
            update_rendered_form()
    
    def on_parent_change(event):
        """Handle parent container dropdown change"""
        new_parent_name = event.new
        old_parent = card._current_parent
        
        # Get the new parent container object
        new_parent = container_registry.get(new_parent_name)
        if new_parent is None:
            return
        
        # Don't move if already in the correct parent
        if new_parent is old_parent:
            return
        
        # Remove from old parent (the visual parent container)
        old_objs = list(old_parent.objects)
        if card in old_objs:
            old_objs.remove(card)
            old_parent.objects = old_objs
        
        # If old parent was a container's container_obj, update that container's delete button
        for other_card, other_is_container, other_container_obj in all_cards:
            if other_is_container and other_container_obj is old_parent:
                update_delete_button_state_for_card_helper(other_card, other_container_obj)
        
        # Add to new parent (the visual parent container)
        new_objs = list(new_parent.objects)
        new_objs.append(card)
        new_parent.objects = new_objs
        
        # Update current parent reference
        card._current_parent = new_parent
        
        # If new parent is a container's container_obj, update that container's delete button
        for other_card, other_is_container, other_container_obj in all_cards:
            if other_is_container and other_container_obj is new_parent:
                update_delete_button_state_for_card_helper(other_card, other_container_obj)
        
        # Update rendered form
        update_rendered_form()
    
    def on_config_change(_):
        """Handle changes to widget configuration fields"""
        # Update rendered form when any config field changes
        update_rendered_form()
    
    # Watch for changes in widget config fields
    if not is_container and variable_name is not None and widget_config_fields:
        for field_widget in widget_config_fields.values():
            field_widget.param.watch(on_config_change, 'value')
    
    up.on_click(on_up)
    down.on_click(on_down)
    delete.on_click(on_delete)
    parent_container_dropdown.param.watch(on_parent_change, 'value')
    
    # Set initial delete button state
    update_delete_button_state()
    
    # Add to tracking
    all_cards.append((card, is_container, container_obj))
    
    return card

cards_col = pn.Column(sizing_mode="stretch_width")
container_registry["Form"] = cards_col



def create_new_widget_card(_):
    # Get the selected variable
    variable_name = card_variable_input.value
    if not variable_name or variable_name not in available_input_fields:
        return
    
    # Get custom name from input
    custom_name = card_name_input.value.strip()
    
    # Generate title
    title = f"{custom_name if custom_name else variable_name} [{variable_name}]"
    
    # Get parent container from master dropdown
    parent_container_name = master_parent_container_dropdown.value
    parent_container = container_registry.get(parent_container_name, cards_col)
    
    # Get field info for the variable
    field_info = input_fields.get(variable_name)
    if field_info is None:
        return
    
    # Create the card - config fields will be added automatically in make_reorderable_card
    # Pass empty body since config fields are the main content
    new_card = make_reorderable_card(
        title, 
        [], 
        parent_container=parent_container,
        variable_name=variable_name,
        custom_name=custom_name
    )
    parent_objs = list(parent_container.objects)
    parent_objs.append(new_card)
    parent_container.objects = parent_objs
    
    # Remove variable from available_input_fields
    print(f"Available input fields: {available_input_fields}")
    if variable_name in available_input_fields:
        print("Removing variable from available_input_fields")
        available_input_fields.remove(variable_name)
        update_available_input_fields_dropdown()
        print(f"After removal, available input fields: {available_input_fields}")
    
    # Clear the input fields
    card_name_input.value = ""
    
    # Update rendered form
    update_rendered_form()

add_card_button.on_click(create_new_widget_card)

new_widget_block = pn.Column(
            pn.pane.Markdown("## New Widget"),
            card_variable_input,
            card_name_input,
            master_parent_container_dropdown,
            add_card_button,
        )

# New Container block: choose either a Row or a Column from the dropdown, add a name

def create_new_container(_):
    container_type = container_type_dropdown.value
    container_name = container_name_input.value.strip()
    
    # Require a name - button should be disabled if blank
    if not container_name:
        return
    
    # Generate unique name if needed
    base_name = container_name
    counter = 1
    while container_name in container_registry:
        container_name = f"{base_name} {counter}"
        counter += 1
    
    display_name = f"{container_type}: {container_name}"
    
    # Create the container card with is_container=True
    parent_container = container_registry.get("Form", cards_col)
    container_card = make_reorderable_card(
        display_name,
        body=[pn.pane.Markdown(f"Container: {container_name}")],
        parent_container=parent_container,
        is_container=True,
        container_name=display_name
    )
    
    # Add the container's internal container object to registry
    if container_card._container_obj is not None:
        container_registry[container_name] = container_card._container_obj
        update_all_dropdowns()
    
    # Add to parent
    parent_objs = list(parent_container.objects)
    parent_objs.append(container_card)
    parent_container.objects = parent_objs
    
    # Reset inputs
    container_name_input.value = ""
    # Button will be disabled automatically via the watch
    
    # Update rendered form
    update_rendered_form()

container_type_dropdown = pn.widgets.Select(name="Container Type", options=["Row", "Collapsible Container"], value="Row")
container_name_input = pn.widgets.TextInput(name="Container Name (required)", value="")
add_container_button = pn.widgets.Button(name="➕ Add New Container", button_type="primary", width=150, disabled=True)
add_container_button.on_click(create_new_container)

def update_container_button_state(_):
    """Update add_container_button state based on container_name_input"""
    add_container_button.disabled = not container_name_input.value.strip()

container_name_input.param.watch(update_container_button_state, 'value')

new_container_block = pn.Column(
            pn.pane.Markdown("## New Container"),
            container_type_dropdown,
            container_name_input,
            add_container_button,
        )
update_available_input_fields_dropdown()  # This call is needed to make sure that we don't have the dropdown state tied to a stale or mutated list, which would prevent redrawing

# Serialization and Rendering Functions

def serialize_card(card) -> dict:
    """Serialize a single card to a dictionary representation"""
    if card._is_container:
        # This is a container card
        container_type = "Row" if card.title.startswith("Row:") else "Collapsible Container"
        children = []
        
        # Get children from the container's container_obj
        if card._container_obj is not None:
            for child_card in card._container_obj.objects:
                children.append(serialize_card(child_card))
        
        return {
            "type": "container",
            "container_type": container_type,
            "title": card.title,
            "children": children
        }
    else:
        # This is a widget card
        widget_dict = {
            "type": "widget",
            "input_field": card._variable_name,
            "widget": card._widget_type,
            "name": card._custom_name if card._custom_name else card._variable_name,
        }
        
        # Add configuration values from widget_config_fields
        if hasattr(card, '_widget_config_fields') and card._widget_config_fields:
            for field_name, field_widget in card._widget_config_fields.items():
                value = field_widget.value
                # Only include non-None, non-empty values (except for description and value which should always be included)
                if field_name == "value" or field_name == "description" or (value is not None and value != ""):
                    # Convert Enum values to their string representation if needed
                    if isinstance(value, Enum):
                        value = value.value
                    widget_dict[field_name] = value
                
                # For Select widgets, also preserve the options
                if field_name == "value" and isinstance(field_widget, pn.widgets.Select):
                    widget_dict["options"] = field_widget.options
        
        return widget_dict

def serialize_layout() -> dict:
    """Serialize the entire layout starting from the Form container"""
    form_children = []
    for card in cards_col.objects:
        form_children.append(serialize_card(card))
    
    return {
        "type": "container",
        "container_type": "Form",
        "children": form_children
    }

def build_widget_from_dict(input_dict: dict) -> pn.widgets.base.Widget:
    """Build a Panel widget from a dictionary representation"""
    RESERVED_KEYS = {"input_field", "widget", "type", "container_type", "children", "title"}
    clean_params = {k: v for k, v in input_dict.items() if k not in RESERVED_KEYS}
    widget_type = input_dict.get("widget", None)
    if not widget_type:
        raise ValueError(f"Widget type must be specified in the input dictionary: input_dict={input_dict}")
    widget_class = PANEL_CLASS_MAP.get(widget_type)
    if widget_class is None:
        raise ValueError(f"Unknown widget type: {widget_type}")
    
    # Handle description separately - Panel widgets use 'description' parameter
    # Note: Some widgets might not support description, so we'll let it fail gracefully
    description = clean_params.pop("description", None)
    if description:
        clean_params["description"] = description
    
    # Filter out None values for optional parameters (except value which might be 0 or False)
    # Keep value, name, description, options always
    filtered_params = {}
    for key, val in clean_params.items():
        if key in ["value", "name", "description", "options"]:
            filtered_params[key] = val
        elif val is not None:
            filtered_params[key] = val
    
    return widget_class(**filtered_params)

def build_container_from_dict(container_dict: dict) -> pn.layout.base.Panel:
    """Build a Panel container (Row, Column, or Card) from a dictionary representation"""
    container_type = container_dict.get("container_type", "Column")
    children = container_dict.get("children", [])
    
    # Build child elements
    child_elements = []
    for child_dict in children:
        child_type = child_dict.get("type")
        if child_type == "container":
            child_elements.append(build_container_from_dict(child_dict))
        elif child_type == "widget":
            child_elements.append(build_widget_from_dict(child_dict))
        else:
            raise ValueError(f"Unknown child type: {child_type}")
    
    # Create the container
    if container_type == "Row":
        return pn.Row(*child_elements, sizing_mode="stretch_width")
    elif container_type == "Collapsible Container":
        title = container_dict.get("title", "Container")
        return pn.Card(*child_elements, title=title, collapsible=True, sizing_mode="stretch_width")
    elif container_type == "Form":
        # Form is just a Column
        return pn.Column(*child_elements, sizing_mode="stretch_width")
    else:
        # Default to Column
        return pn.Column(*child_elements, sizing_mode="stretch_width")

def build_form_from_layout(layout_dict: dict) -> pn.layout.base.Panel:
    """Build the complete form from a serialized layout dictionary"""
    if layout_dict.get("type") == "container":
        return build_container_from_dict(layout_dict)
    else:
        raise ValueError("Root layout must be a container")

def update_rendered_form():
    """Update the rendered form in render_col based on current layout"""
    try:
        layout_dict = serialize_layout()
        
        # Check if there are any widgets to render
        if not layout_dict.get("children"):
            render_col.objects = [pn.pane.Markdown("## Rendered Form\n\nNo widgets added yet.")]
            return
        
        rendered_form = build_form_from_layout(layout_dict)
        
        # Wrap in a Card with title
        form_card = pn.Card(
            rendered_form,
            title="Rendered Form",
            collapsible=False,
            sizing_mode="stretch_width"
        )
        
        # Clear and update render_col
        render_col.objects = [form_card]
    except Exception as e:
        error_msg = pn.pane.Markdown(f"## Error rendering form\n\n```\n{str(e)}\n```")
        render_col.objects = [pn.Card(error_msg, title="Rendered Form", collapsible=False)]
        print(f"Error updating rendered form: {e}")
        import traceback
        traceback.print_exc()

def deserialize_card(card_dict: dict, parent_container) -> tuple:
    """
    Deserialize a card dictionary and create the corresponding Panel card.
    Returns (card, used_variables) where used_variables is a set of variable names.
    """
    used_variables = set()
    
    if card_dict.get("type") == "container":
        # Create a container card
        container_type = card_dict.get("container_type", "Column")
        title = card_dict.get("title", "Container")
        
        # Determine container_name format
        if container_type == "Row":
            container_name = f"Row: {title.replace('Row: ', '')}"
        else:
            container_name = title
        
        # Create the container card
        container_card = make_reorderable_card(
            title,
            body=[pn.pane.Markdown(f"Container: {title}")],
            parent_container=parent_container,
            is_container=True,
            container_name=container_name
        )
        
        # Register the container if it's not "Form"
        if container_card._container_obj is not None:
            # Extract clean container name (remove "Row: " or "Collapsible Container: " prefix)
            container_name_clean = title
            if title.startswith("Row: "):
                container_name_clean = title[5:]  # Remove "Row: "
            elif title.startswith("Column: "):
                container_name_clean = title[8:]  # Remove "Column: "
            # Also handle if container_name was already set during creation
            
            if container_name_clean not in container_registry and container_name_clean != "Form":
                container_registry[container_name_clean] = container_card._container_obj
        
        # Process children
        children_dicts = card_dict.get("children", [])
        for child_dict in children_dicts:
            child_card, child_vars = deserialize_card(child_dict, container_card._container_obj)
            used_variables.update(child_vars)
            if container_card._container_obj is not None:
                container_card._container_obj.objects = list(container_card._container_obj.objects) + [child_card]
        
        return container_card, used_variables
    
    elif card_dict.get("type") == "widget":
        # Create a widget card
        variable_name = card_dict.get("input_field")
        
        if variable_name is None:
            raise ValueError("Widget card missing 'input_field'")
        
        used_variables.add(variable_name)
        
        # Extract custom name from the full name
        full_name = card_dict.get("name", variable_name)
        if f" [{variable_name}]" in full_name:
            custom_name = full_name.replace(f" [{variable_name}]", "")
        else:
            # If it doesn't have the pattern, check if it's just the variable name
            custom_name = "" if full_name == variable_name else full_name
        
        # Get field info
        field_info = input_fields.get(variable_name)
        if field_info is None:
            raise ValueError(f"Unknown input field: {variable_name}")
        
        # Generate title
        title = f"{custom_name if custom_name else variable_name} [{variable_name}]"
        
        # Create the card - config fields will be populated automatically
        widget_card = make_reorderable_card(
            title,
            [],
            parent_container=parent_container,
            variable_name=variable_name,
            custom_name=custom_name
        )
        
        # Restore widget configuration values
        if hasattr(widget_card, '_widget_config_fields') and widget_card._widget_config_fields:
            for field_name, field_widget in widget_card._widget_config_fields.items():
                if field_name in card_dict:
                    value = card_dict[field_name]
                    # Skip options - they're set from field_info
                    if field_name == "options":
                        continue
                    try:
                        field_widget.value = value
                    except Exception as e:
                        print(f"Warning: Could not set {field_name} to {value}: {e}")
        
        return widget_card, used_variables
    
    else:
        raise ValueError(f"Unknown card type: {card_dict.get('type')}")

def deserialize_layout(layout_dict: dict):
    """Deserialize a layout dictionary and rebuild the design view"""
    global available_input_fields
    
    # Clear current layout
    cards_col.objects = []
    all_cards.clear()
    
    # Clear container registry except Form
    keys_to_remove = [k for k in container_registry.keys() if k != "Form"]
    for key in keys_to_remove:
        del container_registry[key]
    
    # Process children of the root container
    if layout_dict.get("type") == "container":
        children_dicts = layout_dict.get("children", [])
        
        for child_dict in children_dicts:
            child_card, child_vars = deserialize_card(child_dict, cards_col)
            cards_col.objects = list(cards_col.objects) + [child_card]
    
    # Update available_input_fields
    all_used_vars = set()
    for card, _, _ in all_cards:
        if not card._is_container and hasattr(card, '_variable_name'):
            all_used_vars.add(card._variable_name)
    
    # Restore available_input_fields
    available_input_fields = [var for var in input_fields.keys() if var not in all_used_vars]
    
    # Update all dropdowns
    update_all_dropdowns()
    update_available_input_fields_dropdown()
    
    # Update rendered form
    update_rendered_form()

def download_layout_json():
    """Generate JSON string for download"""
    layout_dict = serialize_layout()
    json_str = json.dumps(layout_dict, indent=2)
    return json_str.encode('utf-8')

def handle_file_upload(event):
    """Handle file upload and deserialize the layout"""
    if event.new is None:
        return
    
    try:
        # Read the file content
        file_contents = event.new
        if isinstance(file_contents, bytes):
            file_contents = file_contents.decode('utf-8')
        
        # Parse JSON
        layout_dict = json.loads(file_contents)
        
        # Deserialize and rebuild
        deserialize_layout(layout_dict)
        
        # Clear the file input
        file_upload.value = None
        
    except json.JSONDecodeError as e:
        error_msg = pn.pane.Markdown(f"## Error loading file\n\nInvalid JSON: {str(e)}")
        render_col.objects = [pn.Card(error_msg, title="Error", collapsible=False)]
        print(f"Error parsing JSON: {e}")
    except Exception as e:
        error_msg = pn.pane.Markdown(f"## Error loading layout\n\n```\n{str(e)}\n```")
        render_col.objects = [pn.Card(error_msg, title="Error", collapsible=False)]
        print(f"Error loading layout: {e}")
        import traceback
        traceback.print_exc()

# Main entrypoint

# File download/upload widgets
def get_layout_json_bytes():
    """Get the current layout as JSON bytes for download"""
    import io
    layout_dict = serialize_layout()
    json_str = json.dumps(layout_dict, indent=2)
    return io.BytesIO(json_str.encode('utf-8'))

file_download = pn.widgets.FileDownload(
    callback=get_layout_json_bytes,
    filename="form_layout.json",
    button_type="primary",
    label="📥 Download Layout",
    auto=False
)

file_upload = pn.widgets.FileInput(
    accept=".json",
    multiple=False
)
file_upload.param.watch(handle_file_upload, 'value')

main_controls = pn.Column(
    pn.pane.Markdown("### Layout Controls"),
    pn.Row(file_download, file_upload, sizing_mode="stretch_width"),
    sizing_mode="stretch_width"
)

design_col = pn.Column(new_widget_block,
        new_container_block,
        cards_col)
render_col = pn.Column(sizing_mode="stretch_width")

# Initial render
update_rendered_form()


# TODO: Add rendered_col which shows the final form

pn.template.FastListTemplate(
    title="Reorderable Cards MVP",
    main=[
        main_controls,
        pn.Row(design_col, 
            render_col),
    ],
).servable()