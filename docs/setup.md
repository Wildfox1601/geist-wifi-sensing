# Run Geist

The scripted demo exercises the dashboard and event log with just a host computer and an Android device or emulator. Live sensing adds an ESP32-S3 and runs the bundled classifier on the host.

| Component | Scripted demo | Live sensing |
| --- | --- | --- |
| Host computer | Python 3.12 and Mosquitto | Same, plus the device CLI and inference dependencies in `requirements.txt` |
| Android dashboard | Flutter with Dart 3.10.7 or a compatible newer Dart 3 release, Android SDK, and JDK 17 | Same |
| Sensing hardware | — | ESP32-S3, USB data cable, and a 2.4 GHz Wi-Fi network |

Run host commands from the repository root. Use a separate terminal for each long-running process and activate the same Python environment in each terminal that runs a Python command.

## Demo without an ESP32

1. Create a Python environment and install the bridge dependencies.

   ```sh
   python3.12 -m venv .venv
   source .venv/bin/activate
   python -m pip install -r backend/requirements.txt
   ```

   On Windows PowerShell, use `py -3.12 -m venv .venv` and `.\.venv\Scripts\Activate.ps1`.

2. Start the Mosquitto broker. The supplied configuration listens on loopback at TCP port 1883.

   ```sh
   mosquitto -c backend/mosquitto.conf
   ```

3. Activate the same environment in a new terminal and start the bridge.

   ```sh
   python backend/server.py
   ```

   The bridge defaults to `127.0.0.1:5000`. To reach it from a physical phone, put the phone and host on the same trusted LAN and bind the server to the host's LAN address. Replace `192.0.2.10` with that address.

   ```sh
   GEIST_HOST=192.0.2.10 python backend/server.py
   ```

   In PowerShell, set `$env:GEIST_HOST = '192.0.2.10'` before starting the bridge. An Android Studio emulator on the same host can use `10.0.2.2` with the loopback binding. The app communicates over plain HTTP and Socket.IO, and the bridge has no authentication. Keep it on a trusted network.

4. Launch the [Flutter dashboard](../app/README.md). Once connected, run the demo publisher in another terminal with the same environment active.

   ```sh
   python backend/simulate.py
   ```

   The publisher sends one sequence and exits. The dashboard should show **IDLE**, **Subject Walking**, **Subject Seated**, **CRITICAL FALL DETECTED**, and then **IDLE** again. The fall state lasts about five seconds. [See the dashboard states](../README.md#see-geist-in-action).

5. Open **Logs** and tap refresh to verify a new **Fall Detected** entry. The same history is available from the bridge. Use the address you bound the bridge to if you changed it from loopback.

   ```sh
   curl http://127.0.0.1:5000/api/logs
   ```

   The bridge writes entries to `geist.db` in its working directory and returns the 20 most recent entries, newest first. Replaying the simulator adds another entry.

If you already have a local `src/config_local.py`, the bridge reads its broker settings. Set `MQTT_BROKER` and `MQTT_PORT` in the server environment to override the address and port if needed. The simulator accepts `--broker` and `--port`. Use the same broker for both processes. The supplied simulator and broker configuration use anonymous local MQTT.

## Live sensing with an ESP32-S3

1. Install the device CLI and inference dependencies into the same environment.

   ```sh
   python -m pip install -r requirements.txt
   if [ ! -e src/config_local.py ]; then
       cp src/config_local.py.example src/config_local.py
   fi
   ```

   On PowerShell, use `Copy-Item src/config_local.py.example src/config_local.py` if you need to create the local file. Set `WIFI_SSID` and `WIFI_PASSWORD` to your 2.4 GHz network credentials. The host services can use the template's loopback MQTT settings when Mosquitto runs on the same computer.

2. Connect the board over USB. Flash the CSI-enabled MicroPython image if the board needs it, then deploy the project sources and check the installation.

   ```sh
   python me flash --chip s3
   python me deploy
   python me verify
   ```

   Add `--port` and the serial device if autodetection needs help, such as `/dev/ttyACM0` on Linux or `COM4` on Windows. The CLI caches the downloaded firmware in `firmware/`. Flashing writes new firmware to the selected board.

3. Keep Mosquitto, the bridge, and the app running. Start the host activity classifier in another terminal.

   ```sh
   python -m src.har_backend
   ```

4. Stream CSI from the board to the host. Replace `192.0.2.10` with the host's LAN IPv4 address.

   ```sh
   python me stream --ip 192.0.2.10
   ```

   The ESP32 sends CSI to UDP 5001. Stop the simulator during live sensing so the dashboard receives only classifier output. Once the classifier has received its first 300 packets, look for `Activity:` messages in its terminal and matching updates on the dashboard. The [room demonstration](../screenshots%20and%20captures/project_demo.mp4) shows what the live path looks like.

### Prototype hardware

| Enclosure closed | Enclosure open |
| --- | --- |
| <img src="../screenshots%20and%20captures/geist_box_prototype.jpg" width="320" alt="Closed white Geist prototype enclosure with a USB cable"> | <img src="../screenshots%20and%20captures/geist_box_prototype2.jpg" width="320" alt="Open Geist prototype enclosure showing a USB-connected development board"> |

The two views show the prototype enclosure and the USB-connected sensing board inside it. During setup, keep USB connected so the device CLI can deploy and start the streamer. For repeatable comparisons, keep the board and access point in fixed positions while collecting or comparing recordings.

### Upstream motion detector

For the standalone upstream motion detector, use `python me run` with a broker address reachable from the ESP32. The inherited monitor and theremin require an MQTT broker with a WebSocket listener, as described in the [original Micro-ESPectre guide](https://github.com/francescopace/espectre/blob/2.6.0/micro-espectre/README.md).

## Connections and troubleshooting

| Connection | Default | What to check |
| --- | --- | --- |
| Simulator or classifier → broker → bridge | TCP `127.0.0.1:1883` | Start Mosquitto before the Python services. The bridge should report MQTT connection result `0`. |
| ESP32-S3 → host classifier | UDP `5001` | Pass the host's LAN IPv4 address to `me stream --ip`. If no `Activity:` lines appear, check the board's Wi-Fi connection and stream output, then check whether the host firewall allows UDP 5001 from the board. |
| Android app → bridge | HTTP and Socket.IO on TCP `5000` | Use `10.0.2.2` in the standard Android emulator with a loopback-bound bridge. For a physical phone, use the host's LAN address in the app and bind the bridge to that address. Allow TCP 5000 from the phone if the host firewall blocks it. |

- If the phone stays on **Connecting…**, open `http://<host-ip>:5000/` in the phone browser. A reachable bridge returns a short running message. Check that both devices are on a LAN that allows them to reach each other.
- If the bridge is reachable and the dashboard stays on its initial status, check the MQTT connection and rerun the simulator after the app connects. **System Online** indicates the app connected to the bridge.
- If events appear in the API but the Logs tab shows an older list, use its refresh button.

## Tests

Run `python -m pytest tests` from the root after installing `requirements.txt`. Tests that depend on historical upstream captures skip when those files are absent. Run `flutter test` from `app/` after fetching Flutter dependencies.
