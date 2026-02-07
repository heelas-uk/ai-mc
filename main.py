from openai import OpenAI
import streamlit as st
import base64
import logging
import sys
import pathlib

# Log to stderr so errors appear in the terminal where Streamlit runs
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
    handlers=[logging.StreamHandler(sys.stderr)],
) 

st.set_page_config(page_title="MINECRAFT Legal Assistant", page_icon="⚖️")

# Minecraft dark theme (concise, high-contrast)
st.markdown(
    """
    <style>
    /* Root */
    :root, html, body, .stApp, .main, .block-container { background: #0b1220 !important; color: #e6eef8 !important; color-scheme: dark !important; }

    /* Header / toolbar */
    header, [data-testid="stToolbar"] { background: #07101a !important; border-bottom: 1px solid #0f1a24 !important; }

    /* Title */
    .title { color: #a3f39d !important; font-weight: 700; font-family: monospace; }

    /* Buttons and inputs */
    button, .stButton>button, input, textarea, .stTextInput, .stTextArea, .stFileUploader { background: #07101a !important; color: #e6eef8 !important; border: 1px solid #23303e !important; }
    ::placeholder { color: #9fb3c6 !important; opacity: 1 !important; }

    /* Chat boxes and expanders */
    .stMessage, .stChatMessage, .stExpander, .st-expander { background: #07101a !important; color: #e6eef8 !important; border: 1px solid #162229 !important; }

    /* Images */
    .stImage img { background: #07101a !important; border-radius: 6px !important; }

    /* Links */
    a { color: #7ee787 !important; }
    </style>
    """,
    unsafe_allow_html=True,
)

st.title("⚖️ MINECRAFT Legal Assistant")
st.caption("Official server legal assistant — concise, lawful, and Minecraft-focused.")

client = OpenAI(
    api_key=st.secrets["HACK_CLUB_AI_API_KEY"],
    base_url="https://ai.hackclub.com/proxy/v1"
)

# Search functionality removed — system prompt is loaded from `law.md` and used as server rules.


# Defaults
if "openai_model" not in st.session_state:
    st.session_state["openai_model"] = "moonshotai/kimi-k2.5"

# Hidden system prompt (loaded from `law.md` if available)
try:
    law_path = pathlib.Path(__file__).parent / "law.md"
    if law_path.exists():
        with law_path.open("r", encoding="utf-8") as f:
            laws_text = f.read().strip()
        DEFAULT_SYSTEM_PROMPT = (
            "You are a helpful assistant for a Minecraft server. Use the following server laws to inform your answers and moderate behavior:\n\n"
            + laws_text
            + "\n\nAnswer concisely, be friendly, and avoid unnecessary verbosity."
        )
    else:
        DEFAULT_SYSTEM_PROMPT = (
            "You are a helpful assistant. Answer concisely, be friendly, and avoid unnecessary verbosity."
        )
except Exception:
    logging.exception("Failed to read law.md")
    DEFAULT_SYSTEM_PROMPT = (
        "You are a helpful assistant. Answer concisely, be friendly, and avoid unnecessary verbosity."
    )

if "system_prompt" not in st.session_state:
    st.session_state["system_prompt"] = DEFAULT_SYSTEM_PROMPT

# Top controls and server laws (sidebar removed)
st.subheader("Settings & Server Laws")
st.markdown("**System prompt is read-only.** Edit `law.md` and click **Reload laws** to update the assistant's rules.")

btn_col1, btn_col2 = st.columns(2)
with btn_col1:
    if st.button("Reload laws", key="reload_laws_main"):
        try:
            law_path = pathlib.Path(__file__).parent / "law.md"
            if law_path.exists():
                with law_path.open("r", encoding="utf-8") as f:
                    st.session_state["system_prompt"] = f.read().strip()
                st.success("Reloaded laws into system prompt.")
            else:
                st.error("`law.md` not found in workspace.")
        except Exception:
            logging.exception("Failed to reload `law.md`")
            st.error("Failed to reload laws — check terminal for details.")

with btn_col2:
    if st.button("Clear chat", key="clear_chat_main"):
        st.session_state.messages = []

with st.expander("Server Laws ⚖️ (from law.md)", expanded=False):
    st.markdown(st.session_state.get("system_prompt", "(no laws loaded)"))

if "messages" not in st.session_state:
    st.session_state.messages = []

# Render chat messages inside a styled container
for message in st.session_state.messages:
    with st.container():
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

# Image uploader (optional)
uploaded_image = st.file_uploader("Upload an image (optional) — PNG/JPG/GIF", type=["png","jpg","jpeg","gif"], key="uploaded_image")
if uploaded_image:
    st.image(uploaded_image, caption=uploaded_image.name)
    st.caption("You can send this image with or without a text prompt.")
    if st.button("Send image"):
        img = uploaded_image
        bytes_data = img.getvalue()
        b64 = base64.b64encode(bytes_data).decode()
        image_markdown = f"![{img.name}](data:{img.type};base64,{b64})"
        st.session_state.messages.append({"role":"user","content": image_markdown})
        with st.chat_message("user"):
            st.image(bytes_data)

        with st.chat_message("assistant"):
            # Build messages with the system prompt loaded from `law.md` (if present)
            messages_for_api = [
                {"role": "system", "content": st.session_state["system_prompt"]},
                *[
                    {"role": m["role"], "content": m["content"]}
                    for m in st.session_state.messages
                ],
            ]
            try:
                stream = client.chat.completions.create(
                    model=st.session_state["openai_model"],
                    messages=messages_for_api,
                    stream=True,
                )
                response = st.write_stream(stream)
            except Exception as e:
                # Log full traceback to stderr (terminal)
                logging.exception("Chat API error while sending image")
                st.error("Error: failed to send image — check terminal for details.")
                response = "Error: failed to get response from model."

        st.session_state.messages.append({"role":"assistant","content": response})
        # Do not modify widget-backed session state for the uploader here; the uploader keeps its value until the user clears it.

# Chat input with friendlier placeholder
if prompt := st.chat_input("Ask me anything — press Enter to send..."):
    content = prompt
    # If the uploader currently has a file selected, include it. We read the uploader widget value directly
    # rather than attempting to mutate any widget-backed session state.
    if uploaded_image:
        img = uploaded_image
        bytes_data = img.getvalue()
        b64 = base64.b64encode(bytes_data).decode()
        image_markdown = f"![{img.name}](data:{img.type};base64,{b64})"
        content = content + "\n\n" + image_markdown
        # The uploader widget retains its selected file until the user clears it; we do not attempt to reset it programmatically.

    st.session_state.messages.append({"role":"user","content": content})
    with st.chat_message("user"):
        st.markdown(prompt)
        if "data:" in content:
            try:
                st.image(bytes_data, use_column_width=True)
            except Exception:
                pass

    with st.chat_message("assistant"):
        # Build messages with the system prompt loaded from `law.md` (if present)
        messages_for_api = [
            {"role": "system", "content": st.session_state["system_prompt"]},
            *[
                {"role": m["role"], "content": m["content"]}
                for m in st.session_state.messages
            ],
        ]
        try:
            stream = client.chat.completions.create(
                model=st.session_state["openai_model"],
                messages=messages_for_api,
                stream=True,
            )
            response = st.write_stream(stream)
        except Exception as e:
            logging.exception("Chat API error while handling prompt")
            st.error("Error: failed to get response — check terminal for details.")
            response = "Error: failed to get response from model."

    st.session_state.messages.append({"role": "assistant", "content": response})