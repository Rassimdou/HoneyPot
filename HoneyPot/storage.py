# storage.py
import sqlite3, os, json, datetime

class Storage:
    def __init__(self, db_path="honeypot_modular.db", payload_dir="payloads"):
        os.makedirs(payload_dir, exist_ok=True)
        self.payload_dir = payload_dir
        self.conn = sqlite3.connect(db_path, check_same_thread=False)
        self._init_tables()

    def _init_tables(self):
        self.conn.execute('''
            CREATE TABLE IF NOT EXISTS events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                ts TEXT,
                type TEXT,
                src_ip TEXT,
                src_port INTEGER,
                payload TEXT
            )
        ''')
        self.conn.commit()

    def save_event(self, etype, src_ip, src_port, payload_obj):
        ts = datetime.datetime.utcnow().isoformat()
        payload_json = json.dumps(payload_obj, ensure_ascii=False)
        self.conn.execute('INSERT INTO events (ts, type, src_ip, src_port, payload) VALUES (?, ?, ?, ?, ?)',
                          (ts, etype, src_ip, src_port, payload_json))
        self.conn.commit()

    def list_events(self, limit=200):
        cur = self.conn.execute('SELECT id, ts, type, src_ip, src_port, payload FROM events ORDER BY id DESC LIMIT ?', (limit,))
        rows = cur.fetchall()
        results = []
        for r in rows:
            results.append({
                "id": r[0], "ts": r[1], "type": r[2], "src_ip": r[3], "src_port": r[4],
                "payload": json.loads(r[5]) if r[5] else {}
            })
        return results

    def save_payload(self, filename, data_bytes):
        safe_name = f"{int(datetime.datetime.utcnow().timestamp())}_{os.path.basename(filename)}"
        path = os.path.join(self.payload_dir, safe_name)
        with open(path, "wb") as f:
            f.write(data_bytes)
        return path



