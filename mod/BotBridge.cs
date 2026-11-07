// BotBridge – Core-Keeper-Mod, der den Spielzustand per TCP (localhost:7777) an den Python-Bot schickt.
// Version 1: nur LESEN (Position + Blöcke in der Nähe). Befehle (laufen, abbauen) folgen in Version 2.
// Noch nicht kompiliert/getestet – die Spiel-APIs stammen aus den offiziellen SDK-Beispielen.
using System;
using System.Net;
using System.Net.Sockets;
using System.Text;
using System.Threading;
using PugMod;
using PugTilemap;
using Unity.Mathematics;
using UnityEngine;

public class BotBridge : IMod
{
    const int PORT = 7777;
    const float INTERVAL = 0.2f; // Sekunden zwischen zwei Zustands-Updates
    const int RADIUS = 8;        // Sichtweite in Kacheln

    readonly object gate = new object();
    string latestState;
    int stateVersion;
    float timer;

    TcpListener listener;
    Thread serverThread;
    volatile bool running;

    public void EarlyInit() { }

    public void Init()
    {
        running = true;
        serverThread = new Thread(ServerLoop) { IsBackground = true, Name = "BotBridge" };
        serverThread.Start();
        Debug.Log("[BotBridge] gestartet, warte auf Bot auf Port " + PORT);
    }

    public void ModObjectLoaded(UnityEngine.Object obj) { }

    public void Shutdown()
    {
        running = false;
        try { listener?.Stop(); } catch { }
    }

    // Läuft im Haupt-Thread des Spiels: hier dürfen wir Spieldaten lesen.
    public void Update()
    {
        timer += Time.deltaTime;
        if (timer < INTERVAL) return;
        timer = 0f;

        if (Manager.main == null || Manager.main.player == null || Manager.multiMap == null)
            return; // Hauptmenü oder Welt lädt noch

        try
        {
            var player = Manager.main.player;
            var pos = player.WorldPosition;          // Spielwelt: x/z ist die Ebene
            int px = (int)math.round(pos.x);
            int py = (int)math.round(pos.z);

            var lookup = Manager.multiMap.GetTileLayerLookup();
            var sb = new StringBuilder(4096);
            sb.Append("{\"type\":\"state\",\"player\":{\"x\":").Append(px)
              .Append(",\"y\":").Append(py).Append("},\"nearby\":[");

            bool first = true;
            for (int dx = -RADIUS; dx <= RADIUS; dx++)
            {
                for (int dy = -RADIUS; dy <= RADIUS; dy++)
                {
                    var tile = lookup.GetTopTile(new int2(px + dx, py + dy));
                    if (tile.tileType == TileType.none) continue;
                    if (!TileTypeUtility.IsBlockingTile(tile.tileType)) continue; // nur Wände/Erz usw.
                    if (!first) sb.Append(',');
                    first = false;
                    sb.Append("{\"name\":\"").Append(tile.tileType.ToString())
                      .Append("\",\"x\":").Append(px + dx)
                      .Append(",\"y\":").Append(py + dy).Append('}');
                }
            }
            sb.Append("]}");

            lock (gate)
            {
                latestState = sb.ToString();
                stateVersion++;
            }
        }
        catch (Exception e)
        {
            Debug.LogWarning("[BotBridge] Fehler beim Lesen: " + e.Message);
        }
    }

    // Läuft in einem eigenen Thread: Netzwerk, damit das Spiel nie wartet.
    void ServerLoop()
    {
        try
        {
            listener = new TcpListener(IPAddress.Loopback, PORT);
            listener.Start();
        }
        catch (Exception e)
        {
            Debug.LogError("[BotBridge] Port " + PORT + " nicht verfügbar: " + e.Message);
            return;
        }

        while (running)
        {
            TcpClient client = null;
            try
            {
                client = listener.AcceptTcpClient();
                Debug.Log("[BotBridge] Bot verbunden");
                var stream = client.GetStream();
                int sentVersion = -1;
                while (running && client.Connected)
                {
                    string msg = null;
                    lock (gate)
                    {
                        if (stateVersion != sentVersion && latestState != null)
                        {
                            msg = latestState;
                            sentVersion = stateVersion;
                        }
                    }
                    if (msg != null)
                    {
                        var bytes = Encoding.UTF8.GetBytes(msg + "\n");
                        stream.Write(bytes, 0, bytes.Length);
                    }
                    Thread.Sleep(20);
                }
            }
            catch (Exception)
            {
                // Bot hat getrennt -> auf nächste Verbindung warten
            }
            finally
            {
                client?.Close();
                Debug.Log("[BotBridge] Bot getrennt");
            }
        }
    }
}
