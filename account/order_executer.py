import threading
from account.order import place_buy_order_with_trailing_stop, place_market_sell_order, get_account_hash
from stream import get_last_x_minutes_data
from utils.ema import calculate_ema_and_bands
import time
from config import TICKER_SYMBOL
import schwabdev
from dotenv import load_dotenv
import os

# Load environment variables
load_dotenv()
APP_KEY = os.getenv("APP_KEY")
APP_SECRET = os.getenv("APP_SECRET")
REDIRECT_URL = os.getenv("REDIRECT_URL")
TOKENS_FILE = os.getenv("TOKENS_FILE")

# Initialize the Schwab client
client = schwabdev.Client(APP_KEY, APP_SECRET, REDIRECT_URL, TOKENS_FILE)

# List to track active orders
active_orders = []

def add_active_order(order_type, ticker, price, status="Active", order_id=None):
    """Add a new active order to the list."""
    active_orders.append({
        "order_type": order_type,
        "ticker": ticker,
        "price": price,
        "status": status,
        "order_id": order_id
    })

def get_active_orders():
    """Return the current active orders."""
    return active_orders

def update_order_status(order_id, new_status):
    """Update the status of an order."""
    global active_orders
    for order in active_orders:
        if order.get("order_id") == order_id:
            order["status"] = new_status

# Poll active orders in a separate thread to avoid blocking the main thread
def poll_active_orders(client, account_hash):
    """Poll active orders and update their status."""
    while True:
        for order in active_orders:
            order_id = order.get("order_id")
            if order_id:
                # Fetch order details from Schwab API
                response = client.order_details(account_hash, order_id)
                if response.ok:
                    order_details = response.json()
                    if order_details.get("status") == "CANCELED":
                        update_order_status(order_id, "Canceled")
                    elif order_details.get("status") == "FILLED":
                        update_order_status(order_id, "Filled")
        time.sleep(1)  # Poll every second

# Create a function to start polling in a new thread
def start_polling(client, account_hash):
    polling_thread = threading.Thread(target=poll_active_orders, args=(client, account_hash))
    polling_thread.daemon = True  # This ensures that the thread exits when the main program does
    polling_thread.start()

def run_order_executor(orders_tree_widget):
    global active_orders
    last_alert_type = None  # Track the last alert type to alternate between buy and sell orders
    first_order_placed = False  # Ensure we start with a buy order

    # Retrieve the account hash at the beginning
    account_hash = get_account_hash(client)
    if not account_hash:
        print("Failed to retrieve account hash. Exiting order executor.")
        return

    while True:
        # Get EMA and bands data
        ema, upper_band, lower_band = calculate_ema_and_bands()
        latest_data = get_last_x_minutes_data()

        if latest_data:
            last_price = latest_data[-1].get('Last Price')
            if ema is not None and last_price is not None:
                # Ensure we start with a buy order
                if not first_order_placed:
                    if last_price < lower_band:
                        alert_message = f"BUY ALERT: Last price {last_price} is below the lower band {lower_band}"
                        print(alert_message)
                        orders_tree_widget.insert("", "end", values=("BUY", last_price))
                        parent_order_id, _ = place_buy_order_with_trailing_stop(client, TICKER_SYMBOL, account_hash)
                        add_active_order("Buy", TICKER_SYMBOL, last_price, "Active", parent_order_id)
                        last_alert_type = "buy"
                        first_order_placed = True  # Mark that the first buy order has been placed
                else:
                    # After the first buy, alternate between sell and buy orders
                    if last_price > upper_band and last_alert_type != "sell":
                        alert_message = f"SELL ALERT: Last price {last_price} is above the upper band {upper_band}"
                        print(alert_message)
                        orders_tree_widget.insert("", "end", values=("SELL", last_price))
                        parent_order_id, _ = place_market_sell_order(client, TICKER_SYMBOL, account_hash)
                        add_active_order("Sell", TICKER_SYMBOL, last_price, "Active", parent_order_id)
                        last_alert_type = "sell"
                    elif last_price < lower_band and last_alert_type != "buy":
                        alert_message = f"BUY ALERT: Last price {last_price} is below the lower band {lower_band}"
                        print(alert_message)
                        parent_order_id, _ = place_buy_order_with_trailing_stop(client, TICKER_SYMBOL, account_hash)
                        add_active_order("Buy", TICKER_SYMBOL, last_price, "Active", parent_order_id)
                        last_alert_type = "buy"

        time.sleep(1)  # Monitor every second

# Function to handle trailing stop event
def handle_trailing_stop_event(order_id):
    """Handle a trailing stop event by updating the order status."""
    update_order_status(order_id, "Trailing Stop Hit")

# You should run poll_active_orders in a separate thread to keep the orders updated continuously
