# Directional Wellbore Hydraulics, ECD & Well Control Calculator

A clean, modular, undergraduate textbook-based Python engineering project designed for Petroleum Engineering students and drilling engineers. 

Implements:
1. **Directional Trajectory Calculation**: Minimum Curvature Method (MCM) to compute TVD, Northing, Easting, Departure, and Dogleg Severity (DLS).
2. **Wellbore Hydraulics & Dynamic Pressure**: Bingham Plastic annular laminar frictional pressure loss, Annular Velocity ($V_a$), Steel Buoyancy Factor, and Equivalent Circulating Density (ECD) profile.
3. **Safe Drilling Mud Window**: Verifies that static mud weight and dynamic ECD remain safely within pore pressure and fracture gradient boundaries.
4. **Well Control Kill Sheet (IADC / IWCF)**: Computes Formation Pore Pressure, Kill Mud Weight (KMW), Initial Circulating Pressure (ICP), Final Circulating Pressure (FCP), Maximum Allowable Annular Surface Pressure (MAASP), and the linear Drill Pipe Pressure step-down schedule.
5. **Real-World Field & Benchmark Parity**: Verified against real directional survey data from Equinor's North Sea Volve Well 15/9-F-12, Dutch North Sea Well P11-A-02 (horizontal), and SPE Example 8.2 (Bourgoyne et al.), with 100% numerical parity (MAE = 0.0000 ft).

---

## Project Structure

```text
drilling-hydraulics-wellcontrol/
├── dataset/                                 # Field surveys and benchmark datasets
│   ├── raw_downloaded_p11_a02_survey.csv    # Raw downloaded Dutch North Sea P11-A-02 horizontal survey
│   ├── real_northsea_p11_a02_survey.csv     # Processed P11-A-02 survey (8,828 ft MD / 5,267 ft TVD)
│   ├── real_volve_15_9_F12_survey.csv       # Equinor Volve Well 15/9-F-12 survey (3,520 m MD / 3,107 m TVD)
│   ├── spe_example_8_2_benchmark.csv        # SPE Example 8.2 (Bourgoyne) directional benchmark
│   ├── iadc_hydraulics_wellcontrol_benchmark.json # 16-parameter IADC hydraulics/kill sheet benchmark
│   └── directional_survey.csv               # Baseline synthetic 25-station deviated well (10,000 ft MD)
├── src/
│   ├── trajectory.py                        # Minimum Curvature Method (TVD, North, East, Disp, DLS) [<150 lines]
│   ├── hydraulics_ecd.py                    # Bingham Plastic Annular Pressure Loss, ECD & Mud Window [<170 lines]
│   └── well_control.py                      # Well Control Kill Sheet, KMW, ICP, FCP, MAASP, Step-Down [<180 lines]
├── plots/                                   # Generated high-resolution Matplotlib figures
│   ├── well_trajectory_dls.png              # Vertical profile & Dogleg Severity vs MD
│   ├── ecd_mud_window.png                   # Depth vs Pore Pressure, Static MW, ECD, Frac Gradient
│   ├── well_control_kill_sheet.png          # DPP Step-Down Schedule vs Pump Strokes
│   └── real_well_verification.png           # 4-panel parity plot (Volve 15/9-F-12 vs MCM calculations)
├── main.py                                  # CLI script running analysis, formatted tables & plots [<180 lines]
├── app.py                                   # Streamlit interactive web app with benchmark toggles [<200 lines]
├── verify_real_data.py                      # Automated field parity and benchmarking verification script [<200 lines]
├── requirements.txt                         # Python dependencies
├── VALIDATION_REPORT.md                     # Numerical parity report, error metrics, and technical benchmarks
└── README.md                                # Project guide & instructions
```

---

## Quickstart Guide

### 1. Install Dependencies
```bash
pip install -r requirements.txt
```

### 2. Run CLI Analysis & Generate Plots
```bash
python main.py
```

### 3. Run Automated Field & Benchmark Verification Suite
```bash
python verify_real_data.py
```
This validates our calculations against Equinor Volve Well 15/9-F-12, North Sea P11-A-02, and the IADC benchmark problem, printing side-by-side comparison tables and generating `plots/real_well_verification.png`.

### 4. Launch Interactive Streamlit Web App
```bash
streamlit run app.py
```
In the sidebar, you can toggle between the **Synthetic 10,000 ft well**, **Equinor Volve 15/9-F-12 Real North Sea Well**, **North Sea P11-A-02 Horizontal**, and **SPE Example 8.2**, while adjusting operational parameters with real-time reactive recalculations.

---

## Engineering Validation & Technical Benchmarks

* **Numerical Accuracy & Benchmarking**: See [VALIDATION_REPORT.md](VALIDATION_REPORT.md) for full error metrics against Equinor Volve Well 15/9-F-12, North Sea P11-A-02, and published IADC/SPE benchmarks.
* **Textbook Formulations**: Based on standard undergraduate petroleum engineering equations from Bourgoyne et al. (*Applied Drilling Engineering*), Rabia, and IADC/IWCF well control standards.
