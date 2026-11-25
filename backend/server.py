import sqlite3
import os
from flask import Flask, jsonify
from flask_cors import CORS
from flask_socketio import SocketIO
from datetime import datetime
import json
import threading
import paho.mqtt.client as mqtt
import sys
from pathlib import Path

app = Flask(__name__)
CORS(app)
socketio = SocketIO(app, cors_allowed_origins="*", async_mode='threading', logger=True, engineio_logger=True)

# --- CONFIGURATION LINKING ---
# Automatically detect MQTT broker from your Geist config
root_path = Path(__file__).resolve().parents[1]
sys.path.append(str(root_path))
try:
    from src import config_local as geist_config
except ImportError:
    geist_config = None

MQTT_BROKER = os.environ.get("MQTT_BROKER", getattr(geist_config, "MQTT_BROKER", "127.0.0.1"))
MQTT_PORT = int(os.environ.get("MQTT_PORT", getattr(geist_config, "MQTT_PORT", 1883)))
MQTT_USERNAME = getattr(geist_config, "MQTT_USERNAME", "")
MQTT_PASSWORD = getattr(geist_config, "MQTT_PASSWORD", "")

MQTT_TOPIC = "home/espectre/node1"

# --- DATABASE SETUP ---
def init_db():
    conn = sqlite3.connect('geist.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS logs 
                 (id INTEGER PRIMARY KEY, event_type TEXT, timestamp TEXT)''')
    conn.commit()
    conn.close()

init_db()

def log_event(event_type):
    conn = sqlite3.connect('geist.db')
    c = conn.cursor()
    time_str = datetime.now().strftime("%b %d, %I:%M %p")
    c.execute("INSERT INTO logs (event_type, timestamp) VALUES (?, ?)", (event_type, time_str))
    conn.commit()
    conn.close()

# --- MQTT SETUP ---
def on_mqtt_connect(client, userdata, flags, rc):
    print(f"Connected to MQTT broker with result code {rc}")
    client.subscribe(MQTT_TOPIC)

def on_mqtt_message(client, userdata, msg):
    try:
        payload = msg.payload.decode('utf-8')
        data = json.loads(payload)
        state = data.get("state")
        
        # Forward learning states immediately
        if state in ["learning", "learning_done", "training", "training_done", "restore_done"]:
            socketio.emit('learning_update', data)
            return

        if state == "fall":
            print("AI: Fall detected! Triggering App Alarm.")
            socketio.emit('status_update', {'status': 'FALL', 'color': 'red'})
            log_event("Fall Detected")
        elif state == "walk":
            print("AI: Walk detected.")
            socketio.emit('status_update', {'status': 'WALK', 'color': 'yellow'})
        elif state == "sit":
            print("AI: Sit detected.")
            socketio.emit('status_update', {'status': 'SIT', 'color': 'blue'})
        elif state in ["empty", "idle"]:
            print("AI: Room Safe.")
            socketio.emit('status_update', {'status': 'EMPTY', 'color': 'green'})
        elif state not in ["learning", "learning_done", "training", "training_done", "restore_done"]:
            # Handle Custom Activities
            display_name = str(state).upper()
            print(f"AI: Custom Activity '{display_name}' detected.")
            socketio.emit('status_update', {'status': display_name, 'color': 'purple', 'is_custom': True})
    except Exception as e:
        print(f"Error parsing MQTT message: {e}")

mqtt_client = mqtt.Client()
if MQTT_USERNAME:
    mqtt_client.username_pw_set(MQTT_USERNAME, MQTT_PASSWORD)
mqtt_client.on_connect = on_mqtt_connect
mqtt_client.on_message = on_mqtt_message

def start_mqtt():
    try:
        mqtt_client.connect(MQTT_BROKER, MQTT_PORT, 60)
        mqtt_client.loop_forever()
    except Exception as e:
        print(f"MQTT Connection failed: {e}")

mqtt_thread = threading.Thread(target=start_mqtt, daemon=True)
mqtt_thread.start()

@app.route('/')
def index():
    return "Geist Bridge Backend (MQTT -> Flutter) Running!"

@app.route('/api/logs')
def get_logs():
    conn = sqlite3.connect('geist.db')
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    c.execute("SELECT * FROM logs ORDER BY id DESC LIMIT 20")
    rows = c.fetchall()
    conn.close()
    return jsonify([{"event": r["event_type"], "time": r["timestamp"]} for r in rows])

# --- SOCKET.IO COMMANDS FROM APP ---
@socketio.on('start_learning')
def handle_start_learning(data):
    print(f"App requested Learning Mode: {data}")
    mqtt_client.publish("home/espectre/node1/cmd", json.dumps({
        "cmd": "start_learning",
        "activity_name": data.get('activity_name', 'custom'),
        "duration": data.get('duration', 10)
    }))

@socketio.on('train_model')
def handle_train_model(data):
    print("App requested Model Training")
    mqtt_client.publish("home/espectre/node1/cmd", json.dumps({"cmd": "train_model"}))

@socketio.on('restore_model')
def handle_restore_model(data):
    print("App requested Model Restore")
    mqtt_client.publish("home/espectre/node1/cmd", json.dumps({"cmd": "restore_model"}))

if __name__ == '__main__':
    socketio.run(app, host=os.environ.get("GEIST_HOST", "127.0.0.1"), port=5000, debug=False, allow_unsafe_werkzeug=True)
