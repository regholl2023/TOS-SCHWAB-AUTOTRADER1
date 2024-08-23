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

def get_highlight_based_on_proximity(last_price, lower_band, upper_band, ema):
    """Return a highlight tag based on the proximity of the last price to the bands."""
    if last_price == ema:
        return "highlight-black"  # Last price is exactly at the EMA

    range_span = upper_band - lower_band

    if last_price >= upper_band:
        return "highlight-deep_red"
    elif last_price <= lower_band:
        return "highlight-deep_green"
    elif last_price > ema:
        # Calculate proximity percentage for red gradient
        upper_proximity = (last_price - ema) / (upper_band - ema)
        if upper_proximity > 0.75:
            return "highlight-deep_red"
        elif upper_proximity > 0.5:
            return "highlight-medium_red"
        elif upper_proximity > 0.25:
            return "highlight-light_red"
        else:
            return "highlight-normal"
    else:
        # Calculate proximity percentage for green gradient
        lower_proximity = (ema - last_price) / (ema - lower_band)
        if lower_proximity > 0.75:
            return "highlight-deep_green"
        elif lower_proximity > 0.5:
            return "highlight-medium_green"
        elif lower_proximity > 0.25:
            return "highlight-light_green"
        else:
            return "highlight-normal"

def update_ema_table(ema_tree, ema, upper_band, lower_band, last_price):
    """Update the EMA table with the latest values and apply background highlighting."""
    for row in ema_tree.get_children():
        ema_tree.delete(row)

    # Insert the EMA and bounds data in the desired order with highlight tags
    ema_tree.insert("", "end", values=("EMA", ema), tags=("highlight-black",))

    # Always highlight the Upper Band in the deepest red
    ema_tree.insert("", "end", values=("Upper Band", upper_band), tags=("highlight-deep_red",))

    # Determine the highlight for the Last Price based on proximity and the EMA
    highlight_tag = get_highlight_based_on_proximity(last_price, lower_band, upper_band, ema)
    ema_tree.insert("", "end", values=("Last Price", last_price), tags=(highlight_tag,))

    # Always highlight the Lower Band in the deepest green
    ema_tree.insert("", "end", values=("Lower Band", lower_band), tags=("highlight-deep_green",))

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

def monitor_prices(ema_tree, alert_text):
    """Monitor prices and update the EMA table and alerts."""
    while True:
        ema, upper_band, lower_band = calculate_ema_and_bands()
        latest_data = get_last_x_minutes_data()
        
        if latest_data:
            last_price = latest_data[-1].get('Last Price')
            if ema is not None and last_price is not None:
                # Update the EMA table with background highlighting
                update_ema_table(ema_tree, ema, upper_band, lower_band, last_price)

                # Check for alerts
                if last_price > upper_band:
                    alert_text.insert(tk.END, f"SELL ALERT: Last price {last_price} is above the upper band {upper_band}!\n", "alert-sell")
                elif last_price < lower_band:
                    alert_text.insert(tk.END, f"BUY ALERT: Last price {last_price} is below the lower band {lower_band}!\n", "alert-buy")
                alert_text.see(tk.END)  # Automatically scroll to the end

        time.sleep(5)  # Monitor every 5 seconds

def setup_gui(start_stream):
    """Setup the tkinter GUI and start the stream and monitoring."""
    # Create the main window
    root = tk.Tk()
    root.title("Live Data Stream & EMA Monitor")

    # Define styles for the Treeview with background highlights
    style = ttk.Style(root)
    style.configure("highlight-deep_red.TLabel", background="#8B0000")  # Deep red
    style.configure("highlight-medium_red.TLabel", background="#CD5C5C")  # Medium red
    style.configure("highlight-light_red.TLabel", background="#F08080")  # Light red
    style.configure("highlight-deep_green.TLabel", background="#006400")  # Deep green
    style.configure("highlight-medium_green.TLabel", background="#32CD32")  # Medium green
    style.configure("highlight-light_green.TLabel", background="#90EE90")  # Light green
    style.configure("highlight-black.TLabel", background="black", foreground="white")  # Black background with white text

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
    ema_tree.tag_configure("highlight-upper_band", background="red")
    ema_tree.tag_configure("highlight-lower_band", background="green")
    ema_tree.tag_configure("highlight-deep_red", background="#8B0000")
    ema_tree.tag_configure("highlight-medium_red", background="#CD5C5C")
    ema_tree.tag_configure("highlight-light_red", background="#F08080")
    ema_tree.tag_configure("highlight-deep_green", background="#006400")
    ema_tree.tag_configure("highlight-medium_green", background="#32CD32")
    ema_tree.tag_configure("highlight-light_green", background="#90EE90")
    ema_tree.tag_configure("highlight-black", background="black", foreground="white")  # Black background with white text
    ema_tree.pack(fill=tk.BOTH, expand=True)

    # Create the alerts panel
    alert_frame = tk.Frame(root)
    alert_frame.pack(side=tk.BOTTOM, fill=tk.BOTH, expand=True)

    # Create a ScrolledText for displaying alerts
    alert_text = tk.Text(alert_frame, height=10, wrap=tk.WORD)
    alert_text.pack(fill=tk.BOTH, expand=True)
    alert_text.tag_configure("alert-sell", foreground="red")
    alert_text.tag_configure("alert-buy", foreground="green")

    # Start the stream and monitoring in separate threads
    run_stream(live_data_tree, start_stream)
    monitor_thread = Thread(target=monitor_prices, args=(ema_tree, alert_text))
    monitor_thread.start()

    # Start the tkinter main loop
    root.mainloop()
