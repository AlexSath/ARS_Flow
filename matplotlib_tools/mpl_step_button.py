import matplotlib.pyplot as plt
import numpy as np
import ipywidgets as widgets
from IPython.display import display

class StepViewer:
    def __init__(self, fig, ax, max_iterations=5):
        """
        Initializes an independent interactive loop viewer.
        
        Parameters:
        -----------
        max_iterations : int
            The total number of steps to iterate through.
        """
        self.max_iterations = max_iterations
        self.current_iteration = 1
        
        # 1. get axes
        self.fig = fig
        self.ax = ax
        
        # 2. Build the browser-native Next button
        self.btn_next = widgets.Button(
            description=f"Next ({self.current_iteration}/{self.max_iterations})", 
            button_style='primary'
        )
        self.btn_next.on_click(self._on_button_click)
        
        # 3. Perform initial plot render
        self._update_plot()
        
    def _update_plot(self):
        """Internal method to update the canvas data."""
        # Safely refresh only this specific widget canvas context
        self.fig.canvas.draw_idle()

    def _on_button_click(self, change):
        """Internal callback to handle the progression logic."""
        if self.current_iteration < self.max_iterations:
            self.current_iteration += 1
            self._update_plot()
            self.btn_next.description = f"Next ({self.current_iteration}/{self.max_iterations})"
        else:
            self.btn_next.description = "Finished Plotting"
            self.btn_next.disabled = True

    def show(self):
        """Public method to cleanly render the widget layout inside Jupyter."""
        # Ensure the canvas isn't hidden by standard cell outputs
        display(self.fig.canvas)
        display(self.btn_next)

