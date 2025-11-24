import sqlite3
import json
import threading
import time

class SQLiteStorage:
    def __init__(self, db_path="honeypot.db"):
        self.db_path = db_path
        self.slock = threading.Lock()
        self._init_db()


    def _connect(self):
        return sqlite3.connect(self.db_path, check_same_thread=False)
    

    def _init_db(self):
        conn = self._connect()
        cur = conn.cursor()

        # EVENTS TABLE (universal logs)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                type TEXT NOT NULL,
                src_ip TEXT NOT NULL,
                src_port INTEGER,
                payload TEXT,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
            );
        """)

        #Sessions
        cur.execute("""
            CREATE TABLE IF NOT EXISTS sessions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT UNIQUE,
                src_ip TEXT,
                src_port INTEGER,
                username TEXT,
                start_time DATETIME DEFAULT CURRENT_TIMESTAMP,
                end_time DATETIME,
                duration REAL
            );
        """)

        # AUTH ATTEMPTS
        cur.execute("""
            CREATE TABLE IF NOT EXISTS auth_attempts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT,
                src_ip TEXT,
                username TEXT,
                password TEXT,
                attempt_number INTEGER,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
            );
        """)

        
        # COMMANDS
        cur.execute("""
            CREATE TABLE IF NOT EXISTS commands (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT,
                src_ip TEXT,
                username TEXT,
                command TEXT,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
            );
        """)

         # GEOIP
        cur.execute("""
            CREATE TABLE IF NOT EXISTS geoip (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                src_ip TEXT UNIQUE,
                country TEXT,
                city TEXT,
                lat REAL,
                lon REAL,
                asn INTEGER,
                org TEXT,
                first_seen DATETIME DEFAULT CURRENT_TIMESTAMP
            );
        """)


        # INDEXES (important for performance)
        cur.execute("CREATE INDEX IF NOT EXISTS idx_events_ip ON events(src_ip)")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_auth_ip ON auth_attempts(src_ip)")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_cmd_ip ON commands(src_ip)")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_geoip_ip ON geoip(src_ip)")

        conn.commit()
        conn.close()

    #MAIN event saver (called by baseHandler.emit)
    def save_event(self, etype, ip, port, paylaod):
        with self.lock:
            conn = self._connect()
            cur = conn.cursor()

            #Insert JSON payload in event table
            cur.execute("""
                INSERT INTO events (type, src_ip, src_port, payload)
                VALUES (?, ?, ?, ?)
            """,(etype, ip, port, json.dumps(paylaod)))

            conn.commit()
            conn.close()

            #dispatch to specific tables

            if etype == "connection":
                self.save_geoip(paylaod)
            if etype == "auth_attempt":
                self.save_auth_attempt(paylaod)
            if etype == "command":
                self.save_command(paylaod)
            if etype == "session_end":
                self.close_session(paylaod)


        def save_auth_attempt(self, p):
            conn = self._connect()
            cur = conn.cursor()
            cur.execute("""
                INSERT INTO auth_attempts (session_id, src_ip, username, password, attempt_number)
                VALUES (?, ?, ?, ?, ?)
            """, (p["session_id"], p["src_ip"], p["user"], p["pass"], p["attempt"]))
            conn.commit()
            conn.close()

        def save_command(self, p):
            conn = self._connect()
            cur = conn.cursor()
            cur.execute("""
                INSERT INTO commands (session_id, src_ip, username, command)
                VALUES (?, ?, ?, ?)
            """, (p["session_id"], p["src_ip"], p["user"], p["command"]))
            conn.commit()
            conn.close()


        def save_geoip(self, p):
            if "geo" not in p: 
                return

            geo = p["geo"]
            conn = self._connect()
            cur = conn.cursor()

            cur.execute("""
                INSERT OR IGNORE INTO geoip (src_ip, country, city, lat, lon, asn, org)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                p["src_ip"],
                geo.get("country"),
                geo.get("city"),
                geo.get("lat"),
                geo.get("lon"),
                geo.get("asn"),
                geo.get("org")
            ))

            conn.commit()
            conn.close()


        def close_session(self, p):
            conn = self._connect()
            cur = conn.cursor()

            cur.execute("""
                UPDATE sessions SET
                    end_time = CURRENT_TIMESTAMP,
                    duration = ?
                WHERE session_id = ?
            """, (p["duration"], p["session_id"]))

            conn.commit()
            conn.close()



        def start_session(self, payload):
            conn = self._connect()
            cur = conn.cursor()

            cur.execute("""
                INSERT OR IGNORE INTO sessions (session_id, src_ip, src_port, username)
                VALUES (?, ?, ?, ?)
            """, (
                payload["session_id"],
                payload["src_ip"],
                payload["src_port"],
                payload.get("user", "")
            ))

            conn.commit()
            conn.close()

