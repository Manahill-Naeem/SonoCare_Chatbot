from flask import Flask, request, jsonify
import os
from dotenv import load_dotenv
from ultrasound import streamlit_run_agent

load_dotenv()

app = Flask(__name__)

@app.route('/')
def home():
    return """
    <html>
        <head>
            <title>SonoCare Chatbot</title>
            <style>
                body { font-family: Arial, sans-serif; margin: 40px; }
                .container { max-width: 800px; margin: 0 auto; }
                .chat-box { border: 1px solid #ccc; padding: 20px; margin: 20px 0; }
                input[type="text"] { width: 70%; padding: 10px; }
                button { padding: 10px 20px; background: #007bff; color: white; border: none; cursor: pointer; }
                .response { margin: 10px 0; padding: 10px; background: #f8f9fa; }
            </style>
        </head>
        <body>
            <div class="container">
                <h1>🩺 SonoCare Chatbot</h1>
                <p>Ask questions about your ultrasound reports here.</p>
                
                <div class="chat-box">
                    <input type="text" id="userInput" placeholder="Write your question here..." />
                    <button onclick="sendMessage()">Send</button>
                    <div id="chatHistory"></div>
                </div>
            </div>
            
            <script>
                async function sendMessage() {
                    const input = document.getElementById('userInput');
                    const message = input.value.trim();
                    if (!message) return;
                    
                    // Add user message
                    addMessage('user', message);
                    input.value = '';
                    
                    try {
                        const response = await fetch('/chat', {
                            method: 'POST',
                            headers: { 'Content-Type': 'application/json' },
                            body: JSON.stringify({ message: message })
                        });
                        
                        const data = await response.json();
                        addMessage('assistant', data.response);
                    } catch (error) {
                        addMessage('assistant', 'Sorry, there was an error processing your request.');
                    }
                }
                
                function addMessage(role, content) {
                    const history = document.getElementById('chatHistory');
                    const div = document.createElement('div');
                    div.className = 'response';
                    div.innerHTML = `<strong>${role === 'user' ? 'You' : 'Assistant'}:</strong> ${content}`;
                    history.appendChild(div);
                    history.scrollTop = history.scrollHeight;
                }
                
                // Enter key support
                document.getElementById('userInput').addEventListener('keypress', function(e) {
                    if (e.key === 'Enter') {
                        sendMessage();
                    }
                });
            </script>
        </body>
    </html>
    """

@app.route('/chat', methods=['POST'])
def chat():
    try:
        data = request.get_json()
        user_message = data.get('message', '')
        
        if not user_message:
            return jsonify({'error': 'No message provided'}), 400
        
        # Get response from the agent
        response_text, audio_data = streamlit_run_agent(user_message, use_voice=False)
        
        return jsonify({
            'response': response_text,
            'audio_available': audio_data is not None
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/health')
def health():
    return jsonify({'status': 'healthy'})

if __name__ == '__main__':
    app.run(debug=True)
