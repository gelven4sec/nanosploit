import socket
import ssl
import threading
import time


def main():
    # Create socket with ssl
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.setsockopt(socket.SOL_SOCKET, socket.SO_KEEPALIVE, 1)
    context = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
    context.check_hostname = False
    context.verify_mode = ssl.CERT_NONE
    ss = context.wrap_socket(s)

    # Connect to C2 server
    ss.connect(("127.0.0.1", 8000))

    while True:
        buffer = ss.recv()
        if buffer:
            match buffer:
                case b"ping":
                    ss.send(b"pong")
                case _:
                    print(f"Unknown command received: '{buffer.decode()}'")
                    ss.send(buffer)
        else:
            print("Lost server connection, exiting...")
            break

    # Exit program
    exit(1)


if __name__ == "__main__":
    main()
