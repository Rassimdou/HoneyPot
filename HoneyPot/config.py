
LISTEN =[
    {"name":"ssh_like","host":"0.0.0.0","port":2222,
     "banner": "SSH-2.0-OpenSSH_7.6p1 Ubuntu-4ubuntu0.3", "session_timeout": 120},
    {"name": "http_like", "host": "0.0.0.0", "port": 8080,
     "banner": "HTTP/1.1 200 OK | Server: Apache/2.4.18 (Ubuntu)"},

]

STORAGE = {
    "db_path": "honeypot_modular.db",
    "payload_dir": "payloads"
}

GENERAL = {
    "verbose": True
}
