"""
Geist - Automated HAR CNN Training Script
Updated to automatically discover new classes.
"""

import os, sys, json, numpy as np, tensorflow as tf, argparse
from tensorflow.keras import layers, models
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import LabelEncoder
from sklearn.utils import class_weight
from pathlib import Path

DATA_DIR = Path(__file__).parent.parent / 'data'
SPECTROGRAM_DIR = DATA_DIR / 'spectrograms'
MODEL_DIR = Path(__file__).parent.parent / 'models'
TARGET_SHAPE = (33, 17) # 3 seconds @ 100Hz

def load_dataset():
    X, y = [], []
    # Automatically find all subdirectories in spectrograms
    found_labels = [d.name for d in SPECTROGRAM_DIR.iterdir() if d.is_dir()]
    print(f"Loading data for classes: {found_labels}")
    
    for label in found_labels:
        label_dir = SPECTROGRAM_DIR / label
        for f in label_dir.glob("*.npy"):
            spec = np.load(f)
            if spec.shape != TARGET_SHAPE: continue
            X.append(spec)
            y.append(label)
    return np.array(X), np.array(y), found_labels

def build_model(input_shape, num_classes):
    model = models.Sequential([
        layers.Input(shape=(input_shape[0], input_shape[1], 1)),
        layers.Conv2D(16, (3, 3), activation='relu', padding='same'),
        layers.MaxPooling2D((2, 2)),
        layers.Conv2D(32, (3, 3), activation='relu', padding='same'),
        layers.MaxPooling2D((2, 2)),
        layers.Flatten(),
        layers.Dense(32, activation='relu'),
        layers.Dropout(0.5),
        layers.Dense(num_classes, activation='softmax')
    ])
    model.compile(optimizer='adam', loss='sparse_categorical_crossentropy', metrics=['accuracy'])
    return model

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--epochs", type=int, default=30)
    args = parser.parse_args()

    MODEL_DIR.mkdir(exist_ok=True)
    X, y, labels = load_dataset()
    if len(X) == 0:
        print("No spectrograms found.")
        return

    le = LabelEncoder()
    y_encoded = le.fit_transform(y)
    
    X_train, X_val, y_train, y_val = train_test_split(X, y_encoded, test_size=0.2, random_state=42, stratify=y_encoded)
    X_train = X_train[..., np.newaxis]
    X_val = X_val[..., np.newaxis]
    
    weights = class_weight.compute_class_weight('balanced', classes=np.unique(y_train), y=y_train)
    
    model = build_model((TARGET_SHAPE[0], TARGET_SHAPE[1]), len(labels))
    model.fit(X_train, y_train, validation_data=(X_val, y_val), epochs=args.epochs, batch_size=16, 
              class_weight=dict(enumerate(weights)), verbose=1)
    
    model.save(MODEL_DIR / 'har_model.h5')
    
    # Save TFLite to a temporary file first, then rename (atomic)
    # This prevents 'Bus error' in the backend which might have the file memory-mapped.
    print("Converting to TFLite...")
    converter = tf.lite.TFLiteConverter.from_keras_model(model)
    tflite_model = converter.convert()
    
    temp_tflite = MODEL_DIR / 'har_model_tmp.tflite'
    with open(temp_tflite, 'wb') as f:
        f.write(tflite_model)
    
    # Atomic swap
    temp_tflite.replace(MODEL_DIR / 'har_model.tflite')
    
    params = {'labels': list(le.classes_), 'norm_mean': 0.0, 'norm_std': 1.0}
    with open(MODEL_DIR / 'har_model_params.json', 'w') as f: json.dump(params, f)
    print("Retraining Complete.")

if __name__ == "__main__":
    main()
