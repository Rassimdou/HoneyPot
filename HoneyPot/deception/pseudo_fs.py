import time
import random

class PseudoFS:
    def __init__(self, template=None):
        template = template or {
            "README.txt": "Welcome to HoneyPot demo.\n",
            "config.php": "<?php // example ?>\n",
        }
        self.files = dict(template)

    # ---------------------------
    # File system emulation
    # ---------------------------

    def ls(self):
        return "  ".join(self.files.keys())

    def cat(self, name):
        return self.files.get(name, f"cat: {name}: No such file or directory")

    def add_file(self, filename, data_bytes):
        self.files[filename] = f"<binary ({len(data_bytes)} bytes)>"
        return filename

    # ---------------------------
    # Fake system info
    # ---------------------------

    def fake_ps(self):
        procs = [
            "root       1  0.0  0.1  18560  1024 ?        Ss   10:00   0:00 /sbin/init",
            "root     234  0.0  0.3  35200  2400 ?        Ss   10:01   0:00 /usr/sbin/sshd -D",
            "www-data 512  0.0  0.5 120000  4000 ?        S    10:02   0:01 /usr/sbin/apache2 -k start",
            "user    1024  0.0  0.2  50000  2000 pts/0    Ss   10:03   0:00 -bash"
        ]
        return "\n".join(random.sample(procs, k=3))


# ------------------------------------
# Standalone run_command() function
# ------------------------------------

def run_command(cmd, fs, shell_name="bash"):
    cmd = (cmd or "").strip()
    time.sleep(random.uniform(0.05, 0.25))

    if cmd == "":
        return ""

    # ls
    if cmd == "ls":
        return fs.ls()

    # cat
    if cmd.startswith("cat "):
        _, name = cmd.split(" ", 1)
        return fs.cat(name)

    # ps command
    if cmd in ("ps", "ps aux"):
        return fs.fake_ps()

    # uname
    if cmd.startswith("uname"):
        return "Linux ubuntu 4.15.0-20-generic #21-Ubuntu SMP x86_64 GNU/Linux"

    # wget/curl fake download
    if cmd.startswith("wget ") or cmd.startswith("curl "):
        parts = cmd.split()
        url = parts[1] if len(parts) > 1 else "unknown"

        fname = f"download_{int(time.time())}.bin"
        dummy = b"\x00" * 128  # 128 bytes fake file

        fs.add_file(fname, dummy)

        return (
            f"Connecting to {url}\n"
            f"Saving to: '{fname}'\n"
            f"{len(dummy)} bytes saved"
        )

    # fallback
    return f"{shell_name}: {cmd.split()[0]}: command not found"
import time
import random
import shlex
from typing import Tuple, Dict, List
import os

