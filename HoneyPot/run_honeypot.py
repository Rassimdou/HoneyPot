
import config
from storage import Storage
import time

# dynamic imports for handlers
from importlib import import_module

def create_handler(handler_name, host, port, cfg, storage, verbose=True):
    # map simple name -> module class
    mapping = {
        "ssh_like": ("handlers.ssh_handler", "SSHHandler"),
        "http_like": ("handlers.http_handler", "HTTPHandler"),
    }
    if handler_name not in mapping:
        raise ValueError("Unknown handler: " + handler_name)
    module_path, class_name = mapping[handler_name]
    mod = import_module(module_path)
    cls = getattr(mod, class_name)
    return cls(host, port, cfg, storage, verbose=verbose)

def main():
    storage = Storage(db_path=config.STORAGE["db_path"], payload_dir=config.STORAGE["payload_dir"])
    handlers = []
    for item in config.LISTEN:
        name = item.get("name")
        host = item.get("host", "0.0.0.0")
        port = item.get("port")
        h = create_handler(name, host, port, item, storage, verbose=config.GENERAL.get("verbose", True))
        h.start()
        handlers.append(h)
    print("[*] Honeypot started with handlers:", [h.__class__.__name__ for h in handlers])
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n[*] Stopping honeypot")

if __name__ == "__main__":
    main()
