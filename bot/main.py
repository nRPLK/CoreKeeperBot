"""Hauptschleife des Bots.  Start:  python bot\\main.py"""
import time

from brain import Executor, check_goal, missing_for, reflex
from game_link import GameLink
from planner import plan

MISSION = "Baue eine Werkbank. Danach sammle Erz, solange welches in der Nähe ist."
TICK = 0.2  # Sekunden pro Schleifendurchlauf


def repeats(history, goal):
    """Wie oft kam dasselbe Ziel in den letzten Einträgen vor?"""
    return sum(1 for h in history[-6:] if h.startswith(str(goal)))


def fallback(state):
    """Ersatzziel, wenn das Modell festhängt: Erz bevorzugt, sonst irgendwas, sonst erkunden."""
    names = [n["name"] for n in state.get("nearby", [])]
    for wish in ("Kupfererz", "Zinnerz"):
        if wish in names:
            return {"ziel": "sammeln", "objekt": wish, "menge": 3}
    if names:
        return {"ziel": "sammeln", "objekt": names[0], "menge": 3}
    return {"ziel": "erkunden"}


def main():
    link = GameLink()
    link.connect()
    state, recipes = None, {}
    executor, history = None, []
    rejected = 0

    while True:
        try:
            messages = link.receive()
        except (ConnectionError, OSError):
            print("[link] Verbindung verloren -> verbinde neu")
            link.connect()
            state, executor = None, None
            continue
        for msg in messages:
            if msg["type"] == "state":
                state = msg
            elif msg["type"] == "recipes":
                recipes = msg["recipes"]
                print(f"[spiel] {len(recipes)} Rezepte erhalten")
            elif msg["type"] == "event":
                print(f"[spiel] {msg['text']}")

        # Erst weitermachen, wenn das Spiel den letzten Befehl verarbeitet hat
        if state is None or state.get("last_cmd", 0) < link.last_id:
            time.sleep(TICK)
            continue

        # 1. Reflexe haben Vorrang
        r = reflex(state)
        if r:
            action, fields, why = r
            print(f"[reflex] {why}")
            link.send(action, **fields)
            time.sleep(TICK)
            continue

        if state.get("busy"):
            time.sleep(TICK)
            continue

        # 2. Kein Ziel -> Planer fragen
        if executor is None or executor.done:
            if executor is not None:
                history.append(f"{executor.goal} -> {executor.result}")
                print(f"[ziel] fertig: {executor.result}")
                executor = None
            t0 = time.time()
            try:
                goal = plan(state, recipes, MISSION, history)
            except Exception as exc:
                print(f"[planer] Fehler: {exc}  (läuft Ollama?)")
                time.sleep(5)
                continue
            error = check_goal(goal, state, recipes)
            print(f"[planer] {goal}  ({time.time() - t0:.1f} s)")
            if error and goal.get("ziel") == "craften" and repeats(history, goal) < 3:
                # Kleines Modell will zu früh craften -> fehlendes Material selbst holen
                need = missing_for(goal.get("objekt"), state.get("inventory", {}), recipes)
                near = {n["name"] for n in state.get("nearby", [])}
                for mat, count in need.items():
                    if mat in near:
                        print(f"[planer] {error} -> sammle zuerst {count}x {mat}")
                        history.append(f"{goal} -> umgeleitet: sammle {mat}")
                        goal, error = {"ziel": "sammeln", "objekt": mat, "menge": count}, None
                        break
                else:
                    if need and repeats(history, goal) < 2:
                        print(f"[planer] {error}, nichts davon in der Nähe -> erkunden")
                        history.append(f"{goal} -> umgeleitet: erkunden")
                        goal, error = {"ziel": "erkunden"}, None
            if error and goal.get("ziel") == "sammeln" and repeats(history, goal) < 2:
                # Gesuchtes ist nicht in Sichtweite -> suchen gehen statt ablehnen
                print(f"[planer] {error} -> erkunden")
                history.append(f"{goal} -> umgeleitet: erkunden")
                goal, error = {"ziel": "erkunden"}, None
            if error:
                print(f"[planer] abgelehnt: {error}")
                history.append(f"{goal} -> ungültig: {error}")
                rejected += 1
                if rejected >= 3:
                    # Modell hängt fest -> selbst etwas Sinnvolles tun
                    goal = fallback(state)
                    print(f"[planer] 3x ungültig -> Ersatzziel {goal}")
                    rejected = 0
                    executor = Executor(goal, state)
                    continue
                time.sleep(1)
                continue
            rejected = 0
            executor = Executor(goal, state)

        # 3. Ziel ausführen
        cmd = executor.step(state)
        if cmd:
            action, fields = cmd
            link.send(action, **fields)
        time.sleep(TICK)


if __name__ == "__main__":
    main()
