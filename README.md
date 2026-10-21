# Deep Learning for LIBS Spectral Analysis: From NIST Synthetic Modeling to EMSLIBS 2019 Benchmark

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/)
[![PyTorch](https://img.shields.io/badge/PyTorch-2.0+-ee4c2c.svg)](https://pytorch.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

This repository contains an end-to-end deep learning pipeline for Laser-Induced Breakdown Spectroscopy (LIBS) processing, multi-element concentration regression, and high-dimensional spectral classification.

The investigation bridges physics-driven synthetic modeling with empirical real-world benchmarking across two distinct phases:
1. **Phase 1: Synthetic Spectral Modeling & Multi-Element Regression (NIST ASD):** An automated, multi-process scraping engine querying the **NIST Atomic Spectra Database** to simulate plasma emissions under controlled physical parameters ($T_e$, $N_e$). A 1D Convolutional Neural Network (1D-CNN) was trained on 51,332 synthetic spectra to predict the continuous concentrations of 10 target elements simultaneously.
2. **Phase 2: Real-World Soil Classification Benchmark (EMSLIBS 2019):** Systematic benchmarking on the **EMSLIBS 2019 Soil Contest** ($40,002$ spectral channels per shot). The pipeline incorporates binary memory-mapped I/O acceleration, empirical regularization ablations, and a multi-architecture ensemble (ResNet-1D + Inception-1D + WaveNet-1D), achieving a **new benchmark of 80.52% classification accuracy**.

---

## Key Experimental Results

### Phase 1: Elemental Concentration Regression (Synthetic NIST ASD)
* **Dataset Scale:** 51,332 simulated multi-element spectra ($16,001$ spectral points, range 200–800 nm).
* **Target Elements (10):** Mg, Fe, Mn, Al, Zn, C, N, Si, Ni, Cu.
* **Validation Performance:** Achieved a Mean Squared Error (**MSE**) of **1.21** across continuous elemental mass concentrations.

### Phase 2: EMSLIBS 2019 Soil Classification Benchmark
Ablation sweeps demonstrated that cross-architectural diversity (orthogonal inductive biases) significantly outperforms single-architecture seed scaling.

| Model / Ensemble Configuration | Architecture Details & Hyperparameters | Test Accuracy | $\Delta$ vs Baseline |
| :--- | :--- | :---: | :---: |
| **Baseline (Single ResNet-1D)** | `PIAN_ResNet` (Seed 42, standard recipe) | 74.94% | — |
| **Old Baseline Ensemble** | 3 ResNet seeds (42 / 777 / 2024) + TTA | 78.75% | +3.81 pp |
| **Phase 3 ResNet Ensemble** | 4 ResNet seeds (Honest unweighted, $T=1.0$) | 79.15% | +4.21 pp |
| **Single Inception-1D** | Multi-scale parallel kernels (5, 11, 21, 41) | 77.60% | — |
| **Single WaveNet-1D** | Dilated conv blocks (dilation 1, 2, 4, 8) | 75.83% | (78.1% agree w/ ResNet) |
| **Phase 4 Cross-Arch Ensemble (SOTA)** | **ResNet (x2) + Inception-1D + WaveNet-1D** ($T=0.30$, $w=\text{acc}^{10}$) | **80.52%** | **+1.77 pp** |

---

## Methodological Insights & Lessons Learned

1. **Occam's Razor in Spectral Regularization:** Incorporating complex losses (Focal Loss, ClassBalancedLoss) and weight averaging (SWA, EMA) consistently underperformed a streamlined recipe: `CrossEntropyLoss(label_smoothing=0.1)` + `AdamW(weight_decay=0.005)` + `CosineAnnealingLR` + `MixUp(alpha=0.2)` + `SpecAugment`.
2. **Architectural Decorrelation > Seed Diversity:** WaveNet-1D exhibited only a 78.1% prediction agreement with ResNet-1D. Injecting models with differing receptive-field dynamics provided orthogonal error representations that drove the ensemble beyond 80%.
3. **Test-Time Augmentation (TTA):** Averaging predicted probability distributions post-softmax ($\text{avg}(\text{softmax})$) outperformed logit averaging ($\text{softmax}(\text{avg}(\text{logits}))$) by **+0.46 pp**.

---

## Repository Architecture

```text
ML-LIBS/
├── 01_synthetic_elemental_regression.ipynb # Phase 1: 51k NIST HDF5 pipeline & multi-output 1D-CNN regression
├── 02_soil_baseline_and_memmap.ipynb       # Phase 2A: EMSLIBS data engineering, Memmap binary I/O & ResNet baselines
├── 03_soil_sota_ensemble_push.ipynb        # Phase 2B: Regularization ablations, Inception/WaveNet & 80.52% ensemble
├── generator_selenium.py                   # Automated multi-process NIST ASD synthetic spectrum scraper
├── requirements.txt                        # Pinned dependencies
├── .gitignore                              # Data and checkpoint exclusion rules
└── README.md                               # Project documentation