"""Publish scripted activity states for the hardware-free Geist demo."""

import argparse
import json
import time

import paho.mqtt.client as mqtt


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--broker", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=1883)
    args = parser.parse_args()

    client = mqtt.Client()
    client.connect(args.broker, args.port, 60)
    client.loop_start()
    try:
        for state, delay in (("empty", 3), ("walk", 3), ("sit", 3), ("fall", 5), ("empty", 0)):
            print(f"Simulating {state}", flush=True)
            message = client.publish("home/espectre/node1", json.dumps({"state": state}), qos=1)
            message.wait_for_publish()
            time.sleep(delay)
    finally:
        client.disconnect()
        client.loop_stop()


if __name__ == "__main__":
    main()
