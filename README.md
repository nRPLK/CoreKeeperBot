# CoreKeeperBot

> **EN:** An AI agent that plays the game *Core Keeper*. A C# mod streams the game state over TCP, a Python agent reacts with rule-based reflexes, and a small local LLM (Ollama, `qwen2.5:3b-instruct`) plans long-term goals – all running offline on a laptop with integrated graphics.

KI-Bot für Core Keeper: Ein Mod liest den Spielzustand aus, ein Python-Agent entscheidet, ein lokales LLM (Ollama) plant die Ziele.

```
Core Keeper + Mod (C#)  <-- TCP localhost:7777, JSON-Zeilen -->  Python-Bot
                                                                  ├─ Reflexe (Regeln, sofort)
                                                                  ├─ Ausführung (Ziel -> Befehle)
                                                                  └─ Planer (Ollama, qwen2.5:3b-instruct)
```

## Stand
- [x] Python-Bot: Verbindung, Reflexe, Ausführung, Planer
- [x] Testspiel `fake_game.py` (simuliert den Mod, damit man ohne Spiel testen kann)
- [~] C#-Mod `mod/BotBridge.cs` v1: sendet Position + Blöcke (noch ungetestet), Test mit `python bot\mod_probe.py`
- [ ] Mod v2: Befehle ausführen (laufen, abbauen, craften)

## Testen ohne Spiel
Nur Python-Standardbibliothek, kein `pip install` nötig.

Terminal 1:
```
python bot\fake_game.py
```
Terminal 2:
```
python bot\main.py
```
Ollama muss laufen (läuft normalerweise automatisch im Hintergrund).

## Protokoll
Siehe `PROTOKOLL.md`. Der echte Mod muss genau dieses Protokoll sprechen, dann funktioniert der Bot ohne Änderungen mit dem echten Spiel.

## Hinweis
Nur in eigenen Welten / Singleplayer verwenden.

## Was ich dabei gelernt habe
- Agenten-Architektur: schnelle Regeln (Reflexe) + langsamer LLM-Planer getrennt
- Ein eigenes Netzwerkprotokoll entwerfen (TCP, JSON-Zeilen, Befehls-IDs gegen veraltete Zustände)
- Lokale LLMs mit Ollama einbinden und auf schwacher Hardware nutzbar machen (~1 s pro Planung)
- Testen ohne das echte Spiel über eine Simulation (`fake_game.py`)

## Lizenz
MIT – siehe `LICENSE`.
