import os
import json
import logging
from dotenv import load_dotenv
from schwabdev import Client
import config
from collections import deque
from threading import Lock

# Create a deque to store the last X minutes of data
data_deque = deque(maxlen=config.MAX_LENGTH)

# Create a lock for thread-safe access to the deque
deque_lock = Lock()

# Initialize variables to store the latest data
latest_data = {field_name: None for field_name in config.FIELD_MAPPING.values()}

def my_custom_handler(message):
    """Custom handler to update live data and the deque."""
    logging.info(f"Received data: {message}")

    try:
        # Ensure message is parsed as JSON
        data = json.loads(message)
        
        # Check if the data contains market data and handle it
        if 'data' in data:
            content = data['data'][0].get('content', [])[0]

            # Capture the symbol (usually stored under the "key" field)
            symbol = content.get("key")
            if symbol:
                latest_data["Symbol"] = symbol

            # Update the latest data based on the received fields
            for field_key, field_value in content.items():
                field_name = config.FIELD_MAPPING.get(field_key)
                if field_name and field_key != "key":  # Avoid overriding the symbol
                    latest_data[field_name] = field_value

            # Append the latest data to the deque (with thread safety)
            with deque_lock:
                data_deque.append(latest_data.copy())

    except json.JSONDecodeError:
        logging.error("Failed to decode JSON message.")
    except Exception as e:
        logging.error(f"Error processing data: {e}")

def start_stream():
    """Function to start the Schwab API stream."""
    # Configure logging
    logging.basicConfig(filename='stream_data.log', level=logging.INFO, format='%(asctime)s - %(message)s')

    # Load environment variables from .env file
    load_dotenv()

    # Get the environment variables
    app_key = os.getenv('APP_KEY')
    app_secret = os.getenv('APP_SECRET')
    callback_url = os.getenv('REDIRECT_URL')
    tokens_file = os.getenv('tokens_file')

    # Create the client with the environment variables
    client = Client(app_key, app_secret, callback_url, tokens_file=tokens_file)

    # Define the streamer
    streamer = client.stream

    try:
        # Start streamer with custom handler to update deque
        streamer.start(my_custom_handler)

        # Stream all fields for the specified ticker symbol
        streamer.send(streamer.level_one_equities(config.TICKER_SYMBOL, config.FIELDS))

    except KeyboardInterrupt:
        # Graceful shutdown on Ctrl+C
        logging.info("Stream interrupted by user.")
        streamer.stop()

def get_last_x_minutes_data():
    """Function to access the last X minutes of data in a thread-safe manner."""
    with deque_lock:
        return list(data_deque)
