"""
Geist - Data Quality & Class Separation Analysis

Analyzes the generated spectrograms to verify if different activities
have distinct mathematical "signatures". This helps confirm if the 
data is suitable for training before starting Phase 2.

Author: Gemini CLI (Geist Project)
License: GPLv3
"""

import numpy as np
import os
from pathlib import Path

DATA_DIR = Path(__file__).parent.parent / 'data'
SPECTROGRAM_DIR = DATA_DIR / 'spectrograms'

def analyze_classes():
    results = {}
    
    labels = [d.name for d in SPECTROGRAM_DIR.iterdir() if d.is_dir()]
    
    print(f"{'Label':<12} | {'Count':<6} | {'Mean (dB)':<10} | {'Std Dev':<10} | {'Max Power':<10}")
    print("-" * 60)
    
    for label in labels:
        label_dir = SPECTROGRAM_DIR / label
        files = list(label_dir.glob("*.npy"))
        
        if not files:
            continue
            
        means = []
        stds = []
        maxes = []
        
        for f in files:
            spec = np.load(f)
            # Filter out the epsilon we added to log (1e-10) to get real intensity
            means.append(np.mean(spec))
            stds.append(np.std(spec))
            maxes.append(np.max(spec))
            
        results[label] = {
            'count': len(files),
            'mean': np.mean(means),
            'std': np.mean(stds),
            'max': np.mean(maxes)
        }
        
        print(f"{label:<12} | {len(files):<6} | {results[label]['mean']:<10.2f} | {results[label]['std']:<10.2f} | {results[label]['max']:<10.2f}")

    # Check for potential issues
    print("\n--- Diagnostic Insights ---")
    
    if 'idle' in results and 'walk' in results:
        diff = results['walk']['mean'] - results['idle']['mean']
        if diff > 5:
            print(f"✅ GOOD: Walk is significantly more energetic than Idle (Diff: {diff:.2f} dB).")
        else:
            print(f"⚠️ WARNING: Walk and Idle have similar energy levels ({diff:.2f} dB diff). Detection might be hard.")

    if 'fall' in results:
        if results['fall']['max'] > results['walk']['max']:
            print(f"✅ GOOD: Fall shows higher peak intensity than Walk ({results['fall']['max']:.2f} vs {results['walk']['max']:.2f} dB).")
        else:
            print("⚠️ NOTE: Fall peaks are not higher than Walking. This is common if falls are slow, but might need careful training.")

    if 'sit' in results:
        print(f"ℹ️ Sit has {results['sit']['count']} samples. With your 3-4s gap, many windows will capture the 'still' part of sitting.")

if __name__ == "__main__":
    analyze_classes()
