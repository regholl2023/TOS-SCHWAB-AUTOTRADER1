# config.py

# Constants
TICKER_SYMBOL = "SQQQ"  # The ticker symbol you want to stream

# List of all fields to be requested from the LEVELONE_EQUITIES service
FIELDS = ",".join(str(i) for i in range(52))  # Generates '0,1,2,...,51' for all fields

# Field mapping based on Schwab API documentation
FIELD_MAPPING = {
    "0": "Symbol",
    "1": "Bid Price",
    "2": "Ask Price",
    "3": "Last Price",
    "4": "Bid Size",
    "5": "Ask Size",
    "6": "Ask ID",
    "7": "Bid ID",
    "8": "Total Volume",
    "9": "Last Size",
    "10": "High Price",
    "11": "Low Price",
    "12": "Close Price",
    "13": "Exchange ID",
    "14": "Marginable",
    "15": "Description",
    "16": "Last ID",
    "17": "Open Price",
    "18": "Net Change",
    "19": "52 Week High",
    "20": "52 Week Low",
    "21": "PE Ratio",
    "22": "Annual Dividend Amount",
    "23": "Dividend Yield",
    "24": "NAV",
    "25": "Exchange Name",
    "26": "Dividend Date",
    "27": "Regular Market Quote",
    "28": "Regular Market Trade",
    "29": "Regular Market Last Price",
    "30": "Regular Market Last Size",
    "31": "Regular Market Net Change",
    "32": "Security Status",
    "33": "Mark Price",
    "34": "Quote Time",
    "35": "Trade Time",
    "36": "Regular Market Trade Time",
    "37": "Bid Time",
    "38": "Ask Time",
    "39": "Ask MIC ID",
    "40": "Bid MIC ID",
    "41": "Last MIC ID",
    "42": "Net Percent Change",
    "43": "Regular Market Percent Change",
    "44": "Mark Price Net Change",
    "45": "Mark Price Percent Change",
    "46": "Hard to Borrow Quantity",
    "47": "Hard to Borrow Rate",
    "48": "Hard to Borrow Indicator",
    "49": "Shortable",
    "50": "Post-Market Net Change",
    "51": "Post-Market Percent Change"
}

# Deque configuration for storing the last X minutes of data
X_MINUTES = 8  # Example: last 8 minutes of data
MAX_LENGTH = X_MINUTES * 60  # Assuming data updates once per second

# EMA and Std Deviation Configurations
EMA_PERIOD = 12  # Period for EMA calculation
STD_DEVIATION_MULTIPLIER = 1.7  # Multiplier for standard deviation bands
