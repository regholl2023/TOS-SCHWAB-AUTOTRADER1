import time
from account.order import place_buy_order_with_trailing_stop, cancel_and_replace_with_market_sell
from utils.gui import monitor_prices

# Global variable to keep track of the last alert
last_signal = None  # It can be "BUY" or "SELL"

def stream_alert_handler(alert):
    """
    Handles incoming alerts and determines if an order should be placed.
    """
    global last_signal

    if alert == "BUY":
        # Only act on a BUY alert if the last signal was a SELL or None
        if last_signal != "BUY":
            place_buy_order_with_trailing_stop()
            last_signal = "BUY"
            print("Placed a buy order.")

    elif alert == "SELL":
        # Only act on a SELL alert if the last signal was a BUY
        if last_signal == "BUY":
            cancel_and_replace_with_market_sell()
            last_signal = "SELL"
            print("Placed a sell order.")

def monitor_alerts():
    """
    Continuously monitors alerts coming in from the stream.
    """
    while True:
        # Example alert fetching function - replace with actual stream logic
        alert = get_next_alert()  # Implement this function to fetch alerts

        if alert:
            stream_alert_handler(alert)

        # Sleep for a short while before checking again
        time.sleep(1)

def get_next_alert():
    """
    This is a placeholder for fetching the next alert from the stream.
    Replace this with actual logic to get alerts.
    """
    # Simulating alerts coming in - Replace this with your actual alert stream logic
    example_alerts = ["BUY", "SELL", "BUY", "SELL", "BUY"]
    for alert in example_alerts:
        yield alert

def main():
    """
    Entry point for the order executor.
    """
    print("Starting the order executor...")
    monitor_alerts()

if __name__ == "__main__":
    main()
