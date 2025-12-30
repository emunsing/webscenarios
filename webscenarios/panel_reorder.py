import panel as pn

pn.extension()

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

    header = pn.Row(
        pn.pane.Markdown(f"**{title}**", margin=(6, 8, 0, 8)),
        pn.Spacer(),
        up,
        down,
        sizing_mode="stretch_width",
        margin=(0, 0, 0, 0),
    )

    # Put header inside the card itself (so it looks like a "card header")
    card = pn.Card(
        body,
        header=header,
        title=title,                 # we render our own title in header
        collapsible=False,
        sizing_mode="stretch_width",
        margin=(5, 0),
    )

    def on_up(_):
        idx = container.objects.index(card)
        move(container, idx, -1)

    def on_down(_):
        idx = container.objects.index(card)
        move(container, idx, +1)

    up.on_click(on_up)
    down.on_click(on_down)

    return card

# Global column we will reorder
cards_col = pn.Column(sizing_mode="stretch_width")

# Build 3 example cards
c1 = make_reorderable_card("Card A", pn.pane.Markdown("Content A"), cards_col)
c2 = make_reorderable_card("Card B", pn.pane.Markdown("Content B"), cards_col)
c3 = make_reorderable_card("Card C", pn.pane.Markdown("Content C"), cards_col)

cards_col.objects = [c1, c2, c3]

pn.template.FastListTemplate(
    title="Reorderable Cards MVP",
    main=[pn.pane.Markdown("Click ▲/▼ to reorder:"), cards_col],
).servable()