# Protokoll Mod <-> Bot

- Verbindung: TCP, `127.0.0.1:7777`. Der **Mod ist der Server**, der Bot verbindet sich.
- Jede Nachricht ist **eine Zeile JSON**, abgeschlossen mit `\n` (UTF-8).

## Spiel -> Bot

### `state` (ca. 5x pro Sekunde)
```json
{
  "type": "state",
  "player": {"x": 12, "y": -4, "hp": 85, "hp_max": 100},
  "home": {"x": 0, "y": 0},
  "inventory": {"Holz": 3, "Kupfererz": 0},
  "nearby": [{"name": "Kupfererz", "x": 15, "y": -2}],
  "enemies": [{"name": "Schleim", "x": 14, "y": -4, "hp": 20}],
  "busy": false,
  "last_cmd": 41
}
```
- `busy` = der Spieler führt gerade noch einen Befehl aus (läuft, baut ab ...).
- `last_cmd` = `id` des zuletzt verarbeiteten Befehls. Der Bot entscheidet erst neu, wenn `last_cmd` seinen letzten Befehl erreicht hat (sonst würde er mit veraltetem Zustand doppelt craften usw.).

### `recipes` (einmal nach dem Verbinden)
```json
{"type": "recipes", "recipes": {"Werkbank": {"Holz": 8}}}
```

### `event` (optional)
```json
{"type": "event", "text": "Werkbank gecraftet"}
```

## Bot -> Spiel: Befehle

| action    | Felder        | Bedeutung                              |
|-----------|---------------|----------------------------------------|
| `move_to` | `x`, `y`      | zur Position laufen                    |
| `mine`    | `x`, `y`      | Block an Position abbauen (daneben stehen) |
| `attack`  | `x`, `y`      | in Richtung Position angreifen         |
| `craft`   | `item`        | Gegenstand craften                     |
| `wait`    | –             | nichts tun                             |

```json
{"type": "cmd", "id": 42, "action": "mine", "x": 15, "y": -2}
```
