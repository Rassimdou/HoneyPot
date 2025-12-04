import socket, threading, time
from handlers.base import BaseHandler
from deception import PseudoFS, run_command
from geoip import GeoIP

class SSHHandler(BaseHandler):
    def __init__(self, host, port, cfg, storage, verbose=True):
        super().__init__(host, port, cfg, storage, verbose)
        self.banner = cfg.get("banner", "SSH-2.0-OpenSSH_7.6p1")
        self.session_timeout = cfg.get("session_timeout", 60)

        self.weak_credentials = {
            "root": ["root", "admin", "password", "123456", "toor", ""],
            "admin": ["admin", "password", "123456", "admin123", ""],
            "user": ["user", "password", "123456", ""],
            "ubuntu": ["ubuntu", "password", ""],
            "pi": ["raspberry", "pi", ""],
            "": [""],
        }

    def start_listener(self):
        s = socket.socket()
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        s.bind((self.host, self.port))
        s.listen(100)
        if self.verbose:
            print(f"[SSH] Listening on {self.host}:{self.port}")

        while True:
            client, addr = s.accept()
            t = threading.Thread(target=self.handle_client, args=(client, addr), daemon=True)
            t.start()

    def check_credentials(self, username, password):
        if username in self.weak_credentials:
            if password in self.weak_credentials[username]:
                return True
        return False

    def handle_client(self, conn, addr):
        ip, port = addr[0], addr[1]
        session_id = f"{ip}_{int(time.time())}"

        # GeoIP lookup
        geo = GeoIP()
        geo_data = geo.lookup(ip)

        # send banner
        try:
            conn.sendall((self.banner + "\r\n").encode())
        except Exception:
            conn.close()
            return

        # Read client banner
        try:
            conn.settimeout(5.0)
            client_banner = conn.recv(4096).decode(errors='ignore').strip()
        except Exception:
            client_banner = ""

        # Log connection event
        self.emit("connection", {
            "proto": "ssh",
            "src_ip": ip,
            "src_port": port,
            "banner": self.banner,
            "client_banner": client_banner,
            "geo": geo_data,                  # ← GEOIP DATA ADDED
            "session_id": session_id
        })

        max_attempts = 3
        authenticated = False
        username = ""

        for attempt in range(max_attempts):
            try:
                conn.sendall(b"login: ")
                # FIX 1: Add a timeout to prevent indefinite blocking during login
                conn.settimeout(30.0) 
                username = conn.recv(1024).decode(errors='ignore').strip()

                conn.sendall(b"Password: ")
                # FIX 1: Add a timeout to prevent indefinite blocking during password entry
                conn.settimeout(30.0) 
                password = conn.recv(1024).decode(errors='ignore').strip()

                self.emit("auth_attempt", {
                    "proto": "ssh",
                    "src_ip": ip,
                    "src_port": port,
                    "user": username,
                    "pass": password,
                    "attempt": attempt + 1,
                    "session_id": session_id
                })

                if self.check_credentials(username, password):
                    authenticated = True
                    conn.sendall(b"\r\nWelcome to Ubuntu 20.04.3 LTS (GNU/Linux 5.4.0-42-generic x86_64)\r\n\r\n")
                    conn.sendall(f"Last login: {time.strftime('%a %b %d %H:%M:%S %Y')} from 192.168.1.1\r\n".encode())
                    break
                else:
                    conn.sendall(b"\r\nPermission denied, please try again.\r\n")

            except Exception as e:
                if self.verbose:
                    print(f"[SSH] Auth error from {ip}: {e}")
                break

        if not authenticated:
            try:
                conn.sendall(b"\r\nToo many authentication failures\r\n")
                conn.close()
            except:
                pass
            return

        # Start shell
        self.run_shell_session(conn, ip, port, username, session_id)

    def run_shell_session(self, conn, ip, port, username, session_id):
        fs = PseudoFS()

        try:
            prompt = f"{username}@honeypot:~$ "
            conn.sendall(prompt.encode())

            start = time.time()
            command_buffer = ""

            while time.time() - start < self.session_timeout:
                conn.settimeout(30)

                try:
                    data = conn.recv(1)
                    if not data:
                        break

                    char = data.decode(errors='ignore')

                    if char in ('\r', '\n'):
                        if command_buffer.strip():
                            cmd = command_buffer.strip()

                            self.emit("command", {
                                "proto": "ssh",
                                "src_ip": ip,
                                "src_port": port,
                                "user": username,
                                "command": cmd,
                                "session_id": session_id
                            })

                            if cmd.lower() in ("exit", "quit", "logout"):
                                conn.sendall(b"\r\nlogout\r\n")
                                break

                            output_result = run_command(cmd, fs, shell_name="bash")
                            
                            # FIX 2: Check for tuple return and extract the string output.
                            # The 'tuple' object has no attribute 'encode' error is fixed here.
                            if isinstance(output_result, tuple):
                                # Assuming the output string is the first element.
                                output = output_result[0]
                            else:
                                output = output_result
                            
                            if output:
                                conn.sendall(b"\r\n" + output.encode() + b"\r\n")
                            else:
                                conn.sendall(b"\r\n")
                        else:
                            conn.sendall(b"\r\n")

                        command_buffer = ""
                        conn.sendall(prompt.encode())
                        continue

                    elif char in ('\x7f', '\x08'):
                        if command_buffer:
                            command_buffer = command_buffer[:-1]
                            conn.sendall(b'\x08 \x08')
                        continue

                    elif char == '\x03':
                        command_buffer = ""
                        conn.sendall(b"^C\r\n" + prompt.encode())
                        continue

                    elif char == '\x04':
                        break

                    elif ord(char) >= 32:
                        command_buffer += char
                        conn.sendall(data)
                        continue

                except socket.timeout:
                    break

            # The shell error (if it happens) is caught here.
        except Exception as e:
            print(f"[SSH] Shell error from {ip}: {e}")

        finally:
            self.emit("session_end", {
                "proto": "ssh",
                "src_ip": ip,
                "src_port": port,
                "user": username,
                "session_id": session_id,
                "duration": time.time() - start
            })

            try:
                conn.close()
            except:
                pass
