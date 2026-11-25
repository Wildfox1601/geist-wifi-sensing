# Geist Flutter dashboard

The Flutter dashboard is the Android companion for the April 2026 Geist prototype. It receives live activity from the Flask-SocketIO bridge and fetches fall history over HTTP. [Watch the 73-second Android walkthrough](../screenshots%20and%20captures/app_demo_walkthrough.mp4).

## Connect to the bridge

1. Start the [Geist bridge](../docs/setup.md#demo-without-an-esp32).
2. From this directory, run the app with an Android device or emulator selected.

   ```sh
   flutter pub get
   flutter run
   ```

3. Enter the bridge IP without a protocol or port. On a physical Android phone, use the host's LAN IP and bind the bridge to that address. On the standard Android emulator running on the same host, use `10.0.2.2` with the bridge bound to loopback. The app adds `http://` and port `5000`.
4. Enter an example email such as `demo@example.com` and any nonempty demo password. The screen validates that the fields are filled and saves the bridge IP locally.
5. Wait for **System Online** on Home, then start the [scripted publisher](../docs/setup.md#demo-without-an-esp32) or [live classifier](../docs/setup.md#live-sensing-with-an-esp32-s3).

## Home, Logs, and Config

| Screen | What to look for |
| --- | --- |
| **Home** | The live status card changes with each activity. The Sensors, Battery, and Connectivity cards display demo values. [See the walking and seated captures](../README.md#see-geist-in-action). |
| **Logs** | **Event History** shows up to 20 recent fall entries from `GET /api/logs`. Tap refresh to load the latest entries. |
| **Config** | In **Network Configuration**, save a new **Backend IP** and reopen the app to reconnect. Use **Open Learning Mode** to reach Teach Geist. |

<a href="../screenshots%20and%20captures/app_fall_alert.jpeg"><img src="../screenshots%20and%20captures/app_fall_alert.jpeg" width="220" alt="Android dashboard showing Critical Fall Detected and a manual Call 108 button"></a>

When the connected app receives a fall update, the status card turns red, the app requests a local Android notification, and a manual call button appears. Allow Geist notifications in Android settings to try the alert. The bridge records the update for Event History even if the dashboard is closed.

## Teach Geist

1. Start [live sensing](../docs/setup.md#live-sensing-with-an-esp32-s3) so the host receives CSI packets.
2. Open **Config → Open Learning Mode**. Name the activity, select a recording duration, and tap **Start Recording**. Perform the activity while the progress indicator advances.
3. After capture, **Retake** returns to the recording setup. **Train Model** uses the labeled recordings available on the host to build and load a new model. To keep the original activity classes in a retrain, include examples for each one.
4. Use the restore icon in the Teach Geist toolbar to load the host's backed-up model and labels.

The walkthrough demonstrates recording a custom activity, training on the host, and opening the restore prompt. [Read how the host handles training and restore](../docs/activity-recognition.md#teach-geist).
