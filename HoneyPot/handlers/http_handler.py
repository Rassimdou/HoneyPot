# handlers/http_handler.py
import socket, threading
from handlers.base import BaseHandler

class HTTPHandler(BaseHandler):
    def __init__(self, host, port, cfg, storage, verbose=True):
        super().__init__(host, port, cfg, storage, verbose)
        self.banner = cfg.get("banner", "HTTP/1.1 200 OK")

    def start_listener(self):
        s = socket.socket()
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        s.bind((self.host, self.port))
        s.listen(100)
        if self.verbose:
            print(f"[HTTP] Listening on {self.host}:{self.port}")
        while True:
            client, addr = s.accept()
            t = threading.Thread(target=self.handle_client, args=(client, addr), daemon=True)
            t.start()

    def handle_client(self, conn, addr):
        ip, port = addr[0], addr[1]
        try:
            conn.settimeout(2.0)
            data = conn.recv(8192)
            req_line = data.decode(errors='ignore').splitlines()[0] if data else ""
        except Exception:
            req_line = ""
        self.emit("connection", {"proto":"http", "src_ip":ip, "src_port":port, "request":req_line})
        body = "<html><body><h1>Apache/2.4.18 (Ubuntu)</h1></body></html>"
        resp = "HTTP/1.1 200 OK\r\nServer: Apache/2.4.18 (Ubuntu)\r\nContent-Length: %d\r\nContent-Type: text/html\r\n\r\n%s" % (len(body), body)
        try:
            conn.sendall(resp.encode())
        except Exception:
            pass
        try:
            conn.close()
        except:
            pass