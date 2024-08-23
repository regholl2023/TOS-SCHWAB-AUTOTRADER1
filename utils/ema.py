import numpy as np
from stream import get_last_x_minutes_data
import config

def calculate_ema(prices):
    """Calculate Exponential Moving Average (EMA) with a period equal to the length of the deque."""
    period = len(prices)  # The period is dynamically set to the length of the deque

    if not prices or period == 0:
        return None

    prices = np.array(prices)
    weights = np.exp(np.linspace(-1., 0., period))
    weights /= weights.sum()

    # Convolve the prices with the weights
    ema = np.convolve(prices, weights, mode='valid')
    return ema[-1] if len(ema) > 0 else None

def calculate_std_deviation(prices):
    """Calculate the standard deviation of the prices."""
    if not prices:
        return None

    return np.std(prices)

def calculate_upper_lower_bands(ema, std_dev):
    """Calculate the upper and lower bands based on the EMA and standard deviation."""
    if ema is None or std_dev is None:
        return None, None
    
    upper_band = ema + (config.STD_DEVIATION_MULTIPLIER * std_dev)
    lower_band = ema - (config.STD_DEVIATION_MULTIPLIER * std_dev)
    return upper_band, lower_band

def calculate_ema_and_bands():
    """Fetch the latest data and calculate EMA and upper/lower bands."""
    # Fetch the last X minutes of data
    data = get_last_x_minutes_data()

    # Extract the 'Last Price' field
    prices = [entry['Last Price'] for entry in data if entry.get('Last Price') is not None]

    # Calculate EMA with dynamic period based on deque length
    ema = calculate_ema(prices)

    # Calculate standard deviation
    std_dev = calculate_std_deviation(prices)

    # Calculate upper and lower bands
    upper_band, lower_band = calculate_upper_lower_bands(ema, std_dev)

    return ema, upper_band, lower_band
