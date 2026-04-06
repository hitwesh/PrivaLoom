import requests
import time
import numpy as np
import argparse

parser = argparse.ArgumentParser()
parser.add_argument("--id", type=str, required=True)
args = parser.parse_args()

URL = "http://127.0.0.1:5000"

def run_client():
    while True:
        # 1. Get current model
        res = requests.get(f"{URL}/get-weights").json()
        current_round = res['round']
        weights = [np.array(w) for w in res['weights']]
        
        print(f"Client {args.id} training for Round {current_round}...")
        time.sleep(1) # Simulate local work
        
        # 2. Simulate training (add noise)
        updated = [w + (np.random.randn(*w.shape) * 0.01) for w in weights]
        
        # 3. Send back
        requests.post(f"{URL}/send-update", json={
            "client_id": args.id,
            "weights": [w.tolist() for w in updated]
        })
        
        # 4. Wait for next round
        print(f"Client {args.id} waiting for next round...")
        while True:
            if requests.get(f"{URL}/get-weights").json()['round'] > current_round:
                break
            time.sleep(2)

if __name__ == "__main__":
    run_client()