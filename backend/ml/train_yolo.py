"""
StockSense AI - Custom YOLOv8 Fine-Tuning Script
------------------------------------------------
Trains Ultralytics YOLOv8n on custom grocery retail SKUs and exports to ONNX
for ultra-fast offline CPU inference.

Usage:
    python backend/ml/train_yolo.py --epochs 50 --imgsz 640 --batch 16

Directory layout expected:
    backend/ml/dataset/
    ├── images/
    │   ├── train/  (e.g., frame_001.jpg)
    │   └── val/    (e.g., frame_050.jpg)
    └── labels/
        ├── train/  (e.g., frame_001.txt with <class_id> <x_center> <y_center> <width> <height>)
        └── val/    (e.g., frame_050.txt)
"""

import os
import sys
import argparse
from pathlib import Path

def train_and_export(
    data_yaml: str = "backend/ml/dataset.yaml",
    epochs: int = 50,
    imgsz: int = 640,
    batch_size: int = 16,
    output_onnx: str = "backend/models/yolov8n_custom.onnx"
):
    try:
        from ultralytics import YOLO
    except ImportError:
        print("[!] Ultralytics not installed. Install with: pip install ultralytics")
        sys.exit(1)

    print(f"[*] Starting YOLOv8 fine-tuning on {data_yaml} for {epochs} epochs...")
    # Load pretrained baseline weights
    model = YOLO("yolov8n.pt")

    # Train model
    results = model.train(
        data=data_yaml,
        epochs=epochs,
        imgsz=imgsz,
        batch=batch_size,
        device="cpu", # or '0' if CUDA GPU available
        project="backend/ml/runs",
        name="stocksense_retail_detector"
    )

    print("[*] Training complete. Exporting best checkpoint to ONNX format...")
    best_weights = Path(results.save_dir) / "weights" / "best.pt"
    
    export_model = YOLO(str(best_weights))
    exported_path = export_model.export(
        format="onnx",
        imgsz=imgsz,
        dynamic=False,
        simplify=False
    )

    import shutil
    target_onnx = Path(output_onnx)
    target_onnx.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy(exported_path, target_onnx)

    print(f"[+] Custom ONNX model successfully exported: {target_onnx}")
    print(f"[+] To use in StockSense, set environment variable:")
    print(f"    $env:YOLO_MODEL_PATH=\"{target_onnx}\"")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Train custom YOLOv8 model for StockSense retail inventory")
    parser.add_argument("--data", default="backend/ml/dataset.yaml", help="Path to dataset.yaml")
    parser.add_argument("--epochs", type=int, default=50, help="Number of training epochs")
    parser.add_argument("--imgsz", type=int, default=640, help="Image resolution")
    parser.add_argument("--batch", type=int, default=16, help="Batch size")
    parser.add_argument("--output", default="backend/models/yolov8n_custom.onnx", help="Target ONNX export path")
    args = parser.parse_args()

    train_and_export(
        data_yaml=args.data,
        epochs=args.epochs,
        imgsz=args.imgsz,
        batch_size=args.batch,
        output_onnx=args.output
    )
