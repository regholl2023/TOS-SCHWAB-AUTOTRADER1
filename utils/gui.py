import tkinter as tk
from tkinter import ttk
from threading import Thread
import time
from stream import get_last_x_minutes_data
from utils.ema import calculate_ema_and_bands

class RedirectText:
    def __init__(self, text_widget):
        self.output = text_widget

    def write(self, string):
        self.output.insert(tk.END, string)
        self.output.see(tk.END)  # Automatically scroll to the end

    def flush(self):
        pass  # This is needed to support the flush method of sys.stdout

def update_live_data_table(tree, data, existing_items):
    """Update the live data table with the latest ticker data."""
    for key, value in data.items():
        if key in existing_items:
            # Update existing item only if the value has changed
            if tree.item(existing_items[key], "values")[1] != value:
                tree.item(existing_items[key], values=(key, value))
        else:
            # Insert new item if it's not already in the tree
            item_id = tree.insert("", "end", values=(key, value))
            existing_items[key] = item_id

def update_ema_table(ema_tree, ema, upper_band, lower_band, last_price, styles):
    """Update the EMA table with the latest values and apply color coding."""
    for row in ema_tree.get_children():
        ema_tree.delete(row)

    # Insert the EMA and bounds data in the desired order
    ema_tree.insert("", "end", values=("Lower Band", lower_band))
    
    # Apply color coding for the last price
    if last_price > upper_band:
        style = styles["above"]
    elif last_price < lower_band:
        style = styles["below"]
    else:
        style = styles["normal"]
    
    ema_tree.insert("", "end", values=("Last Price", last_price), tags=(style,))
    ema_tree.insert("", "end", values=("Upper Band", upper_band))
    ema_tree.insert("", "end", values=("EMA", ema))

def run_stream(tree, start_stream):
    """Run the stream and update the live data table."""
    existing_items = {}  # Keep track of inserted items

    def stream_update_handler():
        while True:
            data = get_last_x_minutes_data()
            if data:
                update_live_data_table(tree, data[-1], existing_items)
            time.sleep(1)  # Update the table every second

    # Start the stream in a separate thread
    stream_thread = Thread(target=start_stream)
    stream_thread.start()

    # Start updating the table with live data
    stream_update_thread = Thread(target=stream_update_handler)
    stream_update_thread.start()

def monitor_prices(ema_tree, alert_text, styles):
    """Monitor prices and update the EMA table and alerts."""
    while True:
        ema, upper_band, lower_band = calculate_ema_and_bands()
        latest_data = get_last_x_minutes_data()
        
        if latest_data:
            last_price = latest_data[-1].get('Last Price')
            if ema is not None and last_price is not None:
                # Update the EMA table with color coding
                update_ema_table(ema_tree, ema, upper_band, lower_band, last_price, styles)

                # Check for alerts
                if last_price > upper_band:
                    alert_text.insert(tk.END, f"ALERT: Last price {last_price} is above the upper band {upper_band}!\n", "alert")
                elif last_price < lower_band:
                    alert_text.insert(tk.END, f"ALERT: Last price {last_price} is below the lower band {lower_band}!\n", "alert")
                alert_text.see(tk.END)  # Automatically scroll to the end

        time.sleep(5)  # Monitor every 5 seconds

def setup_gui(start_stream):
    """Setup the tkinter GUI and start the stream and monitoring."""
    # Create the main window
    root = tk.Tk()
    root.title("Live Data Stream & EMA Monitor")

    # Define styles for the Treeview
    style = ttk.Style(root)
    style.configure("AboveBand.TLabel", foreground="green")
    style.configure("BelowBand.TLabel", foreground="red")
    style.configure("Normal.TLabel", foreground="black")
    
    # Define styles for the alerts
    styles = {
        "above": "AboveBand.TLabel",
        "below": "BelowBand.TLabel",
        "normal": "Normal.TLabel",
    }

    # Create the live data panel
    live_data_frame = tk.Frame(root)
    live_data_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

    # Create a Treeview for displaying live ticker data
    live_data_tree = ttk.Treeview(live_data_frame, columns=("Field", "Value"), show="headings")
    live_data_tree.heading("Field", text="Field")
    live_data_tree.heading("Value", text="Value")
    live_data_tree.pack(fill=tk.BOTH, expand=True)

    # Create the EMA and bounds panel
    ema_frame = tk.Frame(root)
    ema_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)

    # Create a Treeview for displaying EMA, bounds, and last price
    ema_tree = ttk.Treeview(ema_frame, columns=("Metric", "Value"), show="headings")
    ema_tree.heading("Metric", text="Metric")
    ema_tree.heading("Value", text="Value")
    ema_tree.tag_configure("AboveBand.TLabel", foreground="green")
    ema_tree.tag_configure("BelowBand.TLabel", foreground="red")
    ema_tree.tag_configure("Normal.TLabel", foreground="black")
    ema_tree.pack(fill=tk.BOTH, expand=True)

    # Create the alerts panel
    alert_frame = tk.Frame(root)
    alert_frame.pack(side=tk.BOTTOM, fill=tk.BOTH, expand=True)

    # Create a ScrolledText for displaying alerts
    alert_text = tk.Text(alert_frame, height=10, wrap=tk.WORD)
    alert_text.pack(fill=tk.BOTH, expand=True)
    alert_text.tag_configure("alert", foreground="red")

    # Start the stream and monitoring in separate threads
    run_stream(live_data_tree, start_stream)
    monitor_thread = Thread(target=monitor_prices, args=(ema_tree, alert_text, styles))
    monitor_thread.start()

    # Start the tkinter main loop
    root.mainloop()
