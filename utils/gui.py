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

def get_color_based_on_proximity(last_price, lower_band, upper_band, ema):
    """Return a color tag based on the proximity of the last price to the bands."""
    if last_price == ema:
        return "black"  # Last price is exactly at the EMA

    range_span = upper_band - lower_band

    if last_price >= upper_band:
        return "deep_red"
    elif last_price <= lower_band:
        return "deep_green"
    elif last_price > ema:
        # Calculate proximity percentage for red gradient
        upper_proximity = (last_price - ema) / (upper_band - ema)
        if upper_proximity > 0.75:
            return "deep_red"
        elif upper_proximity > 0.5:
            return "medium_red"
        elif upper_proximity > 0.25:
            return "light_red"
        else:
            return "normal"
    else:
        # Calculate proximity percentage for green gradient
        lower_proximity = (ema - last_price) / (ema - lower_band)
        if lower_proximity > 0.75:
            return "deep_green"
        elif lower_proximity > 0.5:
            return "medium_green"
        elif lower_proximity > 0.25:
            return "light_green"
        else:
            return "normal"

def update_ema_table(ema_tree, ema, upper_band, lower_band, last_price):
    """Update the EMA table with the latest values and apply color coding."""
    for row in ema_tree.get_children():
        ema_tree.delete(row)

    # Insert the EMA and bounds data in the desired order
    ema_tree.insert("", "end", values=("EMA", ema), tags=("black",))

    # Always color the Upper Band in the deepest red
    ema_tree.insert("", "end", values=("Upper Band", upper_band), tags=("deep_red",))

    # Determine the color for the Last Price based on proximity and the EMA
    color_tag = get_color_based_on_proximity(last_price, lower_band, upper_band, ema)
    ema_tree.insert("", "end", values=("Last Price", last_price), tags=(color_tag,))

    # Always color the Lower Band in the deepest green
    ema_tree.insert("", "end", values=("Lower Band", lower_band), tags=("deep_green",))

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
                # Update the EMA table with color coding
                update_ema_table(ema_tree, ema, upper_band, lower_band, last_price)

                # Check for alerts
                if last_price > upper_band:
                    alert_text.insert(tk.END, f"SELL ALERT: Last price {last_price} is above the upper band {upper_band}!\n", "alert-sell")
                elif last_price < lower_band:
                    alert_text.insert(tk.END, f"BUY ALERT: Last price {last_price} is below the lower band {lower_band}!\n", "alert-buy")
                alert_text.see(tk.END)  # Automatically scroll to the end

        time.sleep(5)  # Monitor every 5 seconds

def update_orders_table(orders_tree, new_order):
    """Add a new order to the orders table."""
    orders_tree.insert("", "end", values=(new_order["Order ID"], new_order["Symbol"], new_order["Type"], new_order["Quantity"], new_order["Status"]))

def setup_gui(start_stream):
    """Setup the tkinter GUI and start the stream and monitoring."""
    # Create the main window
    root = tk.Tk()
    root.title("Live Data Stream & EMA Monitor")

    # Define styles for the Treeview
    style = ttk.Style(root)
    style.configure("DeepRed.TLabel", foreground="#8B0000")  # Deep red
    style.configure("MediumRed.TLabel", foreground="#CD5C5C")  # Medium red
    style.configure("LightRed.TLabel", foreground="#F08080")  # Light red
    style.configure("DeepGreen.TLabel", foreground="#006400")  # Deep green
    style.configure("MediumGreen.TLabel", foreground="#32CD32")  # Medium green
    style.configure("LightGreen.TLabel", foreground="#90EE90")  # Light green
    style.configure("Black.TLabel", foreground="black")

    # Define styles for the alerts
    styles = {
        "deep_red": "DeepRed.TLabel",
        "medium_red": "MediumRed.TLabel",
        "light_red": "LightRed.TLabel",
        "deep_green": "DeepGreen.TLabel",
        "medium_green": "MediumGreen.TLabel",
        "light_green": "LightGreen.TLabel",
        "black": "Black.TLabel",
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
    ema_tree.tag_configure("upper_band", background="#8B0000")
    ema_tree.tag_configure("lower_band", background="#006400")
    ema_tree.tag_configure("deep_red", background="#8B0000")
    ema_tree.tag_configure("medium_red", background="#CD5C5C")
    ema_tree.tag_configure("light_red", background="#F08080")
    ema_tree.tag_configure("deep_green", background="#006400")
    ema_tree.tag_configure("medium_green", background="#32CD32")
    ema_tree.tag_configure("light_green", background="#90EE90")
    ema_tree.tag_configure("black", background="white")
    ema_tree.pack(fill=tk.BOTH, expand=True)

    # Create the alerts panel
    alert_frame = tk.Frame(root)
    alert_frame.pack(side=tk.BOTTOM, fill=tk.BOTH, expand=True)

    # Create a ScrolledText for displaying alerts
    alert_text = tk.Text(alert_frame, height=10, wrap=tk.WORD)
    alert_text.pack(fill=tk.BOTH, expand=True)
    alert_text.tag_configure("alert-sell", foreground="red")
    alert_text.tag_configure("alert-buy", foreground="green")

    # Create the orders panel
    orders_frame = tk.Frame(root)
    orders_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)

    # Create a Treeview for displaying orders
    orders_tree = ttk.Treeview(orders_frame, columns=("Order ID", "Symbol", "Type", "Quantity", "Status"), show="headings")
    orders_tree.heading("Order ID", text="Order ID")
    orders_tree.heading("Symbol", text="Symbol")
    orders_tree.heading("Type", text="Type")
    orders_tree.heading("Quantity", text="Quantity")
    orders_tree.heading("Status", text="Status")
    orders_tree.pack(fill=tk.BOTH, expand=True)

    # Start the stream and monitoring in separate threads
    run_stream(live_data_tree, start_stream)
    monitor_thread = Thread(target=monitor_prices, args=(ema_tree, alert_text))
    monitor_thread.start()

    # Simulate adding an order (replace this with actual order handling logic)
    # You can call `update_orders_table` whenever a new order is made
    example_order = {"Order ID": "1234", "Symbol": "AAPL", "Type": "BUY", "Quantity": 10, "Status": "Completed"}
    update_orders_table(orders_tree, example_order)

    # Start the tkinter main loop
    root.mainloop()