class PseudoFS:
    def __init__(self, template=None):
        template = template or {
            "README.txt": "Welcome to HoneyPot demo.\n",
            "config.php": "<?php // Database configuration\n$db_host = 'localhost';\n$db_user = 'root';\n$db_pass = 'secret123';\n?>",
            "index.html": "<html>\n<body>\n<h1>Under Construction</h1>\n<p>Site coming soon...</p>\n</body>\n</html>",
            ".bash_history": "ls\ncat README.txt\nps aux\nwhoami\n",
            "passwords.txt": "admin:password123\nroot:toor\nuser:123456\n",
            "backup.zip": "<compressed backup file>",
        }
        self.files = dict(template)
        self.current_dir = "/home/user"
        self.user = "root"
        self.hostname = "ubuntu-server"
        
        # Add some directory structure
        self.directories = {
            "/home/user": ["README.txt", ".bash_history", "passwords.txt"],
            "/etc": ["passwd", "shadow", "hosts", "ssh/sshd_config"],
            "/var/www": ["index.html", "config.php"],
            "/tmp": ["backup.zip"],
            "/root": [".ssh/id_rsa", ".bashrc"],
        }
        
        # File contents for system files
        self.system_files = {
            "/etc/passwd": "root:x:0:0:root:/root:/bin/bash\nuser:x:1000:1000:User,,,:/home/user:/bin/bash\n",
            "/etc/shadow": "root:$6$rounds=656000$H1ecrJNj6GVK6Vj2$V2RhS...:18000:0:99999:7:::\n",
            "/etc/hosts": "127.0.0.1 localhost\n192.168.1.100 ubuntu-server\n",
            "/etc/ssh/sshd_config": "# SSH Server Configuration\nPort 22\nPermitRootLogin yes\n",
            "/root/.ssh/id_rsa": "-----BEGIN RSA PRIVATE KEY-----\nMIIEogIBAAKCAQEA...\n",
            "/root/.bashrc": "# .bashrc for root\n",
        }

    # ---------------------------
    # File system emulation
    # ---------------------------

    def ls(self, path=None):
        if not path:
            path = self.current_dir
        
        if path in self.directories:
            files = "  ".join(self.directories[path])
            return files
        else:
            return f"ls: cannot access '{path}': No such file or directory"

    def cat(self, name):
        # Check system files first
        if name in self.system_files:
            return self.system_files[name]
        
        # Check regular files
        if name in self.files:
            return self.files[name]
        
        # Check if it's a path in system files
        for sys_path, content in self.system_files.items():
            if sys_path.endswith('/' + name):
                return content
        
        return f"cat: {name}: No such file or directory"

    def add_file(self, filename, data_bytes):
        self.files[filename] = f"<binary data ({len(data_bytes)} bytes)>"
        
        # Add to current directory listing
        if self.current_dir not in self.directories:
            self.directories[self.current_dir] = []
        self.directories[self.current_dir].append(filename)
        
        return filename

    # ---------------------------
    # Fake system info
    # ---------------------------

    def fake_ps(self):
        procs = [
            "root       1  0.0  0.1  18560  1024 ?        Ss   10:00   0:00 /sbin/init",
            "root     234  0.0  0.3  35200  2400 ?        Ss   10:01   0:00 /usr/sbin/sshd -D",
            "www-data 512  0.0  0.5 120000  4000 ?        S    10:02   0:01 /usr/sbin/apache2 -k start",
            "user    1024  0.0  0.2  50000  2000 pts/0    Ss   10:03   0:00 -bash",
            "root    1025  0.0  0.1  30000  1500 ?        Ss   10:04   0:00 /usr/bin/python3 /opt/honeypot.py",
            "mysql   1026  0.0  1.2 500000 12000 ?        Ssl  10:05   0:02 /usr/sbin/mysqld",
            "root    1027  0.0  0.2  45000  2200 ?        Ss   10:06   0:00 /usr/sbin/cron -f",
        ]
        return "\n".join(random.sample(procs, k=5))

    def change_directory(self, path):
        if path == "..":
            # Simple parent directory - in real implementation, handle properly
            self.current_dir = "/home"
            return True
        elif path == "/":
            self.current_dir = "/"
            return True
        elif path in self.directories:
            self.current_dir = path
            return True
        else:
            # Check if it's a subdirectory
            for directory in self.directories:
                if directory.startswith(path) or path.startswith(directory):
                    self.current_dir = path
                    return True
            return False

    def get_current_directory(self):
        return self.current_dir

    def get_user(self):
        return self.user


