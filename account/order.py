# Here's the updated `order.py` file with the latest implementation of `place_buy_order_with_trailing_stop`
import json
import time
import os
from rich.console import Console
from dotenv import load_dotenv
import schwabdev
from config import TICKER_SYMBOL, QUANTITY, STOP_PRICE_OFFSET, STOP_PRICE_LINK_TYPE, STOP_PRICE_LINK_BASIS

# Load environment variables from .env
load_dotenv()
APP_KEY = os.getenv("APP_KEY")
APP_SECRET = os.getenv("APP_SECRET")
REDIRECT_URL = os.getenv("REDIRECT_URL")
TOKENS_FILE = os.getenv("tokens_file")

# Initialize Schwab client (it handles token refresh automatically)
client = schwabdev.Client(APP_KEY, APP_SECRET, REDIRECT_URL, TOKENS_FILE)

# Initialize console for rich output
console = Console()

# Global variables to track order IDs
parent_order_id = None
child_order_id = None

# Function to get account hash
# Function to get account hash
def get_account_hash(client):
    response = client.account_linked()
    if response.ok:
        account_data = response.json()
        if account_data:
            return account_data[0]['hashValue']
    console.print("[bold red]Failed to retrieve account hash.[/bold red]")
    return None


# Function to place a two-legged buy order with a trailing stop
def place_buy_order_with_trailing_stop(client, ticker):
    global account_hash  # Ensure account_hash is accessible
    
    # Call get_account_hash to initialize account_hash
    account_hash = get_account_hash(client)
    
    # Ensure account hash is available before placing an order
    if not account_hash:
        console.print("[bold red]Account hash is not available. Cannot place the order.[/bold red]")
        return None, None

    # Order payload construction (using relevant config values)
    order_payload = {
        "accountId": account_hash,  # Ensure the account ID is correctly passed
        "session": "NORMAL",
        "duration": "DAY",
        "orderType": "MARKET",
        "orderStrategyType": "TRIGGER",
        "editable": True,
        "orderLegCollection": [{
            "orderLegType": "EQUITY",
            "instruction": "BUY",
            "quantity": QUANTITY,
            "instrument": {"symbol": ticker, "assetType": "EQUITY"}
        }],
        "childOrderStrategies": [{
            "session": "NORMAL",
            "duration": "DAY",
            "orderType": "TRAILING_STOP",
            "orderStrategyType": "SINGLE",
            "stopPriceLinkType": STOP_PRICE_LINK_TYPE,
            "stopPriceOffset": STOP_PRICE_OFFSET,
            "stopPriceLinkBasis": STOP_PRICE_LINK_BASIS,
            "editable": True,
            "orderLegCollection": [{
                "orderLegType": "EQUITY",
                "instruction": "SELL",
                "quantity": QUANTITY,
                "instrument": {"symbol": ticker, "assetType": "EQUITY"}
            }]
        }]
    }

    # Place the order and handle the response
    try:
        response = client.order_place(order_payload)  # Pass only the order_payload directly
        api_response = handle_api_response(response)

        log_order_payload_to_file(order_payload, "Buy", ticker, api_response)

        if response.status_code == 201:
            location_header = response.headers.get("Location")
            if location_header:
                parent_order_id = int(location_header.split('/')[-1])
                child_order_id = parent_order_id + 1
                console.print(f"[bold green]Placed buy order for {ticker} with trailing stop. Parent Order ID: {parent_order_id}, Child Order ID: {child_order_id}[/bold green]")
                return parent_order_id, order_payload
            else:
                console.print(f"[bold red]Order placed, but no order ID found in the Location header.[/bold red]")
                return None, order_payload
        else:
            console.print(f"[bold red]Failed to place buy order for {ticker}. Status code: {response.status_code}[/bold red]")
            return None, order_payload

    except Exception as e:
        console.print(f"[bold red]Exception occurred while placing order: {str(e)}[/bold red]")
        return None, None


def handle_api_response(response):
    try:
        return response.json()
    except ValueError:  # If response is not valid JSON
        console.print(f"[bold red]Invalid JSON response[/bold red]")
        return {"error": "Invalid JSON response", "raw_response": response.text}


import os
import json
from datetime import datetime

def log_order_payload_to_file(order_payload, action_type, ticker, api_response=None):
    current_date = datetime.now().strftime("%Y-%m-%d")
    folder_name = f"Logs/OrderPayloads/{current_date}"
    os.makedirs(folder_name, exist_ok=True)
    
    file_name = f"{ticker}_OrderPayloads_{current_date}.txt"
    file_path = os.path.join(folder_name, file_name)
    
    try:
        with open(file_path, mode='a') as file:
            file.write(f"{action_type} Order for {ticker}:\n")
            file.write(json.dumps(order_payload, indent=4))
            file.write("\n\n")
            
            if api_response:
                file.write("API Response:\n")
                if isinstance(api_response, dict):
                    file.write(json.dumps(api_response, indent=4))
                else:
                    file.write(str(api_response))
                file.write("\n\n")
                
    except Exception as e:
        console.print(f"[bold red]Error writing order payload to file: {e}[/bold red]")


# Function to cancel the trailing stop order
def cancel_trailing_stop_order(account_hash, order_id):
    response = client.order_cancel(account_hash, order_id)
    if response.status_code == 200:
        console.print("[bold green]Trailing stop canceled successfully.[/bold green]")
        return True
    else:
        console.print(f"[bold red]Failed to cancel trailing stop: {response.text}[/bold red]")
        return False

# Function to place a market sell order
def place_market_sell_order(account_hash):
    sell_order_payload = {
        "session": "NORMAL",
        "duration": "DAY",
        "orderType": "MARKET",
        "orderStrategyType": "SINGLE",
        "orderLegCollection": [{
            "orderLegType": "EQUITY",
            "instruction": "SELL",
            "quantity": QUANTITY,
            "instrument": {"symbol": TICKER_SYMBOL, "assetType": "EQUITY"}
        }]
    }

    response = client.order_place(account_hash, sell_order_payload)
    if response.status_code == 201:
        console.print("[bold green]Market sell order placed successfully.[/bold green]")
        location_header = response.headers.get("Location")
        if location_header:
            sell_order_id = location_header.split('/')[-1]
            return sell_order_id
    else:
        console.print(f"[bold red]Failed to place sell order: {response.text}[/bold red]")
        return None

# Function to cancel trailing stop and replace it with a market sell order
def cancel_and_replace_with_market_sell(account_hash, order_id):
    if cancel_trailing_stop_order(account_hash, order_id):
        # Wait briefly before placing a new market sell order
        time.sleep(2)
        place_market_sell_order(account_hash)

"""
if __name__ == "__main__":
    # Retrieve the account hash
    account_hash = get_account_hash()
    if not account_hash:
        console.print("[bold red]Could not retrieve account hash. Exiting...[/bold red]")
        exit()

    # Example of placing a buy order with a trailing stop
    parent_order_id, child_order_id = place_buy_order_with_trailing_stop(client, TICKER_SYMBOL)
    
    # Simulate a wait time before canceling the trailing stop order and replacing with a market sell
    if child_order_id:
        time.sleep(10)  # Replace with logic to wait for a specific condition
        #cancel_and_replace_with_market_sell(account_hash, child_order_id)
"""