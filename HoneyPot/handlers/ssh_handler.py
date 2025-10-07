# handlers/ssh_handler.py
import socket, threading, time
from handlers.base import BaseHandler
from deception import PseudoFS, run_command

class SSHHandler(BaseHandler):
    def __init__(self, host, port, cfg, storage, verbose=True):
        super().__init__(host, port, cfg, storage, verbose)
        self.banner = cfg.get("banner", "SSH-2.0-OpenSSH_7.6p1")
        self.session_timeout = cfg.get("session_timeout", 60)

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

    def handle_client(self, conn, addr):
        ip, port = addr[0], addr[1]
        # send banner
        try:
            conn.sendall((self.banner + "\r\n").encode())
        except Exception:
            pass
        # read initial bytes
        try:
            conn.settimeout(2.0)
            first = conn.recv(4096).decode(errors='ignore').strip()
        except Exception:
            first = ""
        self.emit("connection", {"proto":"ssh", "src_ip":ip, "src_port":port, "banner":self.banner, "first":first})
        # simulated login
        try:
            conn.sendall(b"login: ")
            user = conn.recv(1024).decode(errors='ignore').strip()
            conn.sendall(b"Password: ")
            pwd = conn.recv(1024).decode(errors='ignore').strip()
        except Exception:
            user, pwd = "", ""
        self.emit("auth_attempt", {"proto":"ssh", "src_ip":ip, "src_port":port, "user":user, "pass":pwd})
        # fake shell
        fs = PseudoFS()
        try:
            conn.sendall(b"Welcome. Type 'exit' to quit.\r\n$ ")
            start = time.time()
            while time.time() - start < self.session_timeout:
                conn.settimeout(self.session_timeout)
                data = conn.recv(4096)
                if not data:
                    break
                cmd = data.decode(errors='ignore').strip()
                self.emit("command", {"proto":"ssh", "src_ip":ip, "src_port":port, "cmd":cmd})
                if cmd in ("exit","quit"):
                    break
                out = run_command(cmd, fs, shell_name="bash")
                if out and not out.endswith("\n"):
                    out += "\r\n"
                try:
                    conn.sendall(out.encode())
                    conn.sendall(b"$ ")
                except Exception:
                    break
        except Exception:
            pass
        try:
            conn.close()
        except:
            pass
