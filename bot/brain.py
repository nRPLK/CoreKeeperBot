"""Reflexe (feste Regeln) und Ausführung von Zielen in einzelne Befehle."""
import random


def dist(ax, ay, bx, by):
    return max(abs(ax - bx), abs(ay - by))  # Kachel-Abstand inkl. diagonal


def reflex(state):
    """Sofortige Reaktionen, ohne LLM. Gibt (action, fields) oder None zurück."""
    p = state["player"]
    if p["hp"] < 0.3 * p["hp_max"]:
        h = state["home"]
        if dist(p["x"], p["y"], h["x"], h["y"]) > 0:
            return "move_to", {"x": h["x"], "y": h["y"]}, "Leben niedrig -> heim"
    for e in state.get("enemies", []):
        if dist(p["x"], p["y"], e["x"], e["y"]) <= 1:
            return "attack", {"x": e["x"], "y": e["y"]}, f"greife {e['name']} an"
    return None


def missing_for(item, inventory, recipes):
    """Welches Material fehlt für ein Rezept? {Material: Anzahl}"""
    return {k: v - inventory.get(k, 0) for k, v in recipes.get(item, {}).items()
            if inventory.get(k, 0) < v}


def check_goal(goal, state, recipes):
    """Prüft, ob das Ziel vom LLM überhaupt sinnvoll ist. Gibt Fehlertext oder None."""
    z = goal.get("ziel")
    obj = goal.get("objekt")
    if z == "sammeln":
        names = {n["name"] for n in state.get("nearby", [])}
        if obj not in names:
            return f"'{obj}' ist nicht in der Nähe"
    elif z == "craften":
        if obj not in recipes:
            return f"kein Rezept für '{obj}'"
        missing = missing_for(obj, state.get("inventory", {}), recipes)
        if missing:
            return f"für {obj} fehlt {missing}"
    elif z not in ("heimkehren", "erkunden"):
        return f"unbekanntes Ziel '{z}'"
    return None


class Executor:
    """Setzt ein Ziel Schritt für Schritt in Befehle um."""

    def __init__(self, goal, state):
        self.goal = goal
        obj = goal.get("objekt")
        self.start_count = state.get("inventory", {}).get(obj, 0)
        self.done = False
        self.result = ""
        self.explore_target = None

    def step(self, state):
        """Gibt (action, fields) für den nächsten Befehl zurück, oder None wenn fertig."""
        g, p = self.goal, state["player"]
        inv = state.get("inventory", {})

        if g["ziel"] == "sammeln":
            obj, menge = g["objekt"], max(1, int(g.get("menge", 1)))
            if inv.get(obj, 0) - self.start_count >= menge:
                return self._finish(f"{menge}x {obj} gesammelt")
            targets = [n for n in state.get("nearby", []) if n["name"] == obj]
            if not targets:
                return self._finish(f"kein {obj} mehr in der Nähe")
            t = min(targets, key=lambda n: dist(p["x"], p["y"], n["x"], n["y"]))
            if dist(p["x"], p["y"], t["x"], t["y"]) <= 1:
                return "mine", {"x": t["x"], "y": t["y"]}
            return "move_to", {"x": t["x"], "y": t["y"]}

        if g["ziel"] == "craften":
            if self.done:
                return None
            self._finish(f"{g['objekt']} gecraftet")
            return "craft", {"item": g["objekt"]}

        if g["ziel"] == "heimkehren":
            h = state["home"]
            if dist(p["x"], p["y"], h["x"], h["y"]) == 0:
                return self._finish("zuhause")
            return "move_to", {"x": h["x"], "y": h["y"]}

        if g["ziel"] == "erkunden":
            if self.explore_target is None:
                # Ein Stück in eine zufällige Richtung laufen, um Neues zu sehen
                dx, dy = random.choice([(1, 0), (-1, 0), (0, 1), (0, -1), (1, 1), (-1, -1), (1, -1), (-1, 1)])
                self.explore_target = (p["x"] + dx * 8, p["y"] + dy * 8)
                return "move_to", {"x": self.explore_target[0], "y": self.explore_target[1]}
            return self._finish(f"erkundet bis ({p['x']},{p['y']})")

        return self._finish("unbekanntes Ziel")

    def _finish(self, text):
        self.done = True
        self.result = text
        return None
