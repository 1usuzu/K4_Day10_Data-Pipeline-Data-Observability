import os
import warnings
import streamlit as st
from pathlib import Path

# Suppress warnings
warnings.filterwarnings("ignore", category=UserWarning, module="huggingface_hub")

from core.config import load_settings, require_llm_credentials
from retrieval.index import LocalEmbeddingIndex
from retrieval.agent import build_agent, run_agent_question

# ==========================================
# PAGE CONFIGURATION & CUSTOM CSS
# ==========================================
st.set_page_config(page_title="Agentic AI - Research Assistant", page_icon="🔮", layout="wide")

st.markdown("""
<style>
    /* Dark Mode Premium Theme with Glassmorphism */
    .stApp {
        background: linear-gradient(135deg, #0f172a 0%, #1e1b4b 100%);
        color: #f8fafc;
        font-family: 'Inter', sans-serif;
    }
    
    /* Hide Streamlit branding */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {background: transparent !important;}

    /* Chat Message Styling */
    .stChatMessage {
        background: rgba(255, 255, 255, 0.03) !important;
        border: 1px solid rgba(255, 255, 255, 0.05);
        border-radius: 16px;
        padding: 1.5rem;
        margin-bottom: 1rem;
        backdrop-filter: blur(10px);
        -webkit-backdrop-filter: blur(10px);
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06);
        transition: transform 0.2s ease, box-shadow 0.2s ease;
    }
    .stChatMessage:hover {
        transform: translateY(-2px);
        box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.3);
        border: 1px solid rgba(99, 102, 241, 0.3);
    }
    
    /* User Message distinct styling */
    [data-testid="chatAvatarIcon-user"] {
        background: linear-gradient(135deg, #3b82f6 0%, #2dd4bf 100%);
    }
    /* Assistant Message distinct styling */
    [data-testid="chatAvatarIcon-assistant"] {
        background: linear-gradient(135deg, #8b5cf6 0%, #ec4899 100%);
    }
    
    /* Title glowing effect */
    .glow-title {
        font-size: 3rem !important;
        font-weight: 800 !important;
        text-align: center;
        background: linear-gradient(135deg, #60a5fa 0%, #c084fc 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        margin-bottom: 0.5rem;
        text-shadow: 0 0 30px rgba(192, 132, 252, 0.3);
    }
    
    .subtitle {
        text-align: center;
        color: #94a3b8;
        font-size: 1.1rem;
        margin-bottom: 3rem;
        font-weight: 500;
    }
    
    /* Chat Input Styling */
    .stChatInputContainer {
        border-radius: 20px !important;
        background: rgba(15, 23, 42, 0.6) !important;
        border: 1px solid rgba(148, 163, 184, 0.2) !important;
        backdrop-filter: blur(12px);
    }
    .stChatInputContainer:focus-within {
        border: 1px solid #8b5cf6 !important;
        box-shadow: 0 0 20px rgba(139, 92, 246, 0.3) !important;
    }
</style>
""", unsafe_allow_html=True)

st.markdown('<h1 class="glow-title">🔮 Agentic RAG Explorer</h1>', unsafe_allow_html=True)
st.markdown('<p class="subtitle">Chat with your academic papers using OpenRouter & ChromaDB</p>', unsafe_allow_html=True)

# ==========================================
# INITIALIZATION & STATE
# ==========================================
@st.cache_resource(show_spinner=False)
def initialize_system():
    settings = load_settings()
    require_llm_credentials(settings)
    
    if settings.paths.repaired_embeddings_json.exists():
        index_path = settings.paths.repaired_embeddings_json
        index_type = "REPAIRED"
    elif settings.paths.embeddings_json.exists():
        index_path = settings.paths.embeddings_json
        index_type = "BASELINE"
    else:
        raise FileNotFoundError("No vector index found! Please run phase 1 first.")
        
    index = LocalEmbeddingIndex.load(settings, index_path)
    agent = build_agent(settings, index)
    return agent, index_type

if "messages" not in st.session_state:
    st.session_state.messages = []

try:
    with st.spinner("🚀 Initializing AI Core..."):
        agent, loaded_index_type = initialize_system()
        if "init_toast" not in st.session_state:
            st.toast(f"Connected to **{loaded_index_type}** database successfully!", icon="✅")
            st.session_state.init_toast = True
except Exception as e:
    st.error(f"Failed to initialize system: {str(e)}")
    st.stop()

# ==========================================
# CHAT INTERFACE
# ==========================================
# Display chat messages from history on app rerun
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# React to user input
if prompt := st.chat_input("Ask a question about the papers..."):
    # Display user message in chat message container
    st.chat_message("user").markdown(prompt)
    # Add user message to chat history
    st.session_state.messages.append({"role": "user", "content": prompt})

    # Display assistant response in chat message container
    with st.chat_message("assistant"):
        message_placeholder = st.empty()
        with st.spinner("🤖 Analyzing documents & synthesizing answer..."):
            try:
                response = run_agent_question(agent, prompt)
                message_placeholder.markdown(response)
                st.session_state.messages.append({"role": "assistant", "content": response})
            except Exception as e:
                error_msg = f"**Error processing request:** {str(e)}"
                message_placeholder.error(error_msg)
                st.session_state.messages.append({"role": "assistant", "content": error_msg})
