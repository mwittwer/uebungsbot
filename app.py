"""Übungsbot — ein Chat pro Persona, öffentlicher Link, kein Login.

Jede Persona ist eine Markdown-Datei in personas/. Der Link zum Bot ist
    <app-url>/?bot=<dateiname-ohne-endung>
"""

import os
import pathlib
import re

import anthropic
import streamlit as st

MODEL = "claude-opus-5"      # Kosten senken: "claude-sonnet-5" ($2/$10 statt $5/$25 pro 1M Token)
MAX_TURNS = 40               # Kostenbremse: Wortwechsel pro Besucher-Session
MAX_TOKENS = 2000            # Rollenspiel-Antworten sind kurz
PERSONA_DIR = pathlib.Path(__file__).parent / "personas"
DEFAULT_BOT = "empathie"
SAFE_SLUG = re.compile(r"[a-zA-Z0-9_-]+")


# --- Persona laden ------------------------------------------------------------
def load_persona(slug: str):
    """Liest personas/<slug>.md: H1 = Titel, danach Begrüßung, nach '---' der System-Prompt.

    `slug` kommt aus der URL und ist damit fremde Eingabe: erst gegen ein enges
    Muster prüfen, dann verifizieren, dass der aufgelöste Pfad wirklich in
    PERSONA_DIR liegt — sonst liest ?bot=../../etc/hostname fremde Dateien aus.
    """
    if not SAFE_SLUG.fullmatch(slug):
        raise FileNotFoundError(slug)
    target = (PERSONA_DIR / f"{slug}.md").resolve()
    if not target.is_file() or PERSONA_DIR.resolve() not in target.parents:
        raise FileNotFoundError(slug)
    text = target.read_text(encoding="utf-8")
    head, separator, system = text.partition("\n---\n")
    if not separator:
        raise ValueError(f"'{slug}.md' hat keine '---'-Trennlinie zwischen Begrüßung und System-Prompt.")
    lines = head.strip().splitlines()
    title = lines[0].lstrip("#").strip() if lines and lines[0].startswith("#") else slug
    greeting = "\n".join(lines[1:]).strip()
    if not greeting:
        raise ValueError(f"'{slug}.md' enthält keine Begrüßung zwischen Überschrift und '---'.")
    return title, greeting, system.strip()


@st.cache_resource(show_spinner=False)
def get_client():
    key = os.environ.get("ANTHROPIC_API_KEY")
    if not key:
        try:
            key = st.secrets["ANTHROPIC_API_KEY"]
        except Exception:
            key = None
    if not key:
        raise RuntimeError("ANTHROPIC_API_KEY fehlt — in den Streamlit-Secrets hinterlegen.")
    return anthropic.Anthropic(api_key=key)


slug = st.query_params.get("bot", DEFAULT_BOT)
try:
    title, greeting, persona_system = load_persona(slug)
except FileNotFoundError:
    available = sorted(p.stem for p in PERSONA_DIR.glob("*.md"))
    st.error(f"Diesen Bot gibt es nicht: `{slug}`")
    st.caption("Verfügbar: " + (", ".join(f"`{a}`" for a in available) or "— keine Persona hinterlegt —"))
    st.stop()
except ValueError as e:
    st.error(str(e))
    st.stop()

# Die Messages-API verlangt, dass die erste Nachricht die Rolle "user" hat. Die
# Begrüßung wird deshalb nur angezeigt und dem Modell über den System-Prompt
# mitgegeben — nicht als messages[0] geschickt.
SYSTEM_PROMPT = (
    f"{persona_system}\n\n"
    f"Du hast den Dialog bereits mit dieser Nachricht eröffnet:\n\n{greeting}\n\n"
    "Die erste Nachricht deines Gegenübers ist bereits die Antwort darauf. "
    "Begrüße also nicht noch einmal und wiederhole die Eröffnung nicht."
)


# --- Oberfläche ---------------------------------------------------------------
st.set_page_config(page_title=title, page_icon="💬")
st.markdown(
    "<style>#MainMenu{visibility:hidden}footer{visibility:hidden}</style>",
    unsafe_allow_html=True,
)

if st.session_state.get("bot") != slug:          # Botwechsel per URL = frischer Start
    st.session_state.bot = slug
    st.session_state.messages = []

for message in st.session_state.messages:
    st.chat_message(message["role"]).markdown(message["content"])
if not st.session_state.messages:
    st.chat_message("assistant").markdown(greeting)


# --- Dialog -------------------------------------------------------------------
if len(st.session_state.messages) >= MAX_TURNS * 2:
    st.info("Diese Übungsrunde ist zu Ende.")
    if st.button("Neue Runde starten"):
        st.session_state.messages = []
        st.rerun()
    st.stop()

if user_input := st.chat_input("Deine Antwort …"):
    st.session_state.messages.append({"role": "user", "content": user_input})
    st.chat_message("user").markdown(user_input)

    try:
        with st.chat_message("assistant"):
            with get_client().messages.stream(
                model=MODEL,
                max_tokens=MAX_TOKENS,
                output_config={"effort": "low"},   # kurzer Dialog, kein Grübeln nötig
                system=SYSTEM_PROMPT,
                messages=st.session_state.messages,
            ) as stream:
                reply = st.write_stream(stream.text_stream)
        st.session_state.messages.append({"role": "assistant", "content": reply})
    except anthropic.RateLimitError:
        st.session_state.messages.pop()
        st.warning("Gerade sind zu viele Anfragen unterwegs. Bitte kurz warten und noch einmal senden.")
    except anthropic.APIStatusError as e:
        st.session_state.messages.pop()
        st.error("Der Bot ist im Moment nicht erreichbar. Bitte gib der Seminarleitung Bescheid.")
        st.caption(f"Technisch: {e.status_code}")
    except anthropic.APIConnectionError:
        st.session_state.messages.pop()
        st.warning("Verbindung zum Bot unterbrochen. Bitte noch einmal senden.")
