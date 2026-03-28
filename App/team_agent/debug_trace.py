import streamlit as st

st.set_page_config(layout="wide")

if "events" not in st.session_state:
    st.session_state.events = []

tab1, tab2 = st.tabs(["Chat", "Log"])

with tab1:
    prompt = st.chat_input("type anything")
    if prompt:
        # Simuler un run
        st.session_state.events = [
            {"ts": "10:00:00", "kind": "agent_start", "agent": "planner"},
            {"ts": "10:00:01", "kind": "llm_call",    "agent": "planner"},
        ]
        st.write(f"Saved {len(st.session_state.events)} events before rerun")
        st.rerun()  # <- rerun depuis DANS with tab1

    st.write(f"events in tab1: {len(st.session_state.events)}")

with tab2:
    st.write(f"Events in tab2: {len(st.session_state.events)}")
    for e in st.session_state.events:
        st.write(e)
