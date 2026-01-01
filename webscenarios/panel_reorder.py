import panel as pn


def move(container: pn.Column, idx: int, delta: int):
    objs = list(container.objects)
    j = idx + delta
    if j < 0 or j >= len(objs):
        return
    objs[idx], objs[j] = objs[j], objs[idx]
    container.objects = objs  # triggers re-render

def make_reorderable_card(title: str, body, container: pn.Column):
    up = pn.widgets.Button(name="▲", width=32, button_type="light")
    down = pn.widgets.Button(name="▼", width=32, button_type="light")
    delete = pn.widgets.Button(name="🗑️", width=32, button_type="light")

    text_input = pn.widgets.TextInput(name="Text Input", value="Default")

    header = pn.Row(
        pn.pane.Markdown(f"**{title}**", margin=(6, 8, 0, 8)),
        pn.Spacer(),
        up,
        down,
        delete,
        sizing_mode="stretch_width",
        margin=(0, 0, 0, 0),
    )

    card = pn.Card(
        body,
        text_input,
        header=header,
        title=title,
        collapsible=True,
        sizing_mode="stretch_width",
        margin=(5, 0),
    )

    def on_up(_):
        idx = container.objects.index(card)
        move(container, idx, -1)

    def on_down(_):
        idx = container.objects.index(card)
        move(container, idx, +1)

    def on_delete(_):
        objs = list(container.objects)
        if card in objs:
            objs.remove(card)
            container.objects = objs

    up.on_click(on_up)
    down.on_click(on_down)
    delete.on_click(on_delete)

    return card

cards_col = pn.Column(sizing_mode="stretch_width")
c1 = make_reorderable_card("Card A", pn.pane.Markdown("Content A"), cards_col)
c2 = make_reorderable_card("Card B", pn.pane.Markdown("Content B"), cards_col)
c3 = make_reorderable_card("Card C", pn.pane.Markdown("Content C"), cards_col)
cards_col.objects = [c1, c2, c3]

def generate_default_card_name():
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
    name="Card Name",
    value=generate_default_card_name(),
    width=200
)

def create_new_card(_):
    # Use the value from the text input, or generate default if empty
    title = card_name_input.value.strip() if card_name_input.value.strip() else generate_default_card_name()
    
    new_card = make_reorderable_card(title, pn.pane.Markdown(f"Content {title.split()[-1]}"), cards_col)
    cards_col.objects = list(cards_col.objects) + [new_card]
    
    # Update the text input to the next default value
    card_name_input.value = generate_default_card_name()

add_card_button = pn.widgets.Button(name="➕ Add New Card", button_type="primary", width=150)
add_card_button.on_click(create_new_card)

pn.template.FastListTemplate(
    title="Reorderable Cards MVP",
    main=[
        pn.Column(
        card_name_input,
        add_card_button,
        ),
        cards_col
    ],
).servable()