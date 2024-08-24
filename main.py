from utils.gui import setup_gui
from stream import start_stream
from account.order import get_account_hash
import schwabdev
from dotenv import load_dotenv
import os

def main():
    # Load environment variables from .env
    load_dotenv()
    APP_KEY = os.getenv("APP_KEY")
    APP_SECRET = os.getenv("APP_SECRET")
    REDIRECT_URL = os.getenv("REDIRECT_URL")
    TOKENS_FILE = os.getenv("TOKENS_FILE")

    # Initialize the Schwab client (it handles token refresh automatically)
    client = schwabdev.Client(APP_KEY, APP_SECRET, REDIRECT_URL, TOKENS_FILE)

    # Retrieve the account hash
    account_hash = get_account_hash(client)
    if not account_hash:
        print("Failed to retrieve account hash. Exiting.")
        return

    # Start the GUI and pass client and account_hash
    setup_gui(start_stream, client, account_hash)

if __name__ == "__main__":
    main()
