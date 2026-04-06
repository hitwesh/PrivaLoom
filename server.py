import numpy as np
from flask import Flask, request, jsonify
import threading

app = Flask(__name__)

# Core State from Spec
AGGREGATION_THRESHOLD = 20
global_weights = [np.random.randn(10, 10)] 
global_updates = []
round_number = 0
lock = threading.Lock()

@app.route('/get-weights', methods=['GET'])
def get_weights():
    return jsonify({"weights": [w.tolist() for w in global_weights], "round": round_number})

@app.route('/send-update', methods=['POST'])
def send_update():
    global global_updates, global_weights, round_number
    data = request.json
    incoming_weights = [np.array(w) for w in data.get('weights')]

    with lock:
        global_updates.append(incoming_weights)
        print(f"Update received. Buffer: {len(global_updates)}/{AGGREGATION_THRESHOLD}")

        if len(global_updates) >= AGGREGATION_THRESHOLD:
            # Autonomous Aggregation Logic
            print(f"Threshold reached! Aggregating Round {round_number}...")
            new_weights = []
            for i in range(len(global_weights)):
                layer_updates = [u[i] for u in global_updates]
                new_weights.append(np.mean(layer_updates, axis=0))
            
            global_weights = new_weights
            round_number += 1
            global_updates = []
            print(f"Round {round_number} started. Buffer cleared.")
            
    return jsonify({"status": "success", "round": round_number})

if __name__ == '__main__':
    app.run(port=5000, threaded=True)