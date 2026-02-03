# HoneyPot Project Documentation

This document provides an overview of the HoneyPot project, its structure, and a detailed reference of its modules, classes, and methods.

## Project Overview

The HoneyPot project is a modular honeypot system designed to deceive attackers and log their activities. It supports multiple protocols (currently SSH and HTTP) through a handler-based architecture. It features a pseudo-filesystem to simulate a convincing environment, GeoIP lookup for attacker attribution, and a SQLite-based storage system for logging events, sessions, authentication attempts, and commands.

## Project Structure

- **`HoneyPot/`**: The main source code directory.
    - **`handlers/`**: Protocol-specific handlers (SSH, HTTP).
    - **`deception/`**: Modules for deception (fake filesystem, command emulation).
    - **`storage/`**: Database storage implementation.
    - **`config.py`**: Configuration settings.
    - **`geoip.py`**: GeoIP lookup functionality.
    - **`run_honeypot.py`**: Main entry point to start the honeypot.
    - **`storage.py`**: (Alternative/Legacy) Storage implementation.

## Detailed API Reference

### 1. Main Application

#### `HoneyPot/run_honeypot.py`
The entry point of the application.

- **`create_handler(handler_name, host, port, cfg, storage, verbose=True)`**
    - Factory function that dynamically instantiates a handler based on `handler_name` (e.g., "ssh_like", "http_like").
    - **Arguments:**
        - `handler_name`: String name of the handler to create.
        - `host`, `port`: bind address.
        - `cfg`: Configuration dictionary for the handler.
        - `storage`: Storage backend instance.
        - `verbose`: Boolean flag for logging.
    - **Returns:** An instance of the requested handler class.

- **`main()`**
    - Initializes the `SQLiteStorage`.
    - Iterates through the `LISTEN` configuration from `config.py`.
    - Creates and starts handler threads.
    - Keeps the main thread alive with an infinite loop.

#### `HoneyPot/config.py`
Contains configuration dictionaries.

- **`LISTEN`**: List of dictionaries, each defining a service listener (e.g., SSH on port 2222, HTTP on port 8080).
- **`STORAGE`**: Configuration for database path.
- **`GENERAL`**: General settings (e.g., verbose mode).

---

### 2. Handlers (`HoneyPot/handlers/`)

#### `HoneyPot/handlers/base.py`

**Class `BaseHandler`**
Base class for all protocol handlers.

- **`__init__(self, host, port, cfg, storage, verbose=True)`**
    - Initializes the handler with connection details, config, and storage backend.
- **`emit(self, etype, payload)`**
    - Helper method to save an event to storage.
    - **Arguments:**
        - `etype`: Event type string (e.g., "connection", "command").
        - `payload`: Dictionary containing event details.
- **`start(self)`**
    - Starts the `start_listener` event loop in a daemon thread.

#### `HoneyPot/handlers/http_handler.py`

**Class `HTTPHandler`** (Inherits `BaseHandler`)
Simulates a simple HTTP server.

- **`__init__(self, ...)`**: Sets up the generic HTTP banner.
- **`start_listener(self)`**
    - Binds a socket to the configured host/port.
    - Accepts incoming connections and spawns a thread for `handle_client`.
- **`handle_client(self, conn, addr)`**
    - Reads the HTTP request line.
    - Logs the connection event.
    - Sends a fake Apache/Ubuntu HTTP response.
    - Closes connection.

#### `HoneyPot/handlers/ssh_handler.py`

**Class `SSHHandler`** (Inherits `BaseHandler`)
Simulates an SSH server with interacting shell.

- **`__init__(self, ...)`**: Defines `weak_credentials` and session timeout.
- **`start_listener(self)`**: Binds socket and accepts connections.
- **`check_credentials(self, username, password)`**: Verifies if the provided credentials match the weak list.
- **`handle_client(self, conn, addr)`**
    - Performs GeoIP lookup on the client IP.
    - Performs SSH version banner exchange.
    - Logs the local and client banners.
    - Handles the authentication loop (simulates usage of `login:` implementation, though actual SSH protocol is more complex; this appears to be a raw TCP emulation of an undefined or telnet-like login over the configured port, or a simplified SSH handshake simulation). *Note: The code implements a text-based login prompt (`login:`, `Password:`), effectively acting more like Telnet disguised as SSH or a very basic interaction.*
    - Starts the shell session upon success.
- **`run_shell_session(self, conn, ip, port, username, session_id)`**
    - Initializes a `PseudoFS`.
    - Enters a loop reading characters one by one to support rudimentary line editing (backspace).
    - Parses commands and executes them via `run_command` and `PseudoFS`.
    - Logs commands and the session end.

---

### 3. Deception (`HoneyPot/deception/`)

#### `HoneyPot/deception/pseudo_fs.py`

**Class `PseudoFS`**
Simulates a filesystem in memory.

- **`__init__(self, template=None)`**
    - Sets up initial file structure (`/home/user`, `/etc`, etc.) and system files.
- **`ls(self, path=None)`**
    - Lists files in the current or specified directory.
- **`cat(self, name)`**
    - Returns the content of a virtual file.
- **`add_file(self, filename, data_bytes)`**
    - "Uploads" a file to the virtual filesystem (stores bytes in memory).
- **`fake_ps(self)`**
    - Returns a distinct list of fake running processes.
- **`change_directory(self, path)`**
    - Changes the virtual current working directory.
- **`get_current_directory(self)`**
    - Returns current path.
- **`get_user(self)`**
    - Returns current virtual user.

**Function `run_command(cmd, fs=None, shell_name="bash")`**
- logic to parse and emulate common shell commands (`ls`, `cd`, `cat`, `ps`, `uname`, `wget`, `curl`, `whoami`, `id`, `pwd`, `echo`, `mkdir`, `rm`, `netstat`, `ifconfig`, `hostname`, `uptime`, `free`, `df`).
- **Returns:** Tuple `(output_string, success_boolean)`.

---

### 4. Storage

#### `HoneyPot/storage/sqlite_storage.py` (Primary)

**Class `SQLiteStorage`**
Handles persistence using SQLite.

- **`__init__(self, db_path)`**: Initializes lock and calls `_init_db`.
- **`_connect(self)`**: Returns a new SQLite connection.
- **`_init_db(self)`**: Creates tables `events`, `sessions`, `auth_attempts`, `commands`, `geoip` and associated indexes.
- **`save_event(self, etype, ip, port, paylaod)`**:
    - Saves the raw event JSON to the `events` table.
    - Calls specific saver methods based on `etype` (connection, auth_attempt, command, session_end).
- **`save_auth_attempt(self, p)`**: Inserts into `auth_attempts`.
- **`save_command(self, p)`**: Inserts into `commands`.
- **`save_geoip(self, p)`**: Inserts into `geoip` (avoiding duplicates via INSERT OR IGNORE).
- **`close_session(self, p)`**: Updates `sessions` table with end time and duration.
- **`start_session(self, payload)`**: Inserts new session record.

#### `HoneyPot/storage.py` (Secondary/Base)

**Class `Storage`**
A simpler or alternative storage implementation.

- **`__init__`**: Connects to DB.
- **`_init_tables`**: Creates simple `events` table.
- **`save_event`**: Inserts event.
- **`list_events`**: Retrieves events.
- **`save_payload`**: Saves binary data to a file in the `payloads` directory.

---

### 5. Utilities

#### `HoneyPot/geoip.py`

**Class `GeoIP`**
Wrapper around `geoip2` library for IP geolocation.

- **`__init__(self)`**: Attempts to load City and ASN mmdb files.
- **`load_database(self)`**: Loads the database readers.
- **`lookup(self, ip)`**
    - Queries the City and ASN databases.
    - **Returns:** Dict with `country`, `city`, `asn`, `org`.
