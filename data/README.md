# CSI data

The Geist activity labels are `fall`, `idle`, `sit`, and `walk`. Keep each capture in the directory for its activity. The training workflow takes the label from that directory name and supports extra labels collected through Teach Geist.

| Path | Contents |
| --- | --- |
| `data/<label>/*.npz` | Recordings from `me collect` contain a `csi_data` array of raw in-phase and quadrature values and capture metadata. Teach Geist recordings use an `amplitudes` array with one averaged value per packet. |
| `data/dataset_info.json` | Capture index maintained by `me collect`. |
| `data/spectrograms/<label>/*.npy` | Generated `33 × 17` spectrograms. Each filename includes the source recording stem and the window index. |
| `data/visual_verification/*.png` | Sample plots written by the spectrogram visualizer. |

The generator skips recordings shorter than 300 packets and regenerates spectrograms for each input label directory. Keep the source recordings when you want to reproduce a training run. For an evaluation split, group all windows from the same original recording together.

Recordings and generated files are local. The live demo loads the bundled model directly, so it can run without a training dataset. [See the processing diagram and collection commands](../docs/activity-recognition.md).
