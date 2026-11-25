"""
Geist - Spectrogram Visualizer

Loads .npy spectrogram files and saves them as PNG images for visual verification.
This helps ensure the captured CSI data contains visible motion signatures.

Author: Gemini CLI (Geist Project)
License: GPLv3
"""

import numpy as np
import matplotlib.pyplot as plt
from pathlib import Path
import random

DATA_DIR = Path(__file__).parent.parent / 'data'
SPECTROGRAM_DIR = DATA_DIR / 'spectrograms'
VISUAL_DIR = DATA_DIR / 'visual_verification'

def visualize_samples(n_samples=3):
    """Pick random samples from each label and save them as images."""
    VISUAL_DIR.mkdir(exist_ok=True)
    
    labels = [d.name for d in SPECTROGRAM_DIR.iterdir() if d.is_dir()]
    
    if not labels:
        print("No spectrogram directories found.")
        return

    for label in labels:
        label_dir = SPECTROGRAM_DIR / label
        files = list(label_dir.glob("*.npy"))
        
        if not files:
            continue
            
        print(f"Visualizing {label}...")
        selected_files = random.sample(files, min(len(files), n_samples))
        
        for i, file_path in enumerate(selected_files):
            spec = np.load(file_path)
            
            plt.figure(figsize=(8, 6))
            plt.imshow(spec, aspect='auto', origin='lower', cmap='viridis')
            plt.colorbar(label='Intensity (dB)')
            plt.title(f"Spectrogram: {label} - {file_path.name}")
            plt.xlabel("Time segments")
            plt.ylabel("Frequency bins")
            
            output_path = VISUAL_DIR / f"{label}_sample_{i}.png"
            plt.savefig(output_path)
            plt.close()
            print(f"  Saved {output_path}")

if __name__ == "__main__":
    visualize_samples()
