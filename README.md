# Webscenarios

Context: This is intended as a toolkit for creating dynamic web wrappers for Python models, similar to Gradio or
Streamlit, but with a focus on supporting the dynamic creation of widgets on the user front-end, while still maintaining
easy hooks to the underlying Python data model on the back-end.  This could be used to create a
Tableau-like dashboard builder with no user expertise required, interactive web apps which are hooked to sophisticated 
backend models, or many wrappers to a standard model.

The main alternative here is to have a fixed API which is used to wrap the model, which opens up more flexibility for 
the front-end (e.g. using Javascript) but requires both more expertise (typically a separate front-end-developer) and 
requires a clearer deployment process (even with dynamic API definition tools like OpenAPI).

This repository contains a variety of standalone scripts which demonstrate different techniques along the way to 
building the full toolkit.

The simple panel demos can be run like `panel serve --show --autoreload <scriptname>.py`

The uvicorn+panel demos can be run like `python <scriptname>.py` or `uvicorn <scriptname>:app --reload --port 8000`
- These require a postgres server to be running, and if the default Postgres URL isn't used, the URL should be overriden with the environment variable `DATABASE_URL`.

The demos go in the following order:
- `dash_demo.py`: Not fully functional (see notes below). Dash is not able to accomplish our goals.
- `panel_df_apply_demo.py`: Add and remove rows from a Tabulator data table, and trigger computations on data changes.
- `panel_demo.py`: Basic demo of being able to dynamically add and remove widgets.
- `panel_multiplying_scenario_demo.py`: Allow dynamic creation of new widgets based on the output of a process.
- `panel_formbuilder.py`: Generate a front-end with data connection purely from a JSON-ready dictionary
- `panel_reorder.py`: Reorder cards dynamically with up-and-down buttons 
- `panel_reorder_containers.py`: Create new Rows and Columns dynamically, allowing widgets to be shifted between parents
- `panel_datamodel.py`: Tie widgets to specific data model inputs, removing them from availability if they are bound
- `panel_datamodel_formbuilder.py`: Download the data model as a JSON-ready dictionary, and re-generate the front-end from that
- `panel_database_reader.py`: Demonstration of the ability to read/write to a database with Panel
- `panel_db_reader_with_auth.py`: Basic relationship-based access controls with admins, users, sharing/unsharing "projects" (folders) with other users, and individual projects which belong to folders.


## Dash
Dash is clearly designed for statically configured dashboards. It is unable to live-select dynamically created 
sub-widgets when the IDs for those are not known ahead of time. If you're interested in creating and removing 
widgets dynamically, particularly with now having to define a JavaScript interface for a new widget, 
I would not recommend using Dash.  This stub gives my best effort at attempting a dynamic widget creator in Dash,
but it was not fully functional.

## Panel

Panel was much better able to meet the needs of this project as it was able to create dynamic clusters of widgets 
which can then be acted on and removed, and are state-aware in a way that was much more flexible. 

To run panel in auto-reload mode:
```
panel serve panel_demo.py --autoreload --show
```

## Panel_df_apply_demo.py

This MVP demonstrates being able to dynamically apply computations to a user-interactable table. 
This could be useful for being able to add rows/scenarios to a model which has relatively light computation and 
where the apply method can be run quickly. 

## Panel_demo.py

This MVP is intended for situations where the compute function may be high-latency, 
and so we don't want to rerun the compute operation on all scenarios when one scenario changes. 
This is much closer to what a user might expect, where if they click the Compute button on one scenario, then just 
that scenario is run.
