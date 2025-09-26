import pandas as pd
import panel as pn
from io import StringIO
from typing import Dict, Any

# Enable the Panel extensions (required for Tabulator to work)
pn.extension('tabulator', sizing_mode="stretch_width")


# --- 1. Your core function ---
def myfun(x: float, y: float) -> Dict[str, float]:
    """The function to explore with different scenarios."""
    # The outputs are calculated here
    res_1 = x * y
    res_2 = x - y

    return {
        "res_1": res_1,
        "res_2": res_2
    }


class ScenarioExplorer(pn.viewable.Viewer):
    # Initial data for the scenarios
    initial_data = {
        'Scenario': ['A', 'B'],
        'x': [10.0, 5.0],
        'y': [2.0, 3.0],
        'res_1': [0.0, 0.0],  # Placeholder for output
        'res_2': [0.0, 0.0]   # Placeholder for output
    }

    def __init__(self, function):
        self.function = function

        # 1. Initialize DataFrame (MUST be first)
        self.df = pd.DataFrame(self.initial_data).set_index('Scenario')

        # --- Panel Components ---

        # 2. Create the editable table (MUST be created before run_all_scenarios)
        self.tabulator = pn.widgets.Tabulator(
            self.df,
            layout='fit_columns',
            # Allow editing only of the input columns (x, y)
            editors={
                'x': 'number',
                'y': 'number',
                'res_1': None,  # Disable editing outputs
                'res_2': None  # Disable editing outputs
            },
            # Allow scenario name editing (the index column)
            configuration={'headerFilter': False, 'selectable': 'checkbox', 'index': 'select'},
            titles={
                'x': 'Input x',
                'y': 'Input y',
                'res_1': 'Output x*y',
                'res_2': 'Output x-y'
            },
            sortable=False,
            row_height=30
        )

        # 3. Compute initial results (NOW it can be safely called)
        # This will populate the initial df and update the tabulator.value
        self.run_all_scenarios()

        # 4. Control buttons
        self.add_button = pn.widgets.Button(name="➕ Add Scenario", button_type="primary")
        self.remove_button = pn.widgets.Button(name="❌ Remove Selected", button_type="danger")

        # 5. Bind callbacks to events
        self.add_button.on_click(self.add_scenario)
        self.remove_button.on_click(self.remove_scenario)
        # Tabulator on_edit event is key to re-running the function
        self.tabulator.on_edit(self.handle_edit)

        # 6. Lay out the application
        self.app = pn.Column(
            pn.Row(self.add_button, self.remove_button),
            self.tabulator,
            pn.pane.Markdown(
                "### Instructions: Edit 'Input x' and 'Input y' cells and press 'Enter' to update results.",
                styles={'font-style': 'italic'})
        )

    # --- Controller Logic ---

    # def run_all_scenarios(self):
    #     """Re-run the function for all scenarios in the DataFrame."""
    #     for scenario_name, row in self.df.iterrows():
    #         x = row['x']
    #         y = row['y']
    #         output = self.function(x, y)
    #         self.df.loc[scenario_name, 'res_1'] = output['res_1']
    #         self.df.loc[scenario_name, 'res_2'] = output['res_2']
    #     # Set to a *copy* to ensure Panel detects the change and updates the UI
    #     self.tabulator.value = self.df.copy()
    #
    # def handle_edit(self, event):
    #     """Called when a cell is edited in the Tabulator."""
    #     # Tabulator event has the new value, column name, and row index
    #     scenario_name = self.df.index[event.row]
    #     column_name = event.column
    #
    #     if column_name in ['x', 'y']:
    #         try:
    #             new_value = float(event.new)
    #             # Update the DataFrame with the new input value
    #             self.df.loc[scenario_name, column_name] = new_value
    #             # Re-run *only* the scenario that changed
    #             output = self.function(self.df.loc[scenario_name, 'x'], self.df.loc[scenario_name, 'y'])
    #             self.df.loc[scenario_name, 'res_1'] = output['res_1']
    #             self.df.loc[scenario_name, 'res_2'] = output['res_2']
    #             # Force update the Tabulator to show the new inputs/outputs
    #             self.tabulator.value = self.df.copy()
    #         except ValueError:
    #             print(f"Invalid input for {column_name}: {event.new}. Must be a number.")
    #             # Force update to revert the UI change if input was invalid
    #             self.tabulator.value = self.df.copy()

    def handle_edit(self, event):
        """Called when a cell is edited in the Tabulator."""

        # 1. Get data directly from the event payload
        # The key for the new value in the event object is often 'value', not 'new'.
        # Note: If this still fails, you may need to access event.value['value']
        # or use the pre-updated self.df instead.
        try:
            # Assuming 'value' holds the new cell content for the Tabulator edit event
            new_value_str = str(event.value)
            column_name = event.column
            scenario_index = event.row

            if column_name in ['x', 'y']:
                try:
                    new_value = float(new_value_str)

                    # Update the internal DataFrame with the new input value
                    # NOTE: Since the edit already updated the underlying dataframe
                    # in the Tabulator model, we should reload it first to ensure
                    # our self.df is in sync, or better, just use the Tabulator's current value.

                    # Let's rely on the Tabulator having updated the underlying DataFrame first.
                    # We will update self.df from the Tabulator's current value.
                    self.df = self.tabulator.value
                    scenario_name = self.df.index[scenario_index]

                    # Re-run *only* the scenario that changed
                    x = self.df.loc[scenario_name, 'x']
                    y = self.df.loc[scenario_name, 'y']

                    # Ensure we use the latest values for calculation
                    if column_name == 'x': x = new_value
                    if column_name == 'y': y = new_value

                    output = self.function(x, y)

                    # Update the output columns in the internal DataFrame
                    self.df.loc[scenario_name, 'res_1'] = output['res_1']
                    self.df.loc[scenario_name, 'res_2'] = output['res_2']

                    # Force update the Tabulator to show the new outputs
                    # By setting .value = df.copy(), you ensure the outputs are displayed.
                    self.tabulator.value = self.df.copy()

                except ValueError:
                    # Handle case where user types non-numeric text
                    print(f"Invalid input for {column_name}: {new_value_str}. Must be a number.")
                    # Force update to revert the UI change if input was invalid
                    self.tabulator.value = self.df.copy()  # Reverts the visual change

        except AttributeError as e:
            print(f"Tabulator event structure changed. Debug event object: {dir(event)}")
            print(f"Original error: {e}")
            # If the above fails, you can fall back to re-running ALL scenarios
            # after reading the whole updated table.
            self.df = self.tabulator.value
            self.run_all_scenarios()  # Fallback to full re-run

    # And correct run_all_scenarios to update the Tabulator's value
    # (this part was already correct but for completeness)
    def run_all_scenarios(self):
        """Re-run the function for all scenarios in the DataFrame."""
        for scenario_name, row in self.df.iterrows():
            x = row['x']
            y = row['y']
            output = self.function(x, y)
            self.df.loc[scenario_name, 'res_1'] = output['res_1']
            self.df.loc[scenario_name, 'res_2'] = output['res_2']
        # Set to a *copy* to ensure Panel detects the change and updates the UI
        self.tabulator.value = self.df.copy()


    def add_scenario(self, event):
        """Adds a new row/scenario with default values."""
        new_scenario_name = f'Scenario {len(self.df) + 1}'

        # Add a new row to the DataFrame
        self.df.loc[new_scenario_name] = [1.0, 1.0, 0.0, 0.0]

        # Run the new scenario with default inputs
        self.run_all_scenarios()

    def remove_scenario(self, event):
        """Removes the scenarios currently checked in the Tabulator."""
        if not self.tabulator.selected_indices:
            return

        # Get the names of the scenarios to remove
        scenarios_to_remove = self.df.iloc[self.tabulator.selected_indices].index

        # Drop them from the DataFrame
        self.df.drop(scenarios_to_remove, inplace=True)

        # Update the Tabulator value
        self.tabulator.value = self.df.copy()

    # Required for Panel's Viewer protocol
    def __panel__(self):
        return self.app

# --- 3. Run the App ---

# Instantiate the explorer with your function
explorer = ScenarioExplorer(myfun)

# Serve the application
explorer.app.servable(title="Side-by-Side Scenario Explorer with Panel")