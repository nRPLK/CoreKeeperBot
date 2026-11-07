"""Verbindung zum Mod (oder zu fake_game.py): JSON-Zeilen über TCP."""
import json
import socket
import time


class GameLink:
    def __init__(self, host="127.0.0.1", port=7777):
        self.host, self.port = host, port
        self.sock = None
        self.buffer = b""
        self.last_id = 0

    def connect(self):
        while True:
            try:
                self.sock = socket.create_connection((self.host, self.port))
                self.sock.setblocking(False)
                print(f"[link] verbunden mit {self.host}:{self.port}")
                return
            except OSError:
                print("[link] Spiel/Mod nicht erreichbar, neuer Versuch in 2 s ...")
                time.sleep(2)

    def receive(self):
        """Gibt alle seit dem letzten Aufruf angekommenen Nachrichten zurück."""
        messages = []
        try:
            while True:
                chunk = self.sock.recv(65536)
                if not chunk:
                    raise ConnectionError("Verbindung geschlossen")
                self.buffer += chunk
        except BlockingIOError:
            pass
        while b"\n" in self.buffer:
            line, self.buffer = self.buffer.split(b"\n", 1)
            if line.strip():
                messages.append(json.loads(line))
        return messages

    def send(self, action, **fields):
        self.last_id += 1
        msg = {"type": "cmd", "id": self.last_id, "action": action, **fields}
        self.sock.sendall((json.dumps(msg) + "\n").encode("utf-8"))
