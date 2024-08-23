import sys
import os
import requests  # For handling exceptions and retrying failed requests
from datetime import datetime
import json
import time
from rich.console import Console
from dotenv import load_dotenv
import schwabdev
from authenticate import reauthenticate_client, reauth_and_execute

# Add the parent directory to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from config import TICKER_SYMBOL, QUANTITY, STOP_PRICE_OFFSET, STOP_PRICE_LINK_TYPE, STOP_PRICE_LINK_BASIS

# Initialize console for rich output
console = Console()

# Load environment variables and initialize Schwab client
load_dotenv()
APP_KEY = os.getenv("APP_KEY")
APP_SECRET = os.getenv("APP_SECRET")
CALLBACK_URL = os.getenv("REDIRECT_URL")
TOKENS_FILE = os.getenv("tokens_file")

client = schwabdev.Client(APP_KEY, APP_SECRET, CALLBACK_URL, token_file=TOKENS_FILE)

# Global variables to track order IDs
account_hash = None
parent_order_id = None
child_order_id = None  # Track the second leg order ID (trailing stop)

@reauth_and_execute
def get_account_hash():
    global account_hash
    console.print("[bold blue]Fetching linked accounts...[/bold blue]")
    response = client.account_linked()
    
    if response.ok:
        account_data = response.json()
        if account_data:
            account_hash = account_data[0]['hashValue']
            console.print(f"[bold green]Fetched account hash: {account_hash}[/bold green]")
        else:
            console.print(f"[bold red]No linked accounts found.[/bold red]")
    else:
        console.print(f"[bold red]Failed to fetch account hash. Status code: {response.status_code}, Response: {response.text}[/bold red]")

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

# Function to handle API responses
def handle_api_response(response):
    try:
        return response.json()
    except ValueError:  # If response is not valid JSON
        console.print(f"[bold red]Invalid JSON response[/bold red]")
        return {"error": "Invalid JSON response", "raw_response": response.text}

@reauth_and_execute
def check_order_filled(client, order_id):
    get_account_hash()
    
    # Ensure account hash and order ID are available
    if not account_hash or not order_id:
        console.print("[bold red]Account hash or order ID is not available. Cannot check order status.[/bold red]")
        return False

    console.print(f"[bold blue]Checking status of order ID: {order_id}...[/bold blue]")
    response = client.order_details(account_hash, order_id)
    api_response = handle_api_response(response)

    if response.ok:
        order_status = api_response.get('status')
        console.print(f"[bold green]Order status for ID {order_id}: {order_status}[/bold green]")
        
        # Check if the trailing stop order is filled
        if order_status == 'FILLED':
            console.print(f"[bold yellow]Trailing stop order {order_id} has been filled.[/bold yellow]")
            
            # Reset the state to prevent further buys until a new signal
            reset_trading_state()
            return True
    else:
        console.print(f"[bold red]Failed to check order status for ID: {order_id}. Status code: {response.status_code}, Response: {response.text}[/bold red]")
    
    return False

def reset_trading_state():
    global parent_order_id, child_order_id
    
    # Reset all variables related to the current trade cycle
    parent_order_id = None
    child_order_id = None
    
    console.print(f"[bold blue]Trading state has been reset. Awaiting next buy signal.[/bold blue]")

@reauth_and_execute
def place_buy_order_with_trailing_stop(client, ticker):
    global parent_order_id, child_order_id  # Track both order IDs
    get_account_hash()

    # Ensure account hash is available before placing an order
    if not account_hash:
        console.print("[bold red]Account hash is not available. Cannot place the order.[/bold red]")
        return None, None

    order_payload = {
        "session": "NORMAL",
        "duration": "DAY",
        "orderType": "MARKET",
        "orderStrategyType": "TRIGGER",  # Trigger for subsequent orders
        "editable": True,  # Make the order editable
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
            "orderStrategyType": "SINGLE",  # Single trailing stop order
            "stopPriceLinkType": STOP_PRICE_LINK_TYPE,
            "stopPriceOffset": STOP_PRICE_OFFSET,
            "stopPriceLinkBasis": STOP_PRICE_LINK_BASIS,
            "editable": True,  # Ensure the child order is also editable
            "orderLegCollection": [{
                "orderLegType": "EQUITY",
                "instruction": "SELL",
                "quantity": QUANTITY,
                "instrument": {"symbol": ticker, "assetType": "EQUITY"}
            }]
        }]
    }

    console.print("[bold blue]Placing buy order with trailing stop...[/bold blue]")
    response = client.order_place(account_hash, order_payload)
    api_response = handle_api_response(response)
    
    log_order_payload_to_file(order_payload, "Buy", ticker, api_response)

    if response.status_code == 201:
        location_header = response.headers.get("Location")
        if location_header:
            parent_order_id = int(location_header.split('/')[-1])  # Extract the parent order ID from the Location URL
            child_order_id = parent_order_id + 1  # Calculate the child order ID as parent ID + 1
            console.print(f"[bold green]Placed buy order for {ticker} with trailing stop. Parent Order ID: {parent_order_id}, Child Order ID: {child_order_id}[/bold green]")
            return parent_order_id, order_payload  # Return both order ID and payload
        else:
            console.print(f"[bold red]Order placed, but no order ID found in the Location header.[/bold red]")
            return None, order_payload  # Return payload even if no order ID
    else:
        console.print(f"[bold red]Failed to place buy order for {ticker}. Status code: {response.status_code}[/bold red]")
        return None, order_payload  # Return payload in case of failure