def run_command(cmd: str, fs: PseudoFS = None, shell_name: str = "bash") -> Tuple[str, bool]:
    """
    Execute a shell command in the honeypot environment
    
    Args:
        cmd: Command string to execute
        fs: PseudoFS instance (optional, creates new one if None)
        shell_name: Shell name for error messages
    
    Returns:
        Tuple of (output_string, success_bool)
    """
    if fs is None:
        fs = PseudoFS()
    
    cmd = (cmd or "").strip()
    
    # Simulate command processing time
    time.sleep(random.uniform(0.05, 0.25))
    
    if cmd == "":
        return "", True

    try:
        # Parse command and arguments
        parts = shlex.split(cmd)
        if not parts:
            return "", True
            
        command = parts[0]
        args = parts[1:]

        # Handle different commands
        if command == "ls":
            path = args[0] if args else None
            output = fs.ls(path)
            return output, True

        elif command == "cat":
            if not args:
                return "cat: missing file operand", False
            output = fs.cat(args[0])
            success = not output.startswith("cat:")
            return output, success

        elif command == "cd":
            if not args:
                fs.change_directory("/home/user")
                return "", True
            success = fs.change_directory(args[0])
            if success:
                return "", True
            else:
                return f"bash: cd: {args[0]}: No such file or directory", False

        elif command in ["ps", "ps aux", "ps -aux", "ps -ef"]:
            output = fs.fake_ps()
            return output, True

        elif command == "uname":
            if "-a" in args:
                output = f"Linux {fs.hostname} 4.15.0-20-generic #21-Ubuntu SMP Tue Apr 24 08:16:15 UTC 2018 x86_64 x86_64 x86_64 GNU/Linux"
            elif "-r" in args:
                output = "4.15.0-20-generic"
            else:
                output = "Linux"
            return output, True

        elif command in ["wget", "curl"]:
            if not args:
                return f"{command}: missing URL", False
            
            url = args[0]
            fname = f"download_{int(time.time())}_{random.randint(1000,9999)}.bin"
            dummy_size = random.randint(100, 1024)
            dummy_data = b"\x00" * dummy_size

            fs.add_file(fname, dummy_data)

            if command == "wget":
                output = (
                    f"--{time.strftime('%Y-%m-%d %H:%M:%S')}--  {url}\n"
                    f"Resolving {url.split('//')[-1].split('/')[0]}... 192.168.1.100\n"
                    f"Connecting to {url.split('//')[-1].split('/')[0]}... connected.\n"
                    f"HTTP request sent, awaiting response... 200 OK\n"
                    f"Length: {dummy_size} (1.0K) [application/octet-stream]\n"
                    f"Saving to: '{fname}'\n\n"
                    f"100%[======================================>] {dummy_size}       --.-K/s   in 0s      \n\n"
                    f"{time.strftime('%Y-%m-%d %H:%M:%S')} ({dummy_size} B/s) - '{fname}' saved [{dummy_size}/{dummy_size}]"
                )
            else:  # curl
                output = (
                    f"  % Total    % Received % Xferd  Average Speed   Time    Time     Time  Current\n"
                    f"                                 Dload  Upload   Total   Spent    Left  Speed\n"
                    f"100 {dummy_size:4}  100 {dummy_size:4}    0     0   125k      0 --:--:-- --:--:-- --:--:--  125k\n"
                    f"Downloaded {dummy_size} bytes to {fname}"
                )
            return output, True

        elif command == "whoami":
            return f"{fs.get_user()}\n", True

        elif command == "id":
            return f"uid=0({fs.get_user()}) gid=0({fs.get_user()}) groups=0({fs.get_user()})\n", True

        elif command == "pwd":
            return f"{fs.get_current_directory()}\n", True

        elif command == "echo":
            return " ".join(args) + "\n", True

        elif command in ["mkdir", "rm", "cp", "mv"]:
            # Simulate successful file operations
            if command == "mkdir" and args:
                return f"mkdir: created directory '{args[0]}'\n", True
            elif command == "rm" and args:
                return "", True
            return "", True

        elif command == "netstat":
            if "-tuln" in args or "-an" in args:
                output = """Active Internet connections (only servers)
Proto Recv-Q Send-Q Local Address           Foreign Address         State      
tcp        0      0 0.0.0.0:22              0.0.0.0:*               LISTEN     
tcp        0      0 127.0.0.1:25            0.0.0.0:*               LISTEN     
tcp6       0      0 :::80                   :::*                    LISTEN     
tcp6       0      0 :::443                  :::*                    LISTEN     
udp        0      0 0.0.0.0:68              0.0.0.0:*                           """
            else:
                output = """Active Internet connections (w/o servers)
Proto Recv-Q Send-Q Local Address           Foreign Address         State      
tcp        0      0 192.168.1.100:22        192.168.1.50:54321      ESTABLISHED
tcp        0      0 192.168.1.100:22        192.168.1.51:43210      ESTABLISHED"""
            return output, True

        elif command == "ifconfig" or command == "ip addr":
            return f"""eth0: flags=4163<UP,BROADCAST,RUNNING,MULTICAST>  mtu 1500
        inet 192.168.1.100  netmask 255.255.255.0  broadcast 192.168.1.255
        inet6 fe80::20c:29ff:fe12:3456  prefixlen 64  scopeid 0x20<link>
        ether 00:0c:29:12:34:56  txqueuelen 1000  (Ethernet)
        RX packets {random.randint(10000, 50000)}  bytes {random.randint(10000000, 50000000)} ({(random.randint(10000000, 50000000)/1000000):.1f} MB)
        TX packets {random.randint(5000, 20000)}  bytes {random.randint(5000000, 20000000)} ({(random.randint(5000000, 20000000)/1000000):.1f} MB)

lo: flags=73<UP,LOOPBACK,RUNNING>  mtu 65536
        inet 127.0.0.1  netmask 255.0.0.0
        inet6 ::1  prefixlen 128  scopeid 0x10<host>
        loop  txqueuelen 1000  (Local Loopback)""", True

        elif command == "hostname":
            if "-f" in args or "--fqdn" in args:
                return f"{fs.hostname}.local\n", True
            return f"{fs.hostname}\n", True

        elif command == "uptime":
            uptime_days = random.randint(1, 30)
            uptime_hours = random.randint(1, 23)
            users = random.randint(1, 3)
            load = f"{random.uniform(0.1, 1.5):.2f}, {random.uniform(0.1, 1.5):.2f}, {random.uniform(0.1, 1.5):.2f}"
            return f" {time.strftime('%H:%M:%S')} up {uptime_days} days, {uptime_hours:02d}:{random.randint(10,59):02d},  {users} user,  load average: {load}\n", True

        elif command == "free":
            return f"""              total        used        free      shared  buff/cache   available
Mem:         1017692       {random.randint(200000,500000)}       {random.randint(300000,600000)}        {random.randint(10000,50000)}       {random.randint(100000,300000)}       {random.randint(400000,700000)}
Swap:        1048572       {random.randint(0,100000)}       {random.randint(900000,1048572)}""", True

        elif command == "df":
            return f"""Filesystem     1K-blocks    Used Available Use% Mounted on
/dev/sda1       10188088  {random.randint(2000000,5000000)}   {random.randint(5000000,8000000)}   {random.randint(20,40)}% /
tmpfs             {random.randint(500000,600000)}     {random.randint(1000,50000)}   {random.randint(450000,550000)}    {random.randint(1,5)}% /dev/shm
tmpfs              5120        {random.randint(0,100)}       {random.randint(5000,5120)}    {random.randint(1,2)}% /run/lock""", True

        elif command.startswith("sudo"):
            # Simulate sudo - just run the command as if we're root
            if len(args) > 0:
                sudo_cmd = " ".join(args)
                return run_command(sudo_cmd, fs, shell_name)
            else:
                return "usage: sudo -h | -K | -k | -V\nusage: sudo -v [-AknS] [-g group] [-h host] [-p prompt] [-u user]\nusage: sudo -l [-AknS] [-g group] [-h host] [-p prompt] [-U user] [-u user] [command]\nusage: sudo [-AbEHknPS] [-r role] [-t type] [-C num] [-g group] [-h host] [-p prompt] [-u user] [command]\n", True

        elif command == "ssh":
            if args:
                return f"ssh: connect to host {args[0]} port 22: Connection refused\n", False
            else:
                return "usage: ssh [-46AaCfGgKkMNnqsTtVvXxYy] [-B bind_interface]\n           [-b bind_address] [-c cipher_spec] [-D [bind_address:]port]\n           [-E log_file] [-e escape_char] [-F configfile] [-I pkcs11]\n           [-i identity_file] [-J [user@]host[:port]] [-L address]\n           [-l login_name] [-m mac_spec] [-O ctl_cmd] [-o option] [-p port]\n           [-Q query_option] [-R address] [-S ctl_path] [-W host:port]\n           [-w local_tun[:remote_tun]] destination [command]\n", False

        elif command == "scp":
            return "ssh: connect to host target port 22: Connection timed out\n", False

        elif command == "nmap":
            return """Starting Nmap 7.01 ( https://nmap.org ) at 2024-01-15 10:00 UTC
Note: Host seems down. If it is really up, but blocking our ping probes, try -Pn
Nmap done: 1 IP address (0 hosts up) scanned in 3.00 seconds\n""", False

        else:
            return f"{shell_name}: {command}: command not found\n", False

    except Exception as e:
        return f"{shell_name}: error executing command: {str(e)}\n", False