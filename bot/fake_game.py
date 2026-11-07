"""Testspiel: simuliert den Core-Keeper-Mod, damit der Bot ohne echtes Spiel testbar ist.
Spricht dasselbe Protokoll wie der echte Mod (siehe PROTOKOLL.md).
Rezepte und Welt sind BEISPIELWERTE, nicht die echten Core-Keeper-Daten.
Start:  python bot\\fake_game.py
"""
import json
import random
import socket
import time

TICK = 0.2
VIEW = 8  # Sichtweite in Kacheln

RECIPES = {  # Beispielwerte
    "Werkbank": {"Holz": 8},
    "Fackel": {"Holz": 1},
    "Kupferbarren": {"Kupfererz": 2},
}


def dist(ax, ay, bx, by):
    return max(abs(ax - bx), abs(ay - by))


class World:
    def __init__(self, seed=1):
        rnd = random.Random(seed)
        self.blocks = {}
        for name, count, spread in [("Holz", 14, 9), ("Kupfererz", 10, 12), ("Zinnerz", 5, 16)]:
            while count:
                x, y = rnd.randint(-spread, spread), rnd.randint(-spread, spread)
                if (x, y) != (0, 0) and (x, y) not in self.blocks:
                    self.blocks[(x, y)] = name
                    count -= 1
        self.px, self.py, self.hp = 0, 0, 100
        self.inv = {}
        self.target = None
        self.mining = 0
        self.enemies = []
        self.events = []
        self.t = 0
        self.last_cmd = 0
        self.prev = None
        self.stuck = 0

    # --- Befehle ---------------------------------------------------------
    def command(self, c):
        self.last_cmd = c.get("id", self.last_cmd)
        a = c.get("action")
        if a == "move_to":
            self.target, self.prev, self.stuck = (c["x"], c["y"]), None, 0
        elif a == "mine":
            pos = (c["x"], c["y"])
            if pos in self.blocks and dist(self.px, self.py, *pos) <= 1:
                self.mining = 3
                self.mine_pos = pos
        elif a == "attack":
            for e in self.enemies:
                if (e["x"], e["y"]) == (c["x"], c["y"]) and dist(self.px, self.py, e["x"], e["y"]) <= 1:
                    e["hp"] -= 10
                    if e["hp"] <= 0:
                        self.events.append(f"{e['name']} besiegt")
            self.enemies = [e for e in self.enemies if e["hp"] > 0]
        elif a == "craft":
            item = c["item"]
            r = RECIPES.get(item)
            if r and all(self.inv.get(k, 0) >= v for k, v in r.items()):
                for k, v in r.items():
                    self.inv[k] -= v
                self.inv[item] = self.inv.get(item, 0) + 1
                self.events.append(f"{item} gecraftet")
            else:
                self.events.append(f"Craften von {item} fehlgeschlagen")

    # --- Simulation ------------------------------------------------------
    def tick(self):
        self.t += 1
        if self.mining:
            self.mining -= 1
            if self.mining == 0 and self.mine_pos in self.blocks:
                name = self.blocks.pop(self.mine_pos)
                self.inv[name] = self.inv.get(name, 0) + 1
        elif self.target:
            tx, ty = self.target
            stop = 1 if (tx, ty) in self.blocks else 0
            if dist(self.px, self.py, tx, ty) <= stop:
                self.target = None
            else:
                # einfacher Weg um Hindernisse: freies Nachbarfeld, das am nächsten zum Ziel liegt
                now = dist(self.px, self.py, tx, ty)
                free = [(self.px + dx, self.py + dy) for dx in (-1, 0, 1) for dy in (-1, 0, 1)
                        if (dx, dy) != (0, 0) and (self.px + dx, self.py + dy) not in self.blocks
                        and (self.px + dx, self.py + dy) != self.prev]
                if not free:
                    self.target = None
                else:
                    best = min(free, key=lambda c: (dist(*c, tx, ty), abs(c[0] - tx) + abs(c[1] - ty)))
                    self.stuck = self.stuck + 1 if dist(*best, tx, ty) >= now else 0
                    if self.stuck > 6:
                        self.target, self.stuck = None, 0  # gibt auf
                    else:
                        self.prev = (self.px, self.py)
                        self.px, self.py = best
        # Gegner
        if not self.enemies and random.random() < 0.01:
            self.enemies.append({"name": "Schleim", "x": self.px + 5, "y": self.py + 3, "hp": 30})
            self.events.append("Ein Schleim taucht auf")
        for e in self.enemies:
            if dist(self.px, self.py, e["x"], e["y"]) > 1:
                if self.t % 3 == 0:
                    e["x"] += (self.px > e["x"]) - (self.px < e["x"])
                    e["y"] += (self.py > e["y"]) - (self.py < e["y"])
            elif self.t % 5 == 0:
                self.hp = max(0, self.hp - 5)
        if (self.px, self.py) == (0, 0) and self.hp < 100:
            self.hp = min(100, self.hp + 2)

    def state(self):
        return {
            "type": "state",
            "player": {"x": self.px, "y": self.py, "hp": self.hp, "hp_max": 100},
            "home": {"x": 0, "y": 0},
            "inventory": dict(self.inv),
            "nearby": [{"name": n, "x": x, "y": y} for (x, y), n in self.blocks.items()
                       if dist(self.px, self.py, x, y) <= VIEW],
            "enemies": [dict(e) for e in self.enemies],
            "busy": bool(self.mining or self.target),
            "last_cmd": self.last_cmd,
        }


def send(conn, obj):
    conn.sendall((json.dumps(obj, ensure_ascii=False) + "\n").encode("utf-8"))


def main():
    server = socket.socket()
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server.bind(("127.0.0.1", 7777))
    server.listen(1)
    print("[fake_game] warte auf Bot auf 127.0.0.1:7777 ...")
    conn, _ = server.accept()
    conn.setblocking(False)
    print("[fake_game] Bot verbunden")
    world, buf = World(), b""
    send(conn, {"type": "recipes", "recipes": RECIPES})
    while True:
        try:
            while True:
                chunk = conn.recv(65536)
                if not chunk:
                    print("[fake_game] Bot getrennt")
                    return
                buf += chunk
        except BlockingIOError:
            pass
        while b"\n" in buf:
            line, buf = buf.split(b"\n", 1)
            if line.strip():
                world.command(json.loads(line))
        world.tick()
        for ev in world.events:
            send(conn, {"type": "event", "text": ev})
            print(f"[fake_game] {ev}")
        world.events.clear()
        send(conn, world.state())
        if world.t % 10 == 0:
            print(f"[fake_game] pos=({world.px},{world.py}) hp={world.hp} inv={world.inv}")
        time.sleep(TICK)


if __name__ == "__main__":
    main()
