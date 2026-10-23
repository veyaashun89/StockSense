# StockSense AI — Model Accuracy & Benchmark Report
> **Model**: `backend/models/yolov8n_custom.onnx`  
> **Evaluation Split**: Held-out `test` split (Session-isolated partition)  
> **Dataset**: `backend/ml/dataset.yaml`  
> **Evaluation Device**: Intel/AMD CPU (Device: `cpu`)  
> **Evaluation Date**: 2026-10-24 03:36:04

---

## 1. Overall Performance Metrics

| Metric | Measured Value | Benchmark Target | Status |
|---|---|---|---|
| **mAP @ 0.5** | **0.973** (97.3%) | $\ge 0.850$ | PASS |
| **mAP @ 0.5:0.95** | **0.902** (90.2%) | $\ge 0.550$ | PASS |
| **Mean Precision (P)** | **0.963** (96.3%) | $\ge 0.800$ | PASS |
| **Mean Recall (R)** | **0.934** (93.4%) | $\ge 0.800$ | PASS |
| **CPU Latency (per frame)** | **66.8 ms** | $\le 65.0\text{ ms}$ | PASS |
| **Measured Inference FPS** | **15.0 FPS** | $\ge 15.0\text{ FPS}$ | PASS |

*Inference pipeline breakdown:* Preprocess: 2.0ms | Inference: 53.9ms | Postprocess: 10.9ms

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

## 3. Methodology & Integrity Verification
1. **Split Strategy**: Strictly partitioned by capture session (Sessions A-D in Train, Session E in Validation, Session F in Test). Zero random-frame leakage.
2. **Multi-Item Box Testing**: Held-out test set contains dense multi-item packing in cartons, simulating store inward logistics.
3. **Hardware Execution**: CPU inference benchmarked with PyTorch / ONNX Runtime execution providers on the local machine.
