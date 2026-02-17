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
- IMPORTANT: See the below note about websocket gotchas when running Panel with Uvicorn
- These require a postgres server to be running, and if the default Postgres URL isn't used, the URL should be overriden with the environment variable `DATABASE_URL`.

The demos go in the following order:
- `00_dash_demo.py`: Not fully functional (see notes below). Dash is not able to accomplish our goals.
- `01_panel_df_apply_demo.py`: Add and remove rows from a Tabulator data table, and trigger computations on data changes.
- `02_panel_demo.py`: Basic demo of being able to dynamically add and remove widgets.
- `03_panel_multiplying_scenario_demo.py`: Allow dynamic creation of new widgets based on the output of a process.
- `04_panel_formbuilder.py`: Generate a front-end with data connection purely from a JSON-ready dictionary
- `05_panel_reorder.py`: Reorder cards dynamically with up-and-down buttons 
- `06_panel_reorder_containers.py`: Create new Rows and Columns dynamically, allowing widgets to be shifted between parents
- `07_panel_datamodel.py`: Tie widgets to specific data model inputs, removing them from availability if they are bound
- `08_panel_datamodel_formbuilder.py`: Download the data model as a JSON-ready dictionary, and re-generate the front-end from that
- `09_uvicorn_panel_database_reader.py`: Demonstration of the ability to read/write to a database with Panel
- `10_uvicorn_panel_db_reader_with_users.py`: Basic relationship-based access controls with admins, users, sharing/unsharing "projects" (folders) with other users, and individual projects which belong to folders.

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

## Panel + Uvicorn Gotchas

### Cookie size
Websocket has a limited cookie capacity.  If you have been using `localhost` for a lot of development, you may have
accumulated many cookies, to the point that Bokeh/Websocket will refuse to parse the cookies when the HTTP request is
handed from Uvicorn to Bokeh. **This can result in a silent failure which produces no logs but the app doesn't load.**

To diagnose this:
- Check whether you are able to run successfully from 0.0.0.0 or 127.0.0.1 instead of localhost
- Try clearing the local site cookies (Chrome Inspect -> Applications -> Cookies)

## Panel_df_apply_demo.py

This MVP demonstrates being able to dynamically apply computations to a user-interactable table. 
This could be useful for being able to add rows/scenarios to a model which has relatively light computation and 
where the apply method can be run quickly. 

## Panel_demo.py

This MVP is intended for situations where the compute function may be high-latency, 
and so we don't want to rerun the compute operation on all scenarios when one scenario changes. 
This is much closer to what a user might expect, where if they click the Compute button on one scenario, then just 
that scenario is run.

## Panel_auth_demo.py

This is taken directly from the Panel [auth configuration documentation here](https://panel.holoviz.org/how_to/authentication/configuration.html#providers),
and is reliant on the following command line arguments:
- `--oauth-provider` : tested with `google, azure`
- `--oauth-key`: This is typically called the "client id" in the oauth provider configuration.
- `--oauth-secret`: Add credentials in the provider panel, and copy the disappearing secret and use it here.
- `--cookie-secret`: Generated by running `$ panel secret` one time

### Notes on Google OAuth setup
[This Youtube Video was helpful](https://www.youtube.com/watch?v=OK_j05bxmH4) for a live walk-through of how to create
an OAuth client on the Google Cloud Platform.  This worked smoothly for me.

### Notes on Microsoft Azure OAuth setup
**Important note:** This must be set up from Microsoft **Azure**, not Microsoft Entra. Setting up on Entra kept me in an 
infinite authentication loop and never went back to the target app.

I used the "Quickstart" sample code which implements a Flask app. Two general notes about this Quicktart example:
1. You need to set the environment variables in the .env file within the quickstart app.
2. See the below note on Flask and OAuth

### Flask and OAuth on Mac
A critical but subtle note: Your redirect URI needs to be on localhost, but flask generally supports IPv4, 
and listens to 127.0.0.1 as the directory loop for `localhost`. On Mac, localhost can resolve to the IPv6 loopback 
address `::1` if the IPv4 port isn't responsive. This can result in a 403 error "Access to localhost was denied", 
while Flask doesn't provide any error messages.

To debug this: 
- Without Flask running, confirm whether there are any processes listening to localhost:5000 by running `$ lsof -i :5000`.
- **If you see any other processes listening to localhost:5000, change the port which Flask is being served on to something free

## Supabase, auth, and RLS
[Helpful blog post by dob about RLS in SqlAlchemy](https://dobken.nl/posts/rls-postgres/)