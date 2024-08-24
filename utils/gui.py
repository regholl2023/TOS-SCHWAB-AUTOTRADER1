import tkinter as tk
from tkinter import ttk
from threading import Thread
import time
import os
from account import order_executer
from stream import get_last_x_minutes_data
from utils.ema import calculate_ema_and_bands
from account.order_executer import get_active_orders, poll_active_orders, start_polling

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

def update_active_orders_panel(active_orders_tree):
    """Update the active orders panel with the latest active orders info."""
    while True:
        active_orders = get_active_orders()

        # Clear the tree view
        for row in active_orders_tree.get_children():
            active_orders_tree.delete(row)

        # Insert active orders details
        for order in active_orders:
            active_orders_tree.insert("", "end", values=(order["order_type"], order["ticker"], order["price"], order["status"]))
        
        time.sleep(1)  # Refresh every second

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

import datetime  # Add this import for timestamps

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

                # Generate the current timestamp
                timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

                # Check for alerts
                if last_price > upper_band:
                    alert_message = f"{timestamp} - SELL ALERT: Last price {last_price} is above the upper band {upper_band}!"
                    alert_text.insert(tk.END, alert_message + "\n", "alert-sell")
                elif last_price < lower_band:
                    alert_message = f"{timestamp} - BUY ALERT: Last price {last_price} is below the lower band {lower_band}!"
                    alert_text.insert(tk.END, alert_message + "\n", "alert-buy")
                
                alert_text.see(tk.END)  # Automatically scroll to the end

        time.sleep(1)  # Monitor every 1 second

def update_order_log(alert_text):
    """Monitor and update the alert_text panel, filtering for alternating Buy/Sell orders."""
    log_file_path = "orders.log"
    
    if not os.path.exists(log_file_path):
        return  # Exit if log file doesn't exist

    last_position = 0  # Track last position in the log file
    last_order_type = None  # Track the last processed order type

    while True:
        with open(log_file_path, "r") as log_file:
            log_file.seek(last_position)  # Move to the last position
            new_lines = log_file.readlines()  # Read new lines
            last_position = log_file.tell()  # Update the last position

        # Add new lines to the alert_text widget
        for line in new_lines:
            order_type = "Buy" if "BUY" in line.upper() else "Sell" if "SELL" in line.upper() else None
            if order_type and order_type != last_order_type:  # Filter for alternating orders
                alert_text.insert(tk.END, line.strip() + "\n")
                last_order_type = order_type  # Update the last processed order type

        alert_text.see(tk.END)  # Automatically scroll to the end
        time.sleep(1)  # Check for new logs every 1 second

def setup_gui(start_stream, client, account_hash):
    """Setup the tkinter GUI and start the stream and monitoring."""
    # Create the main window
    root = tk.Tk()
    root.title("Live Data Stream & EMA Monitor")

    # Create the live data panel
    live_data_frame = tk.Frame(root)
    live_data_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

    # Create a label for the stock data panel
    stock_data_label = tk.Label(live_data_frame, text="Stock Data", font=("Helvetica", 16))
    stock_data_label.pack()

    # Create a Treeview for displaying live ticker data
    live_data_tree = ttk.Treeview(live_data_frame, columns=("Field", "Value"), show="headings")
    live_data_tree.heading("Field", text="Field")
    live_data_tree.heading("Value", text="Value")
    live_data_tree.pack(fill=tk.BOTH, expand=True)

    # Create the right panel for EMA, active orders, and logs
    right_panel = tk.Frame(root)
    right_panel.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)

    # Create the EMA and bounds panel at the top of the right panel
    ema_frame = tk.Frame(right_panel)
    ema_frame.pack(side=tk.TOP, fill=tk.BOTH, expand=True)

    # Create a label for the EMA data panel
    ema_label = tk.Label(ema_frame, text="EMA Data", font=("Helvetica", 16))
    ema_label.pack()

    # Create a Treeview for displaying EMA, bounds, and last price
    ema_tree = ttk.Treeview(ema_frame, columns=("Metric", "Value"), show="headings")
    ema_tree.heading("Metric", text="Metric")
    ema_tree.heading("Value", text="Value")
    ema_tree.pack(fill=tk.BOTH, expand=True)

    # Create a frame for logs and active orders under the EMA frame
    logs_and_orders_frame = tk.Frame(right_panel)
    logs_and_orders_frame.pack(side=tk.TOP, fill=tk.BOTH, expand=True)

    # Create the active orders panel on the right side of logs_and_orders_frame
    active_orders_frame = tk.Frame(logs_and_orders_frame)
    active_orders_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)

    # Create a label for the active orders panel
    active_orders_label = tk.Label(active_orders_frame, text="Active Orders", font=("Helvetica", 16))
    active_orders_label.pack()

    # Create a Treeview for displaying active orders
    active_orders_tree = ttk.Treeview(active_orders_frame, columns=("Order Type", "Ticker", "Price", "Status"), show="headings")
    active_orders_tree.heading("Order Type", text="Order Type")
    active_orders_tree.heading("Ticker", text="Ticker")
    active_orders_tree.heading("Price", text="Price")
    active_orders_tree.heading("Status", text="Status")
    active_orders_tree.pack(fill=tk.BOTH, expand=True)

    # Create the alerts panel at the bottom
    alert_frame = tk.Frame(root)
    alert_frame.pack(side=tk.BOTTOM, fill=tk.BOTH, expand=True)

    # Create a label for the alerts panel
    alerts_label = tk.Label(alert_frame, text="Alerts", font=("Helvetica", 16))
    alerts_label.pack()

    # Create a ScrolledText for displaying alerts
    alert_text = tk.Text(alert_frame, height=10, wrap=tk.WORD)
    alert_text.pack(fill=tk.BOTH, expand=True)
    alert_text.tag_configure("alert-sell", foreground="red")
    alert_text.tag_configure("alert-buy", foreground="green")

    # Start the stream and monitoring in separate threads
    run_stream(live_data_tree, start_stream)
    monitor_thread = Thread(target=monitor_prices, args=(ema_tree, alert_text))
    monitor_thread.start()

    # Start updating the active orders panel
    active_orders_thread = Thread(target=update_active_orders_panel, args=(active_orders_tree,))
    active_orders_thread.start()

    # Start polling active orders in a separate thread
    start_polling(client, account_hash)  # This will run poll_active_orders in a separate thread

    # Start the order executor in a separate thread
    order_executor_thread = Thread(target=order_executer.run_order_executor, args=(active_orders_tree,))
    order_executor_thread.start()

    # Start the tkinter main loop
    root.mainloop()

def update_active_orders_panel(active_orders_tree):
    """Update the active orders panel with the latest active orders info."""
    while True:
        active_orders = get_active_orders()

        # Clear the tree view
        for row in active_orders_tree.get_children():
            active_orders_tree.delete(row)

        # Insert active orders details
        for order in active_orders:
            active_orders_tree.insert("", "end", values=(order["order_type"], order["ticker"], order["price"], order["status"]))
        
        time.sleep(1)  # Refresh every second