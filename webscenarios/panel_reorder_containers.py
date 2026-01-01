import panel as pn


CARD_MARGIN = (10, 10, 10, 10)

# Global registry mapping container names to Panel container objects
container_registry = {
    "Form": None  # Will be set when cards_col is created
}

# Global list to track all cards and their metadata
all_cards = []  # List of tuples: (card, is_container, container_obj)

def update_all_dropdowns():
    """Update all parent_container_dropdown widgets with current container options"""
    container_names = list(container_registry.keys())
    for card, _, _ in all_cards:
        if hasattr(card, '_parent_container_dropdown'):
            card._parent_container_dropdown.options = container_names

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

def make_reorderable_card(title: str, body, parent_container, is_container: bool = False, container_name: str = None):
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

c1 = make_reorderable_card("Card A", body=[pn.pane.Markdown("Content A")], parent_container=cards_col)
c2 = make_reorderable_card("Card B", body=[pn.pane.Markdown("Content B")], parent_container=cards_col)
c3 = make_reorderable_card("Card C", body=[pn.pane.Markdown("Content C")], parent_container=cards_col)
cards_col.objects = [c1, c2, c3]


# New Widget Block

def generate_default_widget_name():
    """Generate a default unique card title"""
    existing_titles = [card.title for card in cards_col.objects if hasattr(card, 'title')]
    card_num = len(existing_titles) + 1
    if card_num <= 26:
        title = f"Card {chr(64 + card_num)}"  # A, B, C, D, etc.
    else:
        title = f"Card {card_num}"  # Use numbers after Z
    
    # Find next available title if current one exists
    counter = 1
    while title in existing_titles:
        if card_num + counter <= 26:
            title = f"Card {chr(64 + card_num + counter)}"
        else:
            title = f"Card {card_num + counter}"
        counter += 1
    
    return title

card_name_input = pn.widgets.TextInput(
    name="Widget Name",
    value=generate_default_widget_name(),
    width=200
)

def create_new_widget_card(_):
    # Use the value from the text input, or generate default if empty
    title = card_name_input.value.strip() if card_name_input.value.strip() else generate_default_widget_name()
    
    # Default to Form container
    parent_container = container_registry.get("Form", cards_col)
    
    new_card = make_reorderable_card(title, pn.pane.Markdown(f"Content {title.split()[-1]}"), parent_container=parent_container)
    parent_objs = list(parent_container.objects)
    parent_objs.append(new_card)
    parent_container.objects = parent_objs
    
    # Update the text input to the next default value
    card_name_input.value = generate_default_widget_name()

add_card_button = pn.widgets.Button(name="➕ Add New Widget", button_type="primary", width=150)
add_card_button.on_click(create_new_widget_card)

new_widget_block = pn.Column(
            pn.pane.Markdown("## New Widget"),
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


# Main entrypoint

pn.template.FastListTemplate(
    title="Reorderable Cards MVP",
    main=[
        new_widget_block,
        new_container_block,
        cards_col
    ],
).servable()