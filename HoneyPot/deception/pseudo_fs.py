#!/usr/bin/env python3
"""
Pseudo honeypot shell simulator
- Cleaned and refactored version of user's script
- Unified system_files vs files handling
- Fixed incomplete SSH block and closed function
- Added: rm -rf, cp, mv, redirection '>', simple piping '|'
- Improved path handling and directory operations

This is a single-file module. It intentionally simulates a Linux environment
and does NOT perform real filesystem or network operations.
"""

import time
import random
import shlex
from typing import Tuple, List, Dict, Optional


class PseudoFS:
    def __init__(self, template: Optional[Dict[str, str]] = None):
        # User-provided files (regular files in the filesystem)
        template = template or {
            "README.txt": "Welcome to HoneyPot demo.\n",
            "config.php": "<?php // Database configuration\n$db_host = 'localhost';\n$db_user = 'root';\n$db_pass = 'secret123';\n?>",
            "index.html": "<html>\n<body>\n<h1>Under Construction</h1>\n<p>Site coming soon...</p>\n</body>\n</html>",
            ".bash_history": "ls\ncat README.txt\nps aux\nwhoami\n",
            "passwords.txt": "admin:password123\nroot:toor\nuser:123456\n",
            "backup.zip": "<compressed backup file>",
        }

        # store regular (user-level) files by absolute path
        self.files: Dict[str, str] = {}

        # system files stored by absolute path
        self.system_files: Dict[str, str] = {
            "/etc/passwd": "root:x:0:0:root:/root:/bin/bash\nuser:x:1000:1000:User,,,:/home/user:/bin/bash\n",
            "/etc/shadow": "root:$6$rounds=656000$H1ecrJNj6GVK6Vj2$V2RhS...:18000:0:99999:7:::\n",
            "/etc/hosts": "127.0.0.1 localhost\n192.168.1.100 ubuntu-server\n",
            "/etc/ssh/sshd_config": "# SSH Server Configuration\nPort 22\nPermitRootLogin yes\n",
            "/root/.ssh/id_rsa": "-----BEGIN RSA PRIVATE KEY-----\nMIIEogIBAKCAQEA...\n",
            "/root/.bashrc": "# .bashrc for root\n",
        }

        # directories map absolute path -> list of entries (names)
        self.directories: Dict[str, List[str]] = {
            "/": ["home", "etc", "var", "tmp", "root"],
            "/home": ["user"],
            "/home/user": ["README.txt", ".bash_history", "passwords.txt"],
            "/etc": ["passwd", "shadow", "hosts", "ssh"],
            "/etc/ssh": ["sshd_config"],
            "/var": ["www"],
            "/var/www": ["index.html", "config.php"],
            "/tmp": ["backup.zip"],
            "/root": [".ssh", ".bashrc"],
            "/root/.ssh": ["id_rsa"],
        }

        # populate self.files using template into /home/user
        for name, content in template.items():
            path = f"/home/user/{name}".replace("//", "/")
            self.files[path] = content

        # metadata
        self.current_dir = "/home/user"
        self.user = "root"
        self.hostname = "ubuntu-server"

    # ---------------------------
    # Utilities
    # ---------------------------
    def _abs_path(self, path: str) -> str:
        """Return an absolute normalized path for a given path (simple)."""
        if not path:
            return self.current_dir
        if path.startswith("/"):
            p = path
        elif path == "~":
            p = "/home/user"
        else:
            p = f"{self.current_dir}/{path}"
        # normalize: remove duplicate slashes and trailing slash except root
        while "//" in p:
            p = p.replace("//", "/")
        if len(p) > 1 and p.endswith("/"):
            p = p[:-1]
        return p

    def _parent_dir(self, path: str) -> str:
        if path == "/":
            return "/"
        return path.rsplit('/', 1)[0] or "/"

    def exists(self, path: str) -> bool:
        p = self._abs_path(path)
        if p in self.files or p in self.system_files or p in self.directories:
            return True
        # check if basename exists in parent directory
        parent = self._parent_dir(p)
        name = p.rsplit('/', 1)[-1]
        return parent in self.directories and name in self.directories[parent]

    def is_dir(self, path: str) -> bool:
        p = self._abs_path(path)
        return p in self.directories

    def list_dir(self, path: Optional[str] = None, show_hidden: bool = False) -> List[str]:
        p = self._abs_path(path or self.current_dir)
        if p not in self.directories:
            return []
        entries = list(self.directories[p])
        if not show_hidden:
            entries = [e for e in entries if not e.startswith('.')]
        entries.sort()
        return entries

    # ---------------------------
    # File operations
    # ---------------------------
    def read_file(self, path: str) -> str:
        p = self._abs_path(path)
        # direct lookup
        if p in self.files:
            return self.files[p]
        if p in self.system_files:
            return self.system_files[p]
        # fallback: if basename exists as system file
        basename = p.rsplit('/', 1)[-1]
        for sys_p, content in self.system_files.items():
            if sys_p.endswith('/' + basename):
                return content
        return f"cat: {path}: No such file or directory"

    def write_file(self, path: str, content: str) -> None:
        p = self._abs_path(path)
        parent = self._parent_dir(p)
        name = p.rsplit('/', 1)[-1]
        # create parent dir if missing
        if parent not in self.directories:
            self.directories[parent] = []
        # add to parent's listing
        if name not in self.directories[parent]:
            self.directories[parent].append(name)
        # write
        self.files[p] = content

    def add_binary_file(self, filename: str, data_bytes: bytes) -> str:
        p = self._abs_path(filename)
        self.write_file(p, f"<binary data ({len(data_bytes)} bytes)>")
        return p

    def remove_path(self, path: str, recursive: bool = False) -> bool:
        p = self._abs_path(path)
        # if directory
        if p in self.directories:
            if recursive:
                # remove subtree
                to_remove = [k for k in list(self.directories.keys()) if k == p or k.startswith(p + '/')]
                for d in to_remove:
                    del self.directories[d]
                # remove files under that path
                for f in list(self.files.keys()):
                    if f == p or f.startswith(p + '/'):
                        del self.files[f]
                # also remove entries in parent dir
                parent = self._parent_dir(p)
                name = p.rsplit('/', 1)[-1]
                if parent in self.directories and name in self.directories[parent]:
                    self.directories[parent].remove(name)
                return True
            else:
                # non-recursive: only remove if empty
                if self.directories[p]:
                    return False
                parent = self._parent_dir(p)
                name = p.rsplit('/', 1)[-1]
                if parent in self.directories and name in self.directories[parent]:
                    self.directories[parent].remove(name)
                del self.directories[p]
                return True

        # if file
        if p in self.files:
            del self.files[p]
            parent = self._parent_dir(p)
            name = p.rsplit('/', 1)[-1]
            if parent in self.directories and name in self.directories[parent]:
                self.directories[parent].remove(name)
            return True

        # system files cannot be removed in this simulation
        if p in self.system_files:
            return False

        return False

    def copy(self, src: str, dst: str) -> bool:
        s = self._abs_path(src)
        d = self._abs_path(dst)
        # simple file copy only
        if s in self.files or s in self.system_files:
            content = self.files.get(s) or self.system_files.get(s)
            self.write_file(d, content)
            return True
        return False

    def move(self, src: str, dst: str) -> bool:
        s = self._abs_path(src)
        d = self._abs_path(dst)
        success = self.copy(s, d)
        if success:
            # remove original if it was in user files
            if s in self.files:
                del self.files[s]
                parent = self._parent_dir(s)
                name = s.rsplit('/', 1)[-1]
                if parent in self.directories and name in self.directories[parent]:
                    self.directories[parent].remove(name)
            return True
        return False

    def make_dir(self, path: str) -> bool:
        p = self._abs_path(path)
        if p in self.directories:
            return True
        parent = self._parent_dir(p)
        name = p.rsplit('/', 1)[-1]
        if parent not in self.directories:
            self.directories[parent] = []
        self.directories[parent].append(name)
        self.directories[p] = []
        return True

    # ---------------------------
    # Emulated commands output
    # ---------------------------
    def ls(self, path: Optional[str] = None, show_hidden: bool = False, long_format: bool = False) -> str:
        target = self._abs_path(path or self.current_dir)
        if target not in self.directories:
            return f"ls: cannot access '{path or target}': No such file or directory"

        entries = self.list_dir(target, show_hidden=show_hidden)
        if not long_format:
            return "  ".join(entries)

        output_lines = []
        total_blocks = 0
        for name in entries:
            full = f"{target}/{name}".replace("//", "/")
            is_dir = full in self.directories
            perms = "drwxr-xr-x" if is_dir else "-rw-r--r--"
            links = random.randint(2, 5) if is_dir else 1
            owner = self.user
            group = self.user
            size = 4096 if is_dir else len(self.files.get(full, self.system_files.get(full, name)))
            month = random.choice(["Jan","Feb","Mar","Apr","May","Jun","Jul","Aug","Sep","Oct","Nov","Dec"])
            day = random.randint(1,28)
            time_str = f"{random.randint(0,23):02d}:{random.randint(0,59):02d}"
            output_lines.append(f"{perms} {links} {owner} {group} {size:5d} {month} {day:2d} {time_str} {name}")
            total_blocks += (size // 512) + 1

        return f"total {total_blocks}\n" + "\n".join(output_lines)

    def cat(self, name: str) -> str:
        # try relative/absolute
        result = self.read_file(name)
        return result

    def tail(self, filename: str, n: int = 10) -> str:
        content = self.cat(filename)
        if content.startswith("cat:"):
            return content
        lines = content.split('\n')
        return '\n'.join(lines[-n:])

    def head(self, filename: str, n: int = 10) -> str:
        content = self.cat(filename)
        if content.startswith("cat:"):
            return content
        lines = content.split('\n')
        return '\n'.join(lines[:n])

    def grep(self, pattern: str, filename: str) -> str:
        content = self.cat(filename)
        if content.startswith("cat:"):
            return content
        lines = content.split('\n')
        matches = [l for l in lines if pattern in l]
        return '\n'.join(matches)

    def fake_ps(self) -> str:
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

    def change_directory(self, path: str) -> bool:
        p = self._abs_path(path)
        if p == "..":
            # shouldn't happen after _abs_path, but handle gracefully
            parent = self._parent_dir(self.current_dir)
            self.current_dir = parent
            return True
        if p in self.directories:
            self.current_dir = p
            return True
        return False

    def get_current_directory(self) -> str:
        return self.current_dir

    def get_user(self) -> str:
        return self.user


# ---------------------------
# Command runner
# ---------------------------

def _split_pipe_and_redirects(cmd: str) -> Tuple[List[str], Optional[str]]:
    """Return list of pipe-separated commands and output redirection target (if '>')"""
    # naive split (doesn't consider quotes in '>' or '|') - sufficient for simple simulation
    redirect_target = None
    if '>' in cmd:
        parts = cmd.split('>')
        cmd = parts[0].strip()
        redirect_target = parts[1].strip()
    pipe_parts = [p.strip() for p in cmd.split('|')]
    return pipe_parts, redirect_target


def run_command(cmd: str, fs: Optional[PseudoFS] = None, shell_name: str = "bash") -> Tuple[str, bool]:
    """
    Execute a shell command in the honeypot environment.
    Supports simple piping and redirection (output only). Does not spawn real processes.
    """
    if fs is None:
        fs = PseudoFS()

    cmd = (cmd or "").strip()
    # simulate small processing delay
    time.sleep(random.uniform(0.02, 0.15))

    if cmd == "":
        return "", True

    try:
        # handle simple redirection and pipes first
        pipeline, redirect_target = _split_pipe_and_redirects(cmd)
        # run pipeline sequentially, passing previous output as input
        prev_output = ""
        prev_success = True
        for i, subcmd in enumerate(pipeline):
            # parse subcmd into parts respecting quotes
            parts = shlex.split(subcmd)
            if not parts:
                continue
            command = parts[0]
            args = parts[1:]

            # Built-in handlers
            if command == 'ls':
                path = None
                show_hidden = False
                long_format = False
                clean_args = []
                for a in args:
                    if a.startswith('-'):
                        if 'a' in a:
                            show_hidden = True
                        if 'l' in a:
                            long_format = True
                    else:
                        clean_args.append(a)
                if clean_args:
                    path = clean_args[0]
                prev_output, prev_success = fs.ls(path, show_hidden=show_hidden, long_format=long_format), True

            elif command == 'cat':
                if not args and prev_output:
                    # cat reads from previous pipe input
                    prev_output, prev_success = prev_output, True
                elif not args:
                    prev_output, prev_success = "cat: missing file operand", False
                else:
                    prev_output = fs.cat(args[0])
                    prev_success = not prev_output.startswith('cat:')

            elif command == 'cd':
                if not args:
                    fs.change_directory('/home/user')
                    prev_output, prev_success = "", True
                else:
                    success = fs.change_directory(args[0])
                    prev_output, prev_success = ("", True) if success else (f"bash: cd: {args[0]}: No such file or directory", False)

            elif command in ['ps', 'ps aux', 'ps -ef'] or command == 'ps':
                prev_output, prev_success = fs.fake_ps(), True

            elif command == 'uname':
                if '-a' in args:
                    prev_output = f"Linux {fs.hostname} 4.15.0-20-generic #21-Ubuntu SMP Tue Apr 24 08:16:15 UTC 2018 x86_64 x86_64 x86_64 GNU/Linux"
                elif '-r' in args:
                    prev_output = "4.15.0-20-generic"
                else:
                    prev_output = "Linux"
                prev_success = True

            elif command in ['wget', 'curl']:
                url = ""
                for a in args:
                    if not a.startswith('-'):
                        url = a
                        break
                if not url:
                    if args:
                        url = 'http://unknown.com/file'
                    else:
                        prev_output, prev_success = f"{command}: missing URL", False
                        continue
                fname = f"download_{int(time.time())}_{random.randint(1000,9999)}.bin"
                dummy_size = random.randint(100, 1024)
                fs.add_binary_file(fname, b"\x00" * dummy_size)
                if command == 'wget':
                    prev_output = (f"--{time.strftime('%Y-%m-%d %H:%M:%S')}--  {url}\n"
                                   f"Resolving {url.split('//')[-1].split('/')[0]}... 192.168.1.100\n"
                                   f"Connecting to {url.split('//')[-1].split('/')[0]}... connected.\n"
                                   f"HTTP request sent, awaiting response... 200 OK\n"
                                   f"Length: {dummy_size} (1.0K) [application/octet-stream]\n"
                                   f"Saving to: '{fname}'\n\n"
                                   f"100%[======================================>] {dummy_size}       --.-K/s   in 0s      \n\n"
                                   f"{time.strftime('%Y-%m-%d %H:%M:%S')} ({dummy_size} B/s) - '{fname}' saved [{dummy_size}/{dummy_size}]")
                else:
                    prev_output = f"Downloaded {dummy_size} bytes to {fname}"
                prev_success = True

            elif command == 'whoami':
                prev_output, prev_success = fs.get_user() + '\n', True

            elif command == 'id':
                prev_output, prev_success = f"uid=0({fs.get_user()}) gid=0({fs.get_user()}) groups=0({fs.get_user()})\n", True

            elif command == 'pwd':
                prev_output, prev_success = fs.get_current_directory() + '\n', True

            elif command == 'echo':
                text = ' '.join(args)
                if (text.startswith('"') and text.endswith('"')) or (text.startswith("'") and text.endswith("'")):
                    text = text[1:-1]
                prev_output, prev_success = text + '\n', True

            elif command in ['mkdir', 'rm', 'cp', 'mv', 'chmod', 'chown', 'touch']:
                if command == 'mkdir' and args:
                    fs.make_dir(args[0])
                    prev_output, prev_success = "", True
                elif command == 'rm' and args:
                    # support -r and -f and -rf and simple filename
                    flags = [a for a in args if a.startswith('-')]
                    targets = [a for a in args if not a.startswith('-')]
                    recursive = any('r' in f for f in flags)
                    # if no targets -> error
                    if not targets:
                        prev_output, prev_success = "rm: missing operand", False
                    else:
                        ok_all = True
                        for t in targets:
                            ok = fs.remove_path(t, recursive=recursive)
                            ok_all = ok_all and ok
                        prev_output, prev_success = ("", True) if ok_all else ("rm: failed to remove some files", False)
                elif command == 'cp' and len(args) >= 2:
                    src = args[0]
                    dst = args[1]
                    ok = fs.copy(src, dst)
                    prev_output, prev_success = ("", True) if ok else (f"cp: cannot stat '{src}': No such file or directory", False)
                elif command == 'mv' and len(args) >= 2:
                    src = args[0]
                    dst = args[1]
                    ok = fs.move(src, dst)
                    prev_output, prev_success = ("", True) if ok else (f"mv: cannot stat '{src}': No such file or directory", False)
                elif command == 'touch' and args:
                    fs.write_file(args[0], "")
                    prev_output, prev_success = "", True
                else:
                    prev_output, prev_success = "", True

            elif command == 'grep':
                if len(args) < 2:
                    prev_output, prev_success = "usage: grep [OPTION]... PATTERN [FILE]...", False
                else:
                    pattern = args[0].strip('"')
                    filename = args[1]
                    prev_output = fs.grep(pattern, filename) + '\n'
                    prev_success = True

            elif command == 'tail':
                if not args:
                    prev_output, prev_success = "tail: error reading 'standard input'", False
                else:
                    prev_output, prev_success = fs.tail(args[0]) + '\n', True

            elif command == 'head':
                if not args:
                    prev_output, prev_success = "head: error reading 'standard input'", False
                else:
                    prev_output, prev_success = fs.head(args[0]) + '\n', True

            elif command == 'date':
                prev_output, prev_success = time.strftime('%a %b %d %H:%M:%S UTC %Y') + '\n', True

            elif command == 'history':
                hist = fs.read_file('.bash_history')
                numbered = ''
                i = 1
                for line in hist.split('\n'):
                    if line:
                        numbered += f" {i:4d}  {line}\n"
                        i += 1
                prev_output, prev_success = numbered, True

            elif command == 'which':
                if not args:
                    prev_output, prev_success = "", True
                else:
                    bins = ['/usr/bin', '/bin', '/usr/sbin', '/sbin', '/usr/local/bin']
                    prev_output, prev_success = f"{random.choice(bins)}/{args[0]}\n", True

            elif command == 'netstat':
                if '-tuln' in args or '-an' in args:
                    prev_output = """Active Internet connections (only servers)\nProto Recv-Q Send-Q Local Address           Foreign Address         State      \ntcp        0      0 0.0.0.0:22              0.0.0.0:*               LISTEN     \ntcp        0      0 127.0.0.1:25            0.0.0.0:*               LISTEN     \ntcp6       0      0 :::80                   :::*                    LISTEN     \ntcp6       0      0 :::443                  :::*                    LISTEN     \nudp        0      0 0.0.0.0:68              0.0.0.0:*                           """
                else:
                    prev_output = """Active Internet connections (w/o servers)\nProto Recv-Q Send-Q Local Address           Foreign Address         State      \ntcp        0      0 192.168.1.100:22        192.168.1.50:54321      ESTABLISHED\ntcp        0      0 192.168.1.100:22        192.168.1.51:43210      ESTABLISHED"""
                prev_success = True

            elif command in ['ifconfig', 'ip']:
                prev_output = f"""eth0: flags=4163<UP,BROADCAST,RUNNING,MULTICAST>  mtu 1500\n        inet 192.168.1.100  netmask 255.255.255.0  broadcast 192.168.1.255\n        inet6 fe80::20c:29ff:fe12:3456  prefixlen 64  scopeid 0x20<link>\n        ether 00:0c:29:12:34:56  txqueuelen 1000  (Ethernet)\n        RX packets {random.randint(10000, 50000)}  bytes {random.randint(10000000, 50000000)}\n        TX packets {random.randint(5000, 20000)}  bytes {random.randint(5000000, 20000000)}\n\nlo: flags=73<UP,LOOPBACK,RUNNING>  mtu 65536\n        inet 127.0.0.1  netmask 255.0.0.0\n        inet6 ::1  prefixlen 128  scopeid 0x10<host>\n        loop  txqueuelen 1000  (Local Loopback)"""
                prev_success = True

            elif command == 'hostname':
                if '-f' in args or '--fqdn' in args:
                    prev_output, prev_success = f"{fs.hostname}.local\n", True
                else:
                    prev_output, prev_success = f"{fs.hostname}\n", True

            elif command == 'uptime':
                uptime_days = random.randint(1, 30)
                uptime_hours = random.randint(1, 23)
                users = random.randint(1, 3)
                load = f"{random.uniform(0.1, 1.5):.2f}, {random.uniform(0.1, 1.5):.2f}, {random.uniform(0.1, 1.5):.2f}"
                prev_output, prev_success = f" {time.strftime('%H:%M:%S')} up {uptime_days} days, {uptime_hours:02d}:{random.randint(10,59):02d},  {users} user,  load average: {load}\n", True

            elif command == 'free':
                prev_output = f"""              total        used        free      shared  buff/cache   available\nMem:         1017692       {random.randint(200000,500000)}       {random.randint(300000,600000)}        {random.randint(10000,50000)}       {random.randint(100000,300000)}       {random.randint(400000,700000)}\nSwap:        1048572       {random.randint(0,100000)}       {random.randint(900000,1048572)}"""
                prev_success = True

            elif command == 'df':
                prev_output = f"""Filesystem     1K-blocks    Used Available Use% Mounted on\n/dev/sda1       10188088  {random.randint(2000000,5000000)}   {random.randint(5000000,8000000)}   {random.randint(20,40)}% /\ntmpfs             {random.randint(500000,600000)}     {random.randint(1000,50000)}   {random.randint(450000,550000)}    {random.randint(1,5)}% /dev/shm\ntmpfs              5120        {random.randint(0,100)}       {random.randint(5000,5120)}    {random.randint(1,2)}% /run/lock"""
                prev_success = True

            elif command.startswith('sudo'):
                # treat sudo as pass-through: run the remainder of the command
                rest = subcmd.split(None, 1)
                if len(rest) > 1:
                    prev_output, prev_success = run_command(rest[1], fs, shell_name)
                else:
                    prev_output, prev_success = ("usage: sudo -h | -K | -k | -V\n", True)

            elif command == 'ssh':
                # Simplified SSH behaviour: if destination provided, simulate connection refused
                if args:
                    host = args[0]
                    prev_output, prev_success = (f"ssh: connect to host {host} port 22: Connection refused\n", False)
                else:
                    prev_output = (
                        "usage: ssh [-46AaCfGgKkMNnqsTtVvXxYy] [-B bind_interface]\n"
                        "           [-b bind_address] [-c cipher_spec] [-D [bind_address:]port]\n"
                        "           [-E log_file] [-e escape_char] [-F configfile] [-I pkcs11]\n"
                        "           [-i identity_file] [-J [user@]host[:port]] [-L address]\n"
                        "           [-l login_name] [-m mac_spec] [-O ctl_cmd] [-o option] [-p port]\n"
                        "           [-Q query_option] [-R address] [-S ctl_path] [-W host:port]\n"
                        "           [-w local_tun[:remote_tun]] destination [command]\n"
                    )
                    prev_success = False

            elif command == 'scp':
                prev_output, prev_success = ("ssh: connect to host target port 22: Connection timed out\n", False)

            elif command == 'nmap':
                prev_output = """Starting Nmap 7.01 ( https://nmap.org ) at 2024-01-15 10:00 UTC\nNote: Host seems down. If it is really up, but blocking our ping probes, try -Pn\nNmap done: 1 IP address (0 hosts up) scanned in 3.00 seconds\n"""
                prev_success = False

            elif command in ['apt', 'apt-get']:
                if not args:
                    prev_output, prev_success = "apt 1.6.12 (amd64)\nUsage: apt command [options]\n", True
                else:
                    sub = args[0]
                    if sub == 'update':
                        prev_output = """Hit:1 http://archive.ubuntu.com/ubuntu focal InRelease\nGet:2 http://security.ubuntu.com/ubuntu focal-security InRelease [114 kB]\nFetched 228 kB in 1s (230 kB/s)\nReading package lists... Done\n"""
                        prev_success = True
                    elif sub == 'upgrade':
                        prev_output = """Reading package lists... Done\nCalculating upgrade... Done\n0 upgraded, 0 newly installed, 0 to remove and 0 not upgraded.\n"""
                        prev_success = True
                    elif sub == 'install' and len(args) >= 2:
                        pkgs = ' '.join(args[1:])
                        prev_output = f"Reading package lists... Done\nThe following NEW packages will be installed:\n  {pkgs}\n0 upgraded, 1 newly installed, 0 to remove and 0 not upgraded.\n"
                        prev_success = True
                    else:
                        prev_output, prev_success = "", True

            elif command in ['service', 'systemctl']:
                # best-effort simplified handling
                if command == 'service' and len(args) >= 2:
                    srv_name = args[0]
                    action = args[1]
                elif command == 'systemctl' and len(args) >= 2:
                    action = args[0]
                    srv_name = args[1]
                else:
                    prev_output, prev_success = "", True
                    continue
                if action == 'status':
                    prev_output = (f"\u25CF {srv_name}.service - {srv_name} Service\n   Loaded: loaded (/lib/systemd/system/{srv_name}.service; enabled; vendor preset: enabled)\n   Active: active (running) since {time.strftime('%a %Y-%m-%d %H:%M:%S %Z')}; 2 days ago\n Main PID: {random.randint(500, 30000)} ({srv_name})\n")
                    prev_success = True
                elif action in ['start', 'restart', 'stop']:
                    prev_output, prev_success = "", True
                else:
                    prev_output, prev_success = "", True

            elif command == 'git':
                if not args:
                    prev_output = "usage: git [--version] [--help] [-C <path>] [-c <name>=<value>] ...\n"
                    prev_success = True
                else:
                    sub = args[0]
                    if sub == 'clone' and len(args) >= 2:
                        prev_output = (f"Cloning into '{args[1].split('/')[-1].replace('.git','')}'...\n"
                                       "remote: Enumerating objects: 100, done.\nReceiving objects: 100% (100/100), 1.20 MiB | 2.40 MiB/s, done.\n")
                        prev_success = True
                    else:
                        prev_output = f"git: '{sub}' is not a git command. See 'git --help'.\n"
                        prev_success = False

            else:
                # unknown command
                prev_output, prev_success = f"{shell_name}: {command}: command not found\n", False

            # end of command handling iteration
            # if next command in pipeline expects stdin we pass prev_output

        # after pipeline, if redirect_target is set -> write prev_output to file
        if redirect_target:
            # strip possible quotes
            redirect_target = redirect_target.strip('"')
            fs.write_file(redirect_target, prev_output)
            # mimic shell behavior: no output when redirect successful
            return "", True

        return prev_output, prev_success

    except Exception as e:
        return f"{shell_name}: error executing command: {str(e)}\n", False


# For interactive testing
if __name__ == '__main__':
    fs = PseudoFS()
    print("Pseudo honeypot shell simulator. Type 'exit' or Ctrl-C to quit.")
    try:
        while True:
            try:
                cmd = input(f"{fs.get_user()}@{fs.hostname}:{fs.get_current_directory()}$ ")
            except EOFError:
                break
            if not cmd:
                continue
            if cmd.strip() in ('exit', 'quit'):
                break
            out, ok = run_command(cmd, fs)
            if out:
                print(out, end='')
    except KeyboardInterrupt:
        print('\nbye')
