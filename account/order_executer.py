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

def log_order_to_file(order_type, price):
    """Log orders to a file with the order type and price."""
    with open("orders.log", "a") as log_file:
        log_file.write(f"{order_type} order placed at price {price}\n")

def run_order_executor(orders_tree_widget):
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
                        place_buy_order_with_trailing_stop(client, TICKER_SYMBOL)  # Pass account_hash here
                        log_order_to_file("BUY", last_price)
                        last_alert_type = "buy"
                        first_order_placed = True  # Mark that the first buy order has been placed
                else:
                    # After the first buy, alternate between sell and buy orders
                    if last_price > upper_band and last_alert_type != "sell":
                        alert_message = f"SELL ALERT: Last price {last_price} is above the upper band {upper_band}"
                        print(alert_message)
                        orders_tree_widget.insert("", "end", values=("SELL", last_price))
                        place_market_sell_order(client, TICKER_SYMBOL, account_hash)  # Pass account_hash here
                        log_order_to_file("SELL", last_price)
                        last_alert_type = "sell"
                    elif last_price < lower_band and last_alert_type != "buy":
                        alert_message = f"BUY ALERT: Last price {last_price} is below the lower band {lower_band}"
                        print(alert_message)
                        orders_tree_widget.insert("", "end", values=("BUY", last_price))
                        place_buy_order_with_trailing_stop(client, TICKER_SYMBOL, account_hash)  # Pass account_hash here
                        log_order_to_file("BUY", last_price)
                        last_alert_type = "buy"

        time.sleep(1)  # Monitor every second
