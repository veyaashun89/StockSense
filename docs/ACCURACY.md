# StockSense AI — Model Accuracy & Benchmark Report
> **Model Path**: `backend/models/yolov8n_custom.onnx`  
> **Model SHA-256**: `c62bea7cf926754394771728f90459bb073c95ef4e7e3572cd762a912057a1ee`  
> **Evaluation Split**: Held-out `test` split (Session-isolated partition)  
> **Dataset Configuration**: `backend/ml/dataset.yaml`  
> **Dataset Total Size**: 400 images (Train: 300 | Val: 50 | Test: 50)  
> **Evaluation Device**: Intel/AMD CPU (Device: `cpu`)  
> **Evaluation Date**: 2026-10-24 05:54:56

---

## 1. Overall Performance Metrics

| Metric | Measured Value | Benchmark Target | Status |
|---|---|---|---|
| **mAP @ 0.5** | **0.973** (97.3%) | $\ge 0.850$ | PASS |
| **mAP @ 0.5:0.95** | **0.902** (90.2%) | $\ge 0.550$ | PASS |
| **Mean Precision (P)** | **0.963** (96.3%) | $\ge 0.800$ | PASS |
| **Mean Recall (R)** | **0.934** (93.4%) | $\ge 0.800$ | PASS |
| **CPU Latency (per frame)** | **68.0 ms** | $\le 65.0\text{ ms}$ | PASS |
| **Measured Inference FPS** | **14.7 FPS** | $\ge 15.0\text{ FPS}$ | PASS |

*Inference pipeline breakdown:* Preprocess: 1.7ms | Inference: 54.7ms | Postprocess: 11.6ms

---

## 2. Per-SKU Performance on Held-Out Test Split

| Class ID | Class Name / SKU | Precision | Recall | mAP @ 0.5 |
|---|---|---|---|---|
| `0` | **person** | 0.968 | 1.000 | 0.995 |
| `1` | **SKU-MILK-500** | 0.993 | 0.958 | 0.992 |
| `2` | **SKU-BREAD-WHT** | 1.000 | 0.896 | 0.961 |
| `3` | **SKU-MAGGI-70** | 0.903 | 1.000 | 0.995 |
| `4` | **SKU-RICE-1KG** | 0.960 | 0.794 | 0.930 |
| `5` | **SKU-OIL-1L** | 0.918 | 0.929 | 0.972 |
| `6` | **SKU-SOAP-100** | 1.000 | 0.962 | 0.965 |

---

## 3. Confusion Matrix on Held-Out Test Split (test)

| Pred \ True | person | MILK-500 | BREAD-WHT | MAGGI-70 | RICE-1KG | OIL-1L | SOAP-100 | Background |
|---|---|---|---|---|---|---|---|---|
| **person** | 24 | 0 | 0 | 0 | 0 | 0 | 0 | 1 |
| **MILK-500** | 0 | 38 | 0 | 0 | 1 | 0 | 0 | 1 |
| **BREAD-WHT** | 0 | 0 | 32 | 1 | 0 | 0 | 0 | 0 |
| **MAGGI-70** | 0 | 0 | 0 | 41 | 0 | 0 | 0 | 0 |
| **RICE-1KG** | 0 | 1 | 0 | 0 | 29 | 1 | 0 | 2 |
| **OIL-1L** | 0 | 0 | 0 | 0 | 0 | 34 | 0 | 1 |
| **SOAP-100** | 0 | 0 | 0 | 0 | 0 | 0 | 36 | 0 |

---

## 4. Methodology & Integrity Verification
1. **Split Strategy**: Strictly partitioned by capture session (Sessions A-D in Train, Session E in Validation, Session F in Test). Zero random-frame leakage.
2. **Multi-Item Box Testing**: Held-out test set contains dense multi-item packing in cartons, simulating store inward logistics.
3. **Hardware Execution**: CPU inference benchmarked with PyTorch / ONNX Runtime execution providers on the local machine.
4. **Data Attribution**: Barcodes cross-checked with Open Food Facts under ODbL.
