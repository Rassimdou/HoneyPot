import time,random 

class PseudoFS:
    def __init__(self , template=None):
        template = template or{ 
        "README.txt":"Welcome to HoneyPot demo. \n",
        "config.php":"<?php // example ?>\n",
        
        }
        self.files = dict(template)

    def ls(self):
        return "  ".join(self.files.keys())
    
    def cat(self, name):
        return self.files.get(name, f"cat:{name}:No such file or directory")
    
    def add_file(self, filename , data_bytes):
        #store small textual description
        self.files[filename] = f"<binary ({len(data_bytes)}bytes)>"
        return filename
    

    def fake_ps():
        procs=[
            "root       1  0.0  0.1  18560  1024 ?        Ss   10:00   0:00 /sbin/init",
        "root     234  0.0  0.3  35200  2400 ?        Ss   10:01   0:00 /usr/sbin/sshd -D",
        "www-data 512  0.0  0.5 120000  4000 ?        S    10:02   0:01 /usr/sbin/apache2 -k start",
        "user    1024  0.0  0.2  50000  2000 pts/0    Ss   10:03   0:00 -bash"
        ]
        return "\n".join(random.sample(procs, k=3))
    

    def run_command(cmd, fs, shell_name="bash"):
        cmd =(cmd or "").strip()
        time.sleep(random.uniform(0.05,0.25))
        if cmd == "":
            return ""
        if cmd == "ls":
            return fs.ls()
        if cmd.startswith("cat "):
            _, name = cmd.split(" ", 1)
        return fs.cat(name)
        if cmd in ("ps", "ps aux"):
            return fake_ps()
        if cmd.startswith("uname"):
            return "Linux ubuntu 4.15.0-20-generic #21-Ubuntu SMP x86_64 GNU/Linux"
        if cmd.startswith("wget ") or cmd.startswith("curl "):
            parts = cmd.split()
            url = parts[1] if len(parts) > 1 else "unknown"
            fname = f"download_{int(time.time())}.bin"
            dummy = b"\x00" * 128
            fs.add_file(fname, dummy)
        return f"Connecting to {url}\nSaving to: '{fname}'\n"
    # fallback
        return f"{shell_name}: {cmd.split()[0]}: command not found"