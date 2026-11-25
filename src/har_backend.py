"""
Geist - HAR Real-Time Backend (PC-Side)
Integrated with Stability Filtering and Custom Learning Mode.
"""

import sys, time, json, numpy as np, tensorflow as tf
import re
import subprocess
from scipy import signal
from pathlib import Path
from collections import deque
import paho.mqtt.client as mqtt
import threading

root_path = Path(__file__).parent.parent
sys.path.append(str(root_path))
sys.path.append(str(root_path / 'src'))
from tools.csi_utils import CSIReceiver, DEFAULT_SUBCARRIERS
import src.config_local as config

MODEL_PATH = root_path / 'models' / 'har_model.tflite'
PARAMS_PATH = root_path / 'models' / 'har_model_params.json'
WINDOW_SIZE = 300 
INFERENCE_INTERVAL = 25 # Run inference every 0.25s

N_FFT, N_PER_SEG, N_OVERLAP = 64, 32, 16

class HARBackend:
    def __init__(self):
        print("Initializing HAR Backend (Stability Filter & Learning Mode active)...")
        self.backup_model()
        with open(PARAMS_PATH, 'r') as f: self.params = json.load(f)
        self.labels = self.params['labels']
        self.interpreter = tf.lite.Interpreter(model_path=str(MODEL_PATH))
        self.interpreter.allocate_tensors()
        self.input_details, self.output_details = self.interpreter.get_input_details(), self.interpreter.get_output_details()
        
        # MQTT Setup
        self.mqtt_client = mqtt.Client()
        if config.MQTT_USERNAME: self.mqtt_client.username_pw_set(config.MQTT_USERNAME, config.MQTT_PASSWORD)
        self.mqtt_topic = "home/espectre/node1"
        self.cmd_topic = "home/espectre/node1/cmd"
        self.mqtt_client.connect(config.MQTT_BROKER, config.MQTT_PORT, 60)
        self.mqtt_client.on_message = self.on_mqtt_command
        self.mqtt_client.subscribe(self.cmd_topic)

        # Buffers & Receiver
        self.amplitude_buffer = deque(maxlen=WINDOW_SIZE)
        self.prediction_history = deque(maxlen=5)
        self.receiver = CSIReceiver(port=5001, buffer_size=WINDOW_SIZE)
        self.receiver.add_callback(self.on_packet)
        self.packet_count, self.current_state = 0, "idle"
        
        # Learning Mode State
        self.is_learning = False
        self.is_training = False
        self.learning_label = ""
        self.learning_data = []
        self.learning_count = 0
        self.learning_target = 0
        self.mqtt_client.loop_start()

    def backup_model(self):
        import shutil
        backup_path = Path(str(MODEL_PATH).replace(".tflite", "_backup.tflite"))
        backup_params = Path(str(PARAMS_PATH).replace(".json", "_backup.json"))
        if not backup_path.exists() and MODEL_PATH.exists():
            shutil.copy(MODEL_PATH, backup_path)
            print("Created original model backup.")
        if not backup_params.exists() and PARAMS_PATH.exists():
            shutil.copy(PARAMS_PATH, backup_params)

    def generate_spectrogram(self, amplitudes):
        amplitudes_detrended = amplitudes - np.mean(amplitudes)
        _, _, Sxx = signal.spectrogram(amplitudes_detrended, fs=100, nperseg=N_PER_SEG, noverlap=N_OVERLAP, nfft=N_FFT)
        Sxx_log = 10 * np.log10(Sxx + 1e-10)
        s_min, s_max = np.min(Sxx_log), np.max(Sxx_log)
        if s_max - s_min > 1e-6: return ((Sxx_log - s_min) / (s_max - s_min)).astype(np.float32)
        return np.zeros_like(Sxx_log).astype(np.float32)

    def on_mqtt_command(self, client, userdata, msg):
        try:
            data = json.loads(msg.payload.decode())
            cmd = data.get("cmd")
            if cmd == "start_learning":
                label = data.get("activity_name", "custom_task").lower().replace(" ", "_")
                duration = int(data.get("duration", 10))
                if not re.fullmatch(r"[a-z0-9][a-z0-9_-]*", label) or not 3 <= duration <= 60:
                    return
                self.start_learning_mode(label, duration)
            elif cmd == "train_model":
                threading.Thread(target=self.trigger_retraining).start()
            elif cmd == "restore_model":
                self.restore_model()
        except Exception as e:
            print(f"Command Error: {e}")

    def start_learning_mode(self, label, duration_sec):
        print(f"!!! STARTING LEARNING MODE: {label.upper()} for {duration_sec}s !!!")
        self.is_learning = True
        self.learning_label = label
        self.learning_data = []
        self.learning_target = duration_sec * 100 
        self.learning_count = 0
        
        self.mqtt_client.publish(self.mqtt_topic, json.dumps({
            "state": "learning", 
            "progress": 0,
            "message": f"Recording {label}..."
        }))

    def on_packet(self, packet):
        val = np.mean(packet.amplitudes[DEFAULT_SUBCARRIERS])
        
        if self.is_learning or self.is_training:
            if self.is_learning:
                self.learning_data.append(val)
                self.learning_count += 1
                if self.learning_count % 50 == 0:
                    progress = int((self.learning_count / self.learning_target) * 100)
                    self.mqtt_client.publish(self.mqtt_topic, json.dumps({
                        "state": "learning", "progress": progress
                    }))
                
                if self.learning_count >= self.learning_target:
                    self.finish_learning()
            return

        self.amplitude_buffer.append(val)
        self.packet_count += 1
        if self.packet_count % INFERENCE_INTERVAL == 0 and len(self.amplitude_buffer) == WINDOW_SIZE:
            self.run_inference()

    def finish_learning(self):
        self.is_learning = False
        print(f"Collection complete for {self.learning_label}. Saving data...")
        save_dir = Path(root_path / "data" / self.learning_label)
        save_dir.mkdir(parents=True, exist_ok=True)
        timestamp = time.strftime("%Y%m%d_%H%M%S")
        filename = save_dir / f"custom_{self.learning_label}_{timestamp}.npz"
        np.savez(filename, amplitudes=np.array(self.learning_data))
        
        self.mqtt_client.publish(self.mqtt_topic, json.dumps({
            "state": "learning_done", 
            "message": "Data saved. Ready to train model."
        }))

    def trigger_retraining(self):
        try:
            self.is_training = True
            print("Starting AI Retraining Pipeline...")
            self.mqtt_client.publish(self.mqtt_topic, json.dumps({"state": "training", "message": "Training AI (This takes ~30s)..."}))
            subprocess.run([sys.executable, "tools/12_generate_spectrograms.py"], cwd=root_path, check=True)
            result = subprocess.run([sys.executable, "tools/15_train_har_cnn.py", "--epochs", "10"], cwd=root_path)
            if result.returncode == 0:
                print("Retraining finished. Hot-swapping model...")
                self.reload_model()
                self.mqtt_client.publish(self.mqtt_topic, json.dumps({
                    "state": "training_done", "message": "New activity learned successfully!"
                }))
            else:
                print(f"Training script failed with code {result.returncode}")
                self.mqtt_client.publish(self.mqtt_topic, json.dumps({
                    "state": "training_done", "message": "Training failed (Check terminal)."
                }))
        except Exception as e:
            print(f"Retraining error: {e}")
            self.mqtt_client.publish(self.mqtt_topic, json.dumps({
                "state": "training_done", "message": f"Error: {e}"
            }))
        finally:
            self.is_training = False

    def restore_model(self):
        import shutil
        print("Restoring original model...")
        backup_path = Path(str(MODEL_PATH).replace(".tflite", "_backup.tflite"))
        backup_params = Path(str(PARAMS_PATH).replace(".json", "_backup.json"))
        if backup_path.exists(): shutil.copy(backup_path, MODEL_PATH)
        if backup_params.exists(): shutil.copy(backup_params, PARAMS_PATH)
        
        self.reload_model()
        self.mqtt_client.publish(self.mqtt_topic, json.dumps({
            "state": "restore_done", "message": "Restored to original ML model."
        }))

    def reload_model(self):
        try:
            if hasattr(self, 'interpreter'):
                del self.interpreter
            time.sleep(0.5) 
            self.interpreter = tf.lite.Interpreter(model_path=str(MODEL_PATH))
            self.interpreter.allocate_tensors()
            self.input_details = self.interpreter.get_input_details()
            self.output_details = self.interpreter.get_output_details()
            with open(PARAMS_PATH, 'r') as f: self.params = json.load(f)
            self.labels = self.params['labels']
            print(f"Model reloaded successfully. Labels: {self.labels}")
        except Exception as e:
            print(f"Reload Error: {e}")

    def run_inference(self):
        spec = self.generate_spectrogram(np.array(self.amplitude_buffer))
        self.interpreter.set_tensor(self.input_details[0]['index'], spec[np.newaxis, ..., np.newaxis])
        self.interpreter.invoke()
        output_data = self.interpreter.get_tensor(self.output_details[0]['index'])[0]
        class_idx = np.argmax(output_data)
        confidence = float(output_data[class_idx])
        raw_label = self.labels[class_idx]
        
        self.prediction_history.append(raw_label)
        counts = {l: list(self.prediction_history).count(l) for l in self.labels}
        
        if counts.get('fall', 0) >= 2:
            self.current_state = 'fall'
        elif counts.get('walk', 0) >= 3:
            self.current_state = 'walk'
        elif counts.get('sit', 0) >= 4 and confidence > 0.8:
            self.current_state = 'sit'
        elif counts.get('idle', 0) >= 3:
            self.current_state = 'idle'
        else:
            # Check for any custom label majority
            for label in self.labels:
                if label not in ['fall', 'walk', 'sit', 'idle'] and counts.get(label, 0) >= 3:
                    self.current_state = label
                    break
            else:
                # If no clear majority, keep current state but update label if high confidence
                if confidence > 0.9: self.current_state = raw_label

        display_label = self.current_state.upper()
        payload = {
            "state": self.current_state, 
            "display_state": display_label,
            "confidence": confidence, 
            "probabilities": {self.labels[i]: float(output_data[i]) for i in range(len(self.labels))}, 
            "timestamp": time.time()
        }
        self.mqtt_client.publish(self.mqtt_topic, json.dumps(payload))
        print(f"Activity: {display_label} ({confidence*100:.1f}%)")

    def run(self):
        print(f"Backend running (Stability Filter ON). Port 5001...")
        try: self.receiver.run()
        except KeyboardInterrupt: print("Shutting down...")

if __name__ == "__main__":
    backend = HARBackend()
    backend.run()
