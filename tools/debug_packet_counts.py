import numpy as np
import os
from pathlib import Path

data_dir = Path('data')
labels = ['idle', 'walk', 'sit', 'fall']

for label in labels:
    label_dir = data_dir / label
    if not label_dir.exists():
        continue
    files = list(label_dir.glob('*.npz'))
    print(f"{label}: {len(files)} files")
    short_count = 0
    for f in files:
        try:
            d = np.load(f)
            pkts = len(d['csi_data'])
            if pkts < 500:
                print(f"  {f.name}: {pkts} packets (Minimum 500 required)")
                short_count += 1
        except Exception as e:
            print(f"  {f.name}: Error loading ({e})")
    
    if short_count > 0:
        print(f"  Total too short for {label}: {short_count}")
