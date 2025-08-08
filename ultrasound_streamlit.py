import streamlit as st
import time
from ultrasound import streamlit_run_agent

# Streamlit UI setup
st.set_page_config(page_title="Ultrasound Chatbot", page_icon="🩺")
st.title("Ultrasound Chatbot 🩺")
st.markdown("You can ask questions about your ultrasound reports here.")

# Initialize chat history in session state
if "chat_history" not in st.session_state:
    st.session_state.chat_history = []

# Display old chat history
for message in st.session_state.chat_history:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# Add a toggle for the voice assistant
enable_voice = st.toggle("Enable Voice Assistant", value=False)

# Handle new user input
if prompt := st.chat_input("Write your question here..."):
    # Add user message to chat history
    st.session_state.chat_history.append({"role": "user", "content": prompt})

    # Display user's message
    with st.chat_message("user"):
        st.markdown(prompt)

    # Get the bot's response and audio from the agent
    with st.spinner("Preparing response..."):
        response_text, audio_data = streamlit_run_agent(prompt, use_voice=enable_voice)
        
    # Add bot's response to chat history
    st.session_state.chat_history.append({"role": "assistant", "content": response_text})

    # Display bot's response and play audio if available
    with st.chat_message("assistant"):
        st.markdown(response_text)
        if audio_data:
            st.audio(audio_data, format="audio/l16", sample_rate=24000)
