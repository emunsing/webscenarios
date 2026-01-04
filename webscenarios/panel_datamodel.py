from operator import mul
import panel as pn
import attrs
from enum import Enum
import pandas as pd
import numpy as np
import operator
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



## PANEL TOOLING

CARD_MARGIN = (10, 10, 10, 10)

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
    width=200
)

card_variable_input = pn.widgets.Select(
    name="Variable",
    options=available_input_fields if available_input_fields else [],
    value=available_input_fields[0] if available_input_fields else None,
    width=200
)

def update_all_dropdowns():
    """Update all parent_container_dropdown widgets with current container options"""
    container_names = list(container_registry.keys())
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
    
    # For widget cards (not containers), add an editable name field
    name_edit_widget = None
    if not is_container and variable_name is not None:
        # Create text input for custom name editing
        current_custom_name = custom_name if custom_name else ""
        name_edit_widget = pn.widgets.TextInput(
            name="Display Name",
            value=current_custom_name,
            width=250,
            margin=(5, 0, 5, 0)
        )
        
        def on_name_change(event):
            """Handle custom name change"""
            new_custom_name = event.new
            card._custom_name = new_custom_name
            update_card_title(card, new_custom_name, variable_name)
        
        name_edit_widget.param.watch(on_name_change, 'value')
        body = [name_edit_widget] + body

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
    
    def on_down(_):
        current_parent = card._current_parent
        if card in current_parent.objects:
            idx = current_parent.objects.index(card)
            move(current_parent, idx, +1)
    
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
    
    # Default to Form container
    parent_container = container_registry.get("Form", cards_col)
    
    # Get field info for the variable
    field_info = input_fields.get(variable_name)
    if field_info is None:
        return
    
    # Create appropriate widget based on field type
    # For now, just use a markdown placeholder - this will be expanded later
    widget_body = pn.pane.Markdown(f"Widget for {variable_name} ({field_info.dtype.__name__})")
    
    new_card = make_reorderable_card(
        title, 
        widget_body, 
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

add_card_button.on_click(create_new_widget_card)

new_widget_block = pn.Column(
            pn.pane.Markdown("## New Widget"),
            card_variable_input,
            card_name_input,
            add_card_button,
        )

# New Container block: choose either a Row or a Column from the dropdown, add a name

def create_new_container(_):
    container_type = container_type_dropdown.value
    container_name = container_name_input.value.strip()
    
    if not container_name:
        container_name = f"{container_type} {len(container_registry)}"
    
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
    
    # Reset input
    container_name_input.value = ""

container_type_dropdown = pn.widgets.Select(name="Container Type", options=["Row", "Column"], value="Row")
container_name_input = pn.widgets.TextInput(name="Container Name", value="Default")
add_container_button = pn.widgets.Button(name="➕ Add New Container", button_type="primary", width=150)
add_container_button.on_click(create_new_container)

new_container_block = pn.Column(
            pn.pane.Markdown("## New Container"),
            container_type_dropdown,
            container_name_input,
            add_container_button,
        )
update_available_input_fields_dropdown()  # This call is needed to make sure that we don't have the dropdown state tied to a stale or mutated list, which would prevent redrawing

# Main entrypoint

pn.template.FastListTemplate(
    title="Reorderable Cards MVP",
    main=[
        new_widget_block,
        new_container_block,
        cards_col
    ],
).servable()