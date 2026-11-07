"""Planer: fragt das lokale LLM (Ollama) nach dem nächsten Ziel."""
import json
import urllib.request

OLLAMA_URL = "http://localhost:11434/api/chat"
MODEL = "qwen2.5:3b-instruct"

SYSTEM = """Du bist der Planer eines Bots im Spiel Core Keeper.
Du bekommst Inventar, Rezepte und was in der Nähe ist.
Wähle GENAU EIN nächstes Ziel. Nutze nur Rezepte und Objekte aus den Daten, erfinde nichts.
Craften geht NUR mit Dingen aus "jetzt_craftbar". Fehlt Material ("fehlt_fuer"), sammle zuerst genau dieses Material.
Wiederhole kein Ziel, das in "letzte_ziele" als ungültig markiert ist.
Mögliche Ziele:
- {"ziel": "sammeln", "objekt": "<Name aus nearby>", "menge": <Zahl>}
- {"ziel": "craften", "objekt": "<Name aus Rezepte>"}
- {"ziel": "erkunden"}   (wenn das Gesuchte nicht in der Nähe ist)
- {"ziel": "heimkehren"}
Crafte nichts, was in "schon_gebaut" steht, außer die Mission verlangt mehrere davon.
Antworte nur mit JSON."""

SCHEMA = {
    "type": "object",
    "properties": {
        "ziel": {"type": "string", "enum": ["sammeln", "craften", "erkunden", "heimkehren"]},
        "objekt": {"type": "string"},
        "menge": {"type": "integer"},
        "grund": {"type": "string"},
    },
    "required": ["ziel"],
}


def plan(state, recipes, mission, history):
    from brain import missing_for
    inv = state.get("inventory", {})
    nearby_names = sorted({n["name"] for n in state.get("nearby", [])})
    missing = {item: missing_for(item, inv, recipes) for item in recipes}
    user = {
        "mission": mission,
        "inventar": inv,
        "rezepte": recipes,
        "schon_gebaut": [i for i in recipes if inv.get(i, 0) > 0],
        "jetzt_craftbar": [i for i, m in missing.items() if not m],
        "fehlt_fuer": {i: m for i, m in missing.items() if m},
        "in_der_naehe": nearby_names,
        "letzte_ziele": history[-5:],
    }
    body = {
        "model": MODEL,
        "messages": [
            {"role": "system", "content": SYSTEM},
            {"role": "user", "content": json.dumps(user, ensure_ascii=False)},
        ],
        "format": SCHEMA,
        "stream": False,
        "keep_alive": "30m",
        "options": {"temperature": 0.2},
    }
    req = urllib.request.Request(
        OLLAMA_URL,
        data=json.dumps(body).encode("utf-8"),
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=60) as resp:
        answer = json.loads(resp.read())["message"]["content"]
    return json.loads(answer)