@reauth_and_execute
def cancel_trailing_stop_order(client):
    global child_order_id
    get_account_hash()
    
    if not account_hash or not child_order_id:
        console.print("[bold red]Account hash or child order ID is not available. Cannot cancel the order.[/bold red]")
        return False

    retries = 3  # Number of retries for cancellation
    while retries > 0:
        console.print(f"[bold blue]Cancelling trailing stop order ID: {child_order_id}...[/bold blue]")
        response = client.order_cancel(account_hash, child_order_id)
        if response.ok:
            console.print(f"[bold green]Successfully canceled trailing stop order with ID: {child_order_id}[/bold green]")
            return True
        elif response.status_code == 401:
            reauthenticate_client()  # Reauthenticate and retry
        retries -= 1

    console.print(f"[bold red]Failed to cancel trailing stop order after retries. Status code: {response.status_code}, Response: {response.text}[/bold red]")
    return False

@reauth_and_execute
def place_market_sell_order(client, ticker):
    get_account_hash()
    # Ensure account hash is available before placing an order
    if not account_hash:
        console.print("[bold red]Account hash is not available. Cannot place the order.[/bold red]")
        return None

    sell_order_payload = {
        "session": "NORMAL",
        "duration": "DAY",
        "orderType": "MARKET",
        "orderStrategyType": "SINGLE",  # Single market order
        "editable": True,  # Ensure the replacement order is editable
        "orderLegCollection": [{
            "orderLegType": "EQUITY",
            "instruction": "SELL",
            "quantity": QUANTITY,  # Sell the same quantity as the buy order
            "instrument": {"symbol": ticker, "assetType": "EQUITY"}
        }]
    }

    console.print("[bold blue]Placing market sell order...[/bold blue]")
    response = client.order_place(account_hash, sell_order_payload)
    api_response = handle_api_response(response)
    
    log_order_payload_to_file(sell_order_payload, "Sell", ticker, api_response)

    if response.status_code == 201:
        location_header = response.headers.get("Location")
        if location_header:
            order_id = location_header.split('/')[-1]  # Extract the order ID from the Location URL
            console.print(f"[bold green]Placed market sell order for {ticker}. Order ID: {order_id}[/bold green]")
            return order_id
        else:
            console.print(f"[bold red]Sell order placed, but no order ID found in the Location header.[/bold red]")
            return None
    else:
        console.print(f"[bold red]Failed to place sell order for {ticker}. Status code: {response.status_code}[/bold red]")
        return None

# Consolidated function to cancel the trailing stop order and place a market sell order
@reauth_and_execute
def cancel_and_replace_with_market_sell(client, ticker):
    # Cancel the trailing stop order
    if cancel_trailing_stop_order(client):
        # Wait for 5 seconds 
        time.sleep(1)
        # Place a new market sell order after successful cancellation
        place_market_sell_order(client, ticker)

# Main function to place the order and replace it after a delay
def main():
    get_account_hash()
    
    # Example flow
    # Place the buy order with trailing stop
    #order_id, order_payload = place_buy_order_with_trailing_stop(client, TICKER_SYMBOL)
    
    # Wait for 5 seconds before canceling the trailing stop and placing a market sell order
    #time.sleep(5)
    
    # Cancel the trailing stop and place a new market sell order
    #cancel_and_replace_with_market_sell(client, TICKER_SYMBOL)

if __name__ == "__main__":
    main()
