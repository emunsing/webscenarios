# Webscenarios

## Dash
Ash is clearly designed for statically configured dashboards. It is unable to live-select dynamically created 
sub-widgets when the IDs for those are not known ahead of time. If you're interested in creating and removing 
widgets dynamically, particularly with now having to define a JavaScript interface for a new widget, 
I would not recommend using Dash.

## Panel

Panel was much better able to meet the needs of this project as it was able to create dynamic clusters of widgets 
which can then be acted on and removed, and are state-aware in a way that was much more flexible. 

To run panel in auto-reload mode:
```
panel serve panel_demo.py --autoreload --show
```

## Panel_df_apply_demo

This MVP demonstrates being able to dynamically apply computations to a user-interactable table. 
This could be useful for being able to add rows/scenarios to a model which has relatively light computation and 
where the apply method can be run quickly. 

## Panel_demo

This MVP is intended for situations where the compute function may be high-latency, 
and so we don't want to rerun the compute operation on all scenarios when one scenario changes. 
This is much closer to what a user might expect, where if they click the Compute button on one scenario, then just 
that scenario is run.