import argparse

from nanosploit.server import main as server
from nanosploit.client import main as client

if __name__ == '__main__':
    # Create the argument parser
    parser = argparse.ArgumentParser(
        prog="nanosploit",
        description="Minimalist C2 server for educational purpose."
    )
    # Add the server and client choices with server as default
    parser.add_argument(
        "mode",
        choices=["server", "client"],
        help="Choose either 'server' or 'client' mode",
        nargs="?",
        default="server"
    )

    # Execute server or client script
    args = parser.parse_args()
    if args.mode == "server":
        server()
    elif args.mode == "client":
        client()
