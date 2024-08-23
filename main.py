from utils.gui import setup_gui
from stream import start_stream

def main():
    # Start the GUI and pass the stream function to it
    setup_gui(start_stream)

if __name__ == '__main__':
    main()
