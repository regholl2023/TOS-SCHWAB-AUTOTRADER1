import tkinter as tk
from tkinter.scrolledtext import ScrolledText
from threading import Thread
import time
import sys
from queue import Queue, Empty
from stream import start_stream, get_last_x_minutes_data
from utils.ema import calculate_ema_and_bands

class RedirectText:
    def __init__(self, queue):
        self.queue = queue

    def write(self, string):
        self.queue.put(string)

    def flush(self):
        pass  # This is needed to support the flush method of sys.stdout

def run_stream(output_queue):
    sys.stdout = RedirectText(output_queue)
    print("Starting stream...")
    start_stream()

def monitor_prices(output_queue):
    sys.stdout = RedirectText(output_queue)
    while True:
        ema, upper_band, lower_band = calculate_ema_and_bands()
        if ema is not None:
            print(f"EMA: {ema}, Upper Band: {upper_band}, Lower Band: {lower_band}")
            latest_data = get_last_x_minutes_data()
            if latest_data:
                last_price = latest_data[-1].get('Last Price')
                if last_price is not None:
                    if last_price > upper_band:
                        print(f"ALERT: Last price {last_price} is above the upper band {upper_band}!")
                    elif last_price < lower_band:
                        print(f"ALERT: Last price {last_price} is below the lower band {lower_band}!")
        time.sleep(5)

def update_text_widgets():
    while True:
        try:
            text = stream_queue.get_nowait()
            stream_output.insert(tk.END, text)
            stream_output.see(tk.END)
        except Empty:
            break

    while True:
        try:
            text = ema_queue.get_nowait()
            ema_output.insert(tk.END, text)
            ema_output.see(tk.END)
        except Empty:
            break

def main():
    global stream_output, ema_output, stream_queue, ema_queue

    # Create the main window
    root = tk.Tk()
    root.title("Live Data Stream & EMA Monitor")

    # Create two ScrolledText widgets for displaying the output
    stream_output = ScrolledText(root, height=20, width=80)
    stream_output.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

    ema_output = ScrolledText(root, height=20, width=80)
    ema_output.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)

    # Create queues for thread communication
    stream_queue = Queue()
    ema_queue = Queue()

    # Start the stream and monitoring in separate threads
    stream_thread = Thread(target=run_stream, args=(stream_queue,))
    stream_thread.start()

    monitor_thread = Thread(target=monitor_prices, args=(ema_queue,))
    monitor_thread.start()

    # Update the Tkinter widgets with the data from the queues
    def check_queues():
        update_text_widgets()
        root.after(100, check_queues)

    check_queues()

    # Start the tkinter main loop
    root.mainloop()

if __name__ == '__main__':
    main()
