# Attribution and licensing

## Geist

Geist is an April 2026 final-year project at Agni College of Technology. The final review credits Ragavi P for machine learning and preprocessing, Samuel KC for the backend and Flutter app, and Tarun M for hardware and Micro-ESPectre integration. Veni G supervised the project.

Geist's additions include the host activity-recognition service, the STFT and CNN training workflow, the Flask-SocketIO bridge and SQLite event history, and the Flutter dashboard.

## ESPectre

Geist was built from **Micro-ESPectre v2.6.0** by **Francesco Pace and ESPectre contributors**. GitHub's tag is `2.6.0` and points to commit `67a7992`. The derived Micro-ESPectre sources, utilities, browser tools, and original documentation retain their upstream GPL v3 terms and attribution. Changes for Geist include CSI collection and analysis adjustments, integration with the host classifier, and repository and setup updates made for publication. See the [ESPectre project](https://github.com/francescopace/espectre), its [2.6.0 release](https://github.com/francescopace/espectre/releases/tag/2.6.0), and the [GPL v3 text](LICENSE).

The board firmware used by the CLI comes from Francesco Pace's CSI-enabled MicroPython fork. `me` downloads the `v1.0.0-rc6` ESP32-S3 image and checks its SHA-256 digest. See the [firmware project and source](https://github.com/francescopace/micropython-esp32-csi) and its [RC6 release](https://github.com/francescopace/micropython-esp32-csi/releases/tag/v1.0.0-rc6).

The original Geist app, standalone bridge, and project-authored assets have no separate license grant in this snapshot. External dependencies retain their own terms.
