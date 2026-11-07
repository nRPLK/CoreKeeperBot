"""Test für den echten Mod (BotBridge v1): zeigt, was das Spiel schickt.
Start (während Core Keeper mit Mod läuft):  python bot\\mod_probe.py
"""
import json
import socket
import time
from collections import Counter

while True:
    try:
        sock = socket.create_connection(("127.0.0.1", 7777))
        break
    except OSError:
        print("Mod nicht erreichbar (läuft Core Keeper mit BotBridge?) - neuer Versuch in 2 s")
        time.sleep(2)

print("verbunden!")
buf, last_print = b"", 0
while True:
    chunk = sock.recv(65536)
    if not chunk:
        print("Verbindung getrennt")
        break
    buf += chunk
    while b"\n" in buf:
        line, buf = buf.split(b"\n", 1)
        msg = json.loads(line)
        if time.time() - last_print > 1:
            last_print = time.time()
            p = msg["player"]
            kinds = Counter(n["name"] for n in msg["nearby"])
            print(f"Position ({p['x']}, {p['y']}) | Blöcke in der Nähe: {dict(kinds)}")
