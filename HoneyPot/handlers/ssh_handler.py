# handlers/ssh_handler.py
import socket, threading, time
from handlers.base import BaseHandler
from deception import PseudoFS, run_command

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
            "":[""], #anonymous login
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


    def check_credentials(self, username , password):
        """Check if credentials are in our weak list"""
        if username in self.weak_credentials:
            if password in self.weak_credentials[username]:
                return True


    # you can accept also every attempt of login by just return this True
        return False

    def handle_client(self, conn, addr):
        ip, port = addr[0], addr[1]
        session_id = f"{ip}_{int(time.time())}"

        # send banner
        try:
            conn.sendall((self.banner + "\r\n").encode())
        except Exception:
            conn.close()
            return

        #Read client banner 
        try:
            conn.settimout(5.0)
            client_banner = conn.recv(4096).decode(errors='ignore').stripe()
        except Exception:
            client_banner=""

        self.emit("connection", {
            "proto": "ssh",
            "src_ip": ip,
            "src_port": port,
            "banner":self.banner,
            "client_banner":client_banner,
            "session_id": session_id
        })
        # auth attempts (allow only 3 like real SSH )
        max_attemps = 3
        authenticad = False
        username = ""

        for attempt in range(max_attemps):
            try:
                #Prompt for usename 
                conn.sendall(b"login: ")
                username = conn.recv(1024).decode(errors='ignore').stripe()

                # prompt for password (hide input)
                conn.sendall(b"Password: ")
                password = conn.recv(1024).decode(errors='ignore').stripe()


                #log auth attempt
                self.emit("auth_attempt", {
                    "proto": "ssh",
                    "src_ip": ip,
                    "src_port": port,
                    "user": username,
                    "pass": password,
                    "attempt": attempt + 1,
                    "session_id": session_id
                })
                
                #check credentials
                if self.check_credentials(usernamem , password):
                    authenticad = True
                    conn.sendall(b"\r\nWelcome to Ubuntu 20.04.3 LTS (GNU/Linux 5.4.0-42-generic x86_64)\r\n\r\n")
                    conn.sendall(f"Last login: {time.strftime('%a %b %d %H:%M:%S %Y')} from 192.168.1.1\r\n".encode())
                    break
                else:
                    conn.sendall(b"\r\nPermission denied, please try again.\r\n")
            except Exception as e:
                if self.verbose:
                    print(f"[SSH] Auth error from: {ip}: {e}")
                break
        if not authenticad:
            try:
                conn.sendall(b"\r\nToo many authentication failures\r\n")
                conn.close()
            except:
                pass
            return
        
        #start intective shell session
        self.run_shell_session(conn, ip , port , username , session_id)

    def run_shell_session(self, conn, ip, port, username, session_id):
        """"Run an interactive shell and log all commands"""
        fs = PseudoFS()

        try:
            #show shell prompt
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
                    char = data.decode(errors = 'ignore')

                    #handle Enter/Return - execute command
                    if char in ('\r', '\n'):
                        if command_buffer.strip():
                            cmd = command_buffer.strip()
                        
                            #LOG THE COMMAND HERE 
                            self.emit("command", {
                                "proto": "ssh",
                                "src_ip": ip,
                                "src_port": port,
                                "user": username,
                                "command": cmd,
                                "session_id": session_id
                            })

                            if self.verbose:
                                print(f"[SSH CMD] {ip} ({username}): {cmd}")    

                            #check for exit
                            if cmd.lower() in ("exit", "quit", "logout"):
                                conn.sendall(b"\r\nlogout\r\n")
                                break  


                                # EXecute command and send output
                            output = run_command(cmd , fs, shell_name ="bash")
                            if output:
                                conn.sendall(b"\r\n" + output.encode()+ b"\r\n")
                            else:
                                conn.sendall(b"\r\n")
                        else:
                            conn.sendall(b"\r\n")
                        
                        command_buffer =""
                        conn.sendall(prompt.encode())

                    #handle backspace
                    elif char in ('\x7f', '\x08'):
                        if command_buffer:
                            command_buffer = command_buffer[:-1]
                            conn.sendall(b'\x08 \x08') #ERASE CHARACTER

                    # handle ctrl+C
                    elif char == '\x03':
                        command_buffer = ""
                        conn.sendall(b"^C\r\n"+ prompt.encode())

                    # Handle Ctrl+D (EOF)
                    elif char == '\x04':
                        break

                    # Handle Tab (just echo it, or implement autocomplete)
                    elif char == '\t':
                        conn.sendall(b'\t')
                    

                    #regular character 
                    elif ord(char) >= 32 or char == '\t':
                        command_buffer += char
                        conn.sendall(data) #echo back


                except socket.timeout:
                    #session timeout
                    break
                except Exception as e:
                    if self.verbose:
                        print(f"[SSH] Session error from {ip}: {e}")
                    break

        except Exception as e: 
            print(f"[SSH] Shell error from {ip}: {e}")

        
        finally:
            #log session end 
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












        
