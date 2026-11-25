"""
Geist - Robust Spectrogram Generation (3s Window)

Optimized for 5-second interactive samples. 
Uses a 3-second sliding window to maximize training data from short bursts.
Updated to automatically discover new classes and support both raw and pre-processed data formats.
"""

import os
import sys
import numpy as np
from scipy import signal
from pathlib import Path

def setup_paths():
    root_path = Path(__file__).parent.parent
    if str(root_path) not in sys.path: sys.path.insert(0, str(root_path))
    if str(root_path / 'src') not in sys.path: sys.path.insert(0, str(root_path / 'src'))

setup_paths()
from tools.csi_utils import load_npz_as_packets, DEFAULT_SUBCARRIERS

# Parameters
WINDOW_SIZE_PACKETS = 300  # 3 seconds @ 100Hz (Better for data density)
STEP_PACKETS = 20          # 0.2 second steps (High overlap for more data)

N_FFT = 64
N_PER_SEG = 32
N_OVERLAP = 16

DATA_DIR = Path(__file__).parent.parent / 'data'
SPECTROGRAM_DIR = DATA_DIR / 'spectrograms'

def generate_spectrogram(amplitudes, fs=100):
    amplitudes_detrended = amplitudes - np.mean(amplitudes)
    _, _, Sxx = signal.spectrogram(amplitudes_detrended, fs=fs, nperseg=N_PER_SEG, noverlap=N_OVERLAP, nfft=N_FFT)
    Sxx_log = 10 * np.log10(Sxx + 1e-10)
    s_min, s_max = np.min(Sxx_log), np.max(Sxx_log)
    if s_max - s_min > 1e-6:
        return ((Sxx_log - s_min) / (s_max - s_min)).astype(np.float32)
    return np.zeros_like(Sxx_log).astype(np.float32)

def process_file(file_path, label):
    print(f"Processing {file_path.name}...")
    try:
        data = np.load(file_path)
        
        # Check if it's the new format (pre-averaged amplitudes) or old raw format
        if 'amplitudes' in data:
            mean_amp = data['amplitudes']
        elif 'csi_data' in data:
            csi_raw = data['csi_data']
            Q, I = csi_raw[:, 0::2].astype(float), csi_raw[:, 1::2].astype(float)
            mean_amp = np.mean(np.sqrt(I**2 + Q**2)[:, DEFAULT_SUBCARRIERS], axis=1)
        else:
            print(f"  Skipping {file_path.name}: No recognized data keys found.")
            return
        
        num_packets = len(mean_amp)
        if num_packets < WINDOW_SIZE_PACKETS:
            print(f"  Skipping {file_path.name}: Too short ({num_packets} pkts)")
            return

        output_count = 0
        for start in range(0, num_packets - WINDOW_SIZE_PACKETS + 1, STEP_PACKETS):
            spec = generate_spectrogram(mean_amp[start:start+WINDOW_SIZE_PACKETS])
            np.save(SPECTROGRAM_DIR / label / f"{file_path.stem}_spec_{output_count}.npy", spec)
            output_count += 1
        print(f"  Generated {output_count} samples.")
    except Exception as e: print(f"  Error processing {file_path.name}: {e}")

def main():
    SPECTROGRAM_DIR.mkdir(exist_ok=True)
    
    # Automatically find all subdirectories in DATA_DIR that are not spectrograms or baseline
    EXCLUDE_DIRS = ['baseline', 'spectrograms', 'visual_verification', 'unused']
    all_labels = [d.name for d in DATA_DIR.iterdir() if d.is_dir() and d.name not in EXCLUDE_DIRS]
    
    print(f"Found activity classes: {all_labels}")
    
    for label in all_labels:
        (SPECTROGRAM_DIR / label).mkdir(exist_ok=True)
        # Clear old spectrograms for this label
        for f in (SPECTROGRAM_DIR / label).glob("*.npy"): f.unlink()
        
        label_dir = DATA_DIR / label
        if label_dir.exists():
            for npz_file in label_dir.glob("*.npz"): 
                process_file(npz_file, label)

if __name__ == "__main__":
    main()
