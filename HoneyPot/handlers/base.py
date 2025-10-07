
import threading

class BaseHandler:
    """
    Base class for protocol handlers.
    Subclasses must implement start_listener() and handle_client().
    """
    def __init__(self, host, port, cfg, storage, verbose=True):
        self.host = host
        self.port = int(port)
        self.cfg = cfg
        self.storage = storage
        self.verbose = verbose

    def emit(self, etype, payload):
        if self.storage:
            self.storage.save_event(etype, payload.get("src_ip","0.0.0.0"), payload.get("src_port",0), payload)

    def start(self):
        t = threading.Thread(target=self.start_listener, daemon=True)
        t.start()
        if self.verbose:
            print(f"[+] Started handler {self.__class__.__name__} on {self.host}:{self.port}")
