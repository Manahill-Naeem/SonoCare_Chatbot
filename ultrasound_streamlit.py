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

# Handle new user input
if prompt := st.chat_input("Write your question here..."):
    # Add user message to chat history
    st.session_state.chat_history.append({"role": "user", "content": prompt})

    # Display user's message
    with st.chat_message("user"):
        st.markdown(prompt)

    # Get the bot's response from the streamlit_run_agent function
    with st.spinner("Preparing response..."):
        response_text = streamlit_run_agent(prompt)
        
    # Add bot's response to chat history
    st.session_state.chat_history.append({"role": "assistant", "content": response_text})

    # Display bot's response
    with st.chat_message("assistant"):
        st.markdown(response_text)