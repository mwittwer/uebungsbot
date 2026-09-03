# Übungsbot

Ein Rollenspiel-Chatbot für Seminare. Teilnehmer bekommen einen Link, klicken drauf, chatten los —
kein Login, kein Datei-Upload, keine Einstellungen. Eine Persona = eine Markdown-Datei.

## Neue Persona anlegen

Datei unter `personas/<name>.md`, Aufbau:

```markdown
# Titel des Bots

Die Begrüßung, die der Teilnehmer als erstes sieht.
Darf mehrere Absätze haben.

---

Ab hier der System-Prompt. Sieht der Teilnehmer nie.
```

Die drei Bindestriche auf eigener Zeile trennen Begrüßung und System-Prompt. Committen, fertig —
der Bot ist dann unter `?bot=<name>` erreichbar.

## Deployment (Streamlit Community Cloud, kostenlos)

1. Repo zu GitHub pushen. **Ohne Key** — `.gitignore` hält `secrets.toml` draußen.
2. Auf [share.streamlit.io](https://share.streamlit.io) anmelden, *Create app*, Repo wählen,
   Main file path: `app.py`.
3. Unter *Settings → Secrets* eintragen:
   ```toml
   ANTHROPIC_API_KEY = "sk-ant-..."
   ```
4. Link pro Bot verteilen: `https://<deine-app>.streamlit.app/?bot=empathie`

Bei Anthropic ein Ausgabenlimit setzen — der Link ist offen, jeder Aufruf kostet Token.

## Anderswo hosten

Nichts hier ist an Streamlit Cloud gebunden. Es braucht nur einen **dauerhaft laufenden Prozess**
(Render, Fly.io, Railway, Docker, VPS) — nicht Serverless wie Vercel oder Cloudflare Workers,
weil Streamlit eine WebSocket-Verbindung offen hält.

```bash
pip install -r requirements.txt
export ANTHROPIC_API_KEY=sk-ant-...
streamlit run app.py
```

## Stellschrauben in `app.py`

| Konstante | Standard | Wozu |
|---|---|---|
| `MODEL` | `claude-opus-5` | `claude-sonnet-5` kostet $2/$10 statt $5/$25 pro 1M Token |
| `MAX_TURNS` | `40` | Wortwechsel pro Besucher, danach ist die Runde zu Ende |
| `MAX_TOKENS` | `2000` | Länge einer einzelnen Antwort |
| `DEFAULT_BOT` | `empathie` | welche Persona ohne `?bot=` in der URL läuft |

Der Effort steht auf `low` — für Dialog-Rollenspiel reicht das und hält Latenz und Kosten unten.
