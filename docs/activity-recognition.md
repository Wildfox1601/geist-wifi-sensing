# Activity recognition

## From CSI to a prediction

The ESP32-S3 associates with a 2.4 GHz access point and streams CSI samples to the host on UDP 5001. Each sample contains in-phase and quadrature values for Wi-Fi subcarriers. Taking the magnitude gives an amplitude for each subcarrier. When someone moves, changes to the paths that Wi-Fi signals take through the room can change those amplitudes across successive packets.

| Step | What the checked-in classifier does |
| --- | --- |
| Select and average | Averages amplitudes from subcarrier indices 11 through 22 to produce one value per packet. |
| Window and transform | Takes the latest 300 values, subtracts their mean, and computes a short-time Fourier transform (STFT) with 32-sample segments, 16-sample overlap, and a 64-point FFT. |
| Scale | Converts spectrogram power to decibels, then applies per-window min-max scaling. The result is a `33 × 17` array of frequency bins by time steps. |
| Classify | Runs the TensorFlow Lite CNN every 25 received packets after the window fills. A stability filter uses up to five recent labels to help select the published state. |
| Publish | Sends the selected state and the latest model probabilities over MQTT. The bridge sends the state to Flutter and writes each received fall message to SQLite. |

At the nominal 100 packets per second, the first window takes about three seconds to fill and the classifier evaluates another window about every quarter-second. Both intervals depend on packet arrival. A single sustained fall prediction can produce several event rows because each fall message is logged.

### Original processing design

<a href="../screenshots%20and%20captures/CSI%20Data%20Processing%20Pipeline.png"><img src="../screenshots%20and%20captures/CSI%20Data%20Processing%20Pipeline.png" width="360" alt="Original CSI design diagram showing Butterworth and Hampel filtering before spectrogram generation, CNN inference, and a Flask alert"></a>

The design illustration includes Butterworth and Hampel filtering. The checked-in host classifier uses the subcarrier averaging and spectrogram preprocessing described above. Micro-ESPectre's standalone detector has its own filtering, moving variance segmentation (MVS), and normalized band variance index (NBVI) calibration. [Read the upstream algorithms guide](upstream/ALGORITHMS.md).

## Bundled model

The [TensorFlow Lite checkpoint](../models/har_model.tflite) comes from the project's four-class backup. The [matching label file](../models/har_model_params.json) maps its four outputs in the following order.

| Index | Model label | Flutter dashboard |
| --- | --- | --- |
| 0 | `fall` | **CRITICAL FALL DETECTED** |
| 1 | `idle` | **IDLE** |
| 2 | `sit` | **Subject Seated** |
| 3 | `walk` | **Subject Walking** |

The archived final-review files pair four model outputs with five labels, including jumping. Use the bundled checkpoint and label file together for the documented demo. [See the dashboard captures](../README.md#see-geist-in-action).

## Collect and train

Use the [live sensing setup](setup.md#live-sensing-with-an-esp32-s3), then stop the host classifier while `me collect` listens on UDP 5001. Keep the ESP32 stream running. This example records walking samples.

```sh
python me collect --label walk --duration 5 --samples 20 --interactive
```

Repeat collection for each class you want the model to learn. The bundled labels are `fall`, `idle`, `sit`, and `walk`. Use separate recordings for each repetition and make sure each recording contains at least 300 packets. The collector and Teach Geist write `.npz` files in two supported formats. [See the data layout](../data/README.md).

Generate the spectrograms and train the model from the repository root.

```sh
python tools/12_generate_spectrograms.py
python tools/15_train_har_cnn.py --epochs 30
```

The generator steps through each recording 20 packets at a time and saves one spectrogram per 300-packet window. The trainer adds a single input channel, fits a CNN with two convolution and pooling stages, and exports `models/har_model.tflite` and `models/har_model_params.json` together. It also saves `models/har_model.h5` for local use. Training overwrites the active model files. Save the model and label file together before retraining to preserve a checkpoint. Restart the host classifier after command-line training to load the new pair. [See the inspection and training tools](../tools/README.md#geist-activity-recognition).

### Teach Geist

With the live classifier running, **Teach Geist** records a named activity from incoming CSI. One recording can produce multiple overlapping spectrograms. **Train Model** regenerates spectrograms from the host's available captures, runs the trainer for 10 epochs, and loads the exported pair after successful training. Collect examples for every class you want the retrained model to keep. **Restore Original Model** loads the backup pair created by the host on its first run with the active files. [Open the Android walkthrough](../app/README.md#teach-geist).

## April 2026 final review

The April 9 final review reported CNN accuracy above 80% and end-to-end latency below 500 ms for the prototype. These are historical, team-reported figures. The archived materials do not establish independent validation for the published checkpoint. The training script splits overlapping windows after segmentation, so related windows from one recording can appear in both training and validation. A recording-level or room-level split would be needed to assess how well the model generalizes.

The original slide deck and presentation script are kept in the local project archive because they include student identifiers. The presentation's references to on-device processing describe the broader design. In the archived demo code the ESP32 captures CSI and the host performs CNN inference.

The review cites work by Sankalp Dayal, Hirokazu Narui, and Paraskevas Deligiannis as the project's research starting point. [Human Fall Detection in Indoor Environments Using Channel State Information of Wi‑Fi Signals](https://cs229.stanford.edu/proj2016/report/NaruiDayalDeligiannis-HumanFallDetectionUsingWiFi-report.pdf)
