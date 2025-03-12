from flask import Flask, request, jsonify, send_file
from flask_socketio import SocketIO, join_room, emit
from flask_cors import CORS
from openai import OpenAI
import os
# import os
# os.environ["OPENAI_API_KEY"] = "sk-*****"

client = OpenAI()
app = Flask(__name__)
CORS(app)
socketio = SocketIO(app, cors_allowed_origins="*")  # Allow CORS for testing if needed

# Global dictionary to hold voting options per room.
options = {}

# Default route for testing
@app.route('/')
def index():
    return send_file('SprintNamebot.html')

# API endpoint to generate sprint name suggestions
@app.route('/generate', methods=['POST'])
def generate():
    data = request.get_json()
    letter = data.get('letter', 'A')
    topic = data.get('topic', 'unusual measurement units')
    content = data.get('content', 'please give me the top 3 sprint name suggestions for sprint A')
    prompt = f"""You are a creative assistant helping a group of engineers choose distinctive sprint names based on the theme {topic}. 
    For the current sprint, which is sprint {letter}, please generate several sprint name suggestions that all begin with the letter {letter}. 
    For each suggestion, provide:
    1. A sprint name starting with {letter}.
    2. A short explanation detailing how the name relates to the theme {topic} and why it is a fitting choice.
    Ensure every suggestion strictly adheres to these requirements.
    Besides, please provide explanations if the user provides their own naming suggestions."""

    completion = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "developer", "content": prompt},
            {
                "role": "user",
                "content": content
            }
        ]
    )
    return jsonify(completion.choices[0].message.content)

# Socket.IO event: Client connection
@socketio.on('connect')
def on_connect():
    print("Client connected:", request.sid)
    emit('status', {'msg': 'Connected to the server'})

# Socket.IO event: Client disconnection
@socketio.on('disconnect')
def on_disconnect():
    print("Client disconnected:", request.sid)

# Socket.IO event: Join a session/room
@socketio.on('join')
def on_join(data):
    username = data.get('username', 'Anonymous')
    room = data.get('room', 'default')
    join_room(room)
    emit('status', {'msg': f'{username} has joined the room.'}, room=room)

@socketio.on('chat')
def handle_chat(data):
    username = data.get('username', 'Anonymous')
    message = data.get('message', '')
    room = data.get('room', 'default')  # Optionally get the room if you're using one.
    # Broadcast the message to all clients in the room
    emit('chat', message, room=room, include_self=False)
    # Or broadcast to all connected clients regardless of room:
    # emit('chat', {'username': username, 'message': message}, broadcast=True)

# Anonymous Voting Events

@socketio.on('add_option')
def handle_add_option(data):
    room = data.get('room', 'default')
    text = data.get('text')
    if room not in options:
        options[room] = []
    # Add a new option with 0 votes.
    options[room].append({"text": text, "votes": 0})
    print(f"Option added in room {room}: {text}")
    emit('option_update', {'options': options[room]}, room=room)

@socketio.on('vote_option')
def handle_vote_option(data):
    room = data.get('room', 'default')
    index = data.get('index')
    if room in options and 0 <= index < len(options[room]):
        options[room][index]['votes'] += 1
        print(f"Option voted in room {room}: {options[room][index]['text']} now has {options[room][index]['votes']} votes")
    emit('option_update', {'options': options.get(room, [])}, room=room)

@socketio.on('clear_options')
def handle_clear_options(data):
    room = data.get('room', 'default')
    options[room] = []
    print(f"Options cleared in room {room}")
    emit('option_update', {'options': []}, room=room)

@socketio.on('clear_votes')
def handle_clear_votes(data):
    room = data.get('room', 'default')
    if room in options:
        # Reset the vote count for each option in the room.
        for option in options[room]:
            option['votes'] = 0
    print(f"Votes cleared in room {room}")
    emit('option_update', {'options': options.get(room, [])}, room=room)

if __name__ == '__main__':
    # Run the application using SocketIO's run method.
    socketio.run(app, port=12345, debug=True, allow_unsafe_werkzeug=True)