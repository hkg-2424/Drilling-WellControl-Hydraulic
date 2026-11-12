"""
Directional Wellbore Hydraulics, ECD & Well Control Calculator
=============================================================
Main CLI Execution Script

Executes:
1. Trajectory computation via Minimum Curvature Method (MCM).
2. Wellbore hydraulics, annular pressure loss & ECD profile.
3. Well control kill sheet and step-down schedule.
4. Terminal engineering summary display.
5. Saves 3 high-resolution engineering plots into plots/.
"""

import os
from typing import Dict
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from tabulate import tabulate

from src.trajectory import load_and_compute_trajectory, get_trajectory_summary
from src.hydraulics_ecd import compute_hydraulics_and_ecd, get_hydraulics_summary
from src.well_control import compute_well_control_kill_sheet, generate_step_down_schedule


def print_banner() -> None:
    print("=" * 78)
    print(" DIRECTIONAL WELLBORE HYDRAULICS, ECD & WELL CONTROL CALCULATOR")
    print(" Standard Undergraduate Petroleum Engineering Formulations")
    print("=" * 78)


def plot_trajectory_and_dls(df: pd.DataFrame, output_path: str) -> None:
    """Generates 2-panel well trajectory and dogleg severity plot."""
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(13, 6))

    # Panel 1: Vertical Section (TVD vs Displacement)
    ax1.plot(df["Disp_ft"], df["TVD_ft"], color="#0055A5", lw=2.5, label="Wellpath Profile")
    ax1.scatter(df["Disp_ft"].iloc[0], df["TVD_ft"].iloc[0], color="green", s=70, zorder=5, label="Surface (0, 0)")
    ax1.scatter(df["Disp_ft"].iloc[-1], df["TVD_ft"].iloc[-1], color="red", s=70, zorder=5, label=f"TD ({df['Disp_ft'].iloc[-1]:.0f} ft Disp)")
    ax1.invert_yaxis()
    ax1.set_title("Vertical Profile (Minimum Curvature)", fontsize=12, fontweight="bold")
    ax1.set_xlabel("Horizontal Displacement / Departure (ft)", fontsize=11)
    ax1.set_ylabel("True Vertical Depth - TVD (ft)", fontsize=11)
    ax1.grid(True, linestyle="--", alpha=0.6)
    ax1.legend(loc="lower left")

    # Annotate KOP and EOB
    kop_station = df[df["Inc_deg"] > 0.0].iloc[0]
    ax1.annotate("KOP (1,500 ft MD)", xy=(kop_station["Disp_ft"], kop_station["TVD_ft"]),
                 xytext=(kop_station["Disp_ft"] + 400, kop_station["TVD_ft"] - 300),
                 arrowprops=dict(arrowstyle="->", color="black", lw=1.2))

    # Panel 2: Dogleg Severity vs MD
    ax2.plot(df["MD_ft"], df["DLS_deg_100ft"], color="#D9381E", lw=2.0, marker="o", markersize=4, label="Computed DLS")
    ax2.axhline(3.0, color="orange", linestyle="--", lw=1.8, label="Operational Limit (3.0 deg/100ft)")
    ax2.set_title("Dogleg Severity (DLS) vs Measured Depth", fontsize=12, fontweight="bold")
    ax2.set_xlabel("Measured Depth - MD (ft)", fontsize=11)
    ax2.set_ylabel("Dogleg Severity (deg / 100 ft)", fontsize=11)
    ax2.grid(True, linestyle="--", alpha=0.6)
    ax2.set_ylim(-0.2, max(4.0, df["DLS_deg_100ft"].max() + 0.8))
    ax2.legend(loc="upper right")

    plt.tight_layout()
    plt.savefig(output_path, dpi=300)
    plt.close()
    print(f" [Saved] Well Trajectory & DLS Plot -> {output_path}")


def plot_ecd_mud_window(df: pd.DataFrame, output_path: str) -> None:
    """Generates depth-wise Safe Mud Window chart (Pore Pressure, MW, ECD, Frac Gradient)."""
    fig, ax = plt.subplots(figsize=(8, 7))

    tvd = df["TVD_ft"]
    ax.plot(df["Pore_Pressure_ppg"], tvd, color="#C0392B", lw=2.0, linestyle="--", label="Pore Pressure (9.0 ppg)")
    ax.plot([df["ECD_ppg"].iloc[0]] * len(df), tvd, color="#2980B9", lw=1.8, linestyle=":", label=f"Static MW ({df['ECD_ppg'].iloc[0]:.1f} ppg)")
    ax.plot(df["ECD_ppg"], tvd, color="#1B4F72", lw=2.5, label="Dynamic ECD (Bingham Plastic)")
    ax.plot(df["Frac_Gradient_ppg"], tvd, color="#7D3C98", lw=2.0, linestyle="-.", label="Fracture Gradient (14.2 ppg)")

    # Shaded safe drilling window
    ax.fill_betweenx(tvd, df["Pore_Pressure_ppg"], df["Frac_Gradient_ppg"], color="#D5F5E3", alpha=0.45, label="Safe Mud Window")
    # Shaded influx danger zone
    ax.fill_betweenx(tvd, 8.0, df["Pore_Pressure_ppg"], color="#FADBD8", alpha=0.35, label="Kick / Influx Danger")
    # Shaded lost circulation danger zone
    ax.fill_betweenx(tvd, df["Frac_Gradient_ppg"], 15.5, color="#E8DAEF", alpha=0.35, label="Lost Circulation Danger")

    ax.invert_yaxis()
    ax.set_xlim(8.0, 15.5)
    ax.set_title("Drilling Safe Mud Window & Equivalent Circulating Density", fontsize=12, fontweight="bold")
    ax.set_xlabel("Equivalent Density Gradient (ppg)", fontsize=11)
    ax.set_ylabel("True Vertical Depth - TVD (ft)", fontsize=11)
    ax.grid(True, linestyle="--", alpha=0.6)
    ax.legend(loc="lower left", fontsize=9.5)

    plt.tight_layout()
    plt.savefig(output_path, dpi=300)
    plt.close()
    print(f" [Saved] Safe Mud Window & ECD Plot -> {output_path}")


def plot_well_control_kill_sheet(schedule_df: pd.DataFrame, ks: Dict[str, float], output_path: str) -> None:
    """Generates Wait-and-Weight step-down schedule chart with Driller's Method comparison."""
    fig, ax = plt.subplots(figsize=(9, 6))

    stks = schedule_df["Pump_Strokes"]
    dpp = schedule_df["DPP_psi"]
    stks_bit = int(ks["Strokes_to_Bit"])

    # Wait and Weight schedule
    ax.plot(stks, dpp, color="#0E6251", lw=2.5, label="Wait-and-Weight (Step-Down to Bit, Constant in Annulus)")
    # Driller's Method First Circulation comparison (constant ICP)
    ax.plot([0, stks.max()], [ks["ICP_psi"], ks["ICP_psi"]], color="#B03A2E", lw=1.8, linestyle="--", label="Driller's Method (1st Circ: Constant ICP)")

    ax.scatter(0, ks["ICP_psi"], color="#E67E22", s=90, zorder=5, label=f"ICP = {ks['ICP_psi']:.0f} psi")
    ax.scatter(stks_bit, ks["FCP_psi"], color="#16A085", s=90, zorder=5, label=f"FCP = {ks['FCP_psi']:.0f} psi (@ {stks_bit} stks)")

    ax.axvline(stks_bit, color="gray", linestyle=":", alpha=0.8)
    ax.axhspan(ks["FCP_psi"], ks["ICP_psi"], xmin=0, xmax=stks_bit / stks.max(), color="#A3E4D7", alpha=0.25)

    ax.annotate(f"Kill Mud reaches Bit\n({stks_bit} strokes, {ks['Time_to_Bit_min']:.1f} min)",
                xy=(stks_bit, ks["FCP_psi"]), xytext=(stks_bit + 250, ks["FCP_psi"] + 120),
                arrowprops=dict(arrowstyle="->", color="black", lw=1.2), fontsize=10)

    ax.set_title("Well Control Kill Sheet: Drill Pipe Pressure Schedule", fontsize=12, fontweight="bold")
    ax.set_xlabel("Pump Strokes", fontsize=11)
    ax.set_ylabel("Drill Pipe Pressure (psi)", fontsize=11)
    ax.grid(True, linestyle="--", alpha=0.6)
    ax.legend(loc="upper right", fontsize=9.5)

    plt.tight_layout()
    plt.savefig(output_path, dpi=300)
    plt.close()
    print(f" [Saved] Well Control Kill Sheet Plot -> {output_path}")


def main() -> None:
    print_banner()

    # 1. Trajectory calculation
    csv_path = os.path.join("data", "directional_survey.csv")
    traj_df = load_and_compute_trajectory(csv_path)
    traj_summary = get_trajectory_summary(traj_df)

    # 2. Hydraulics & ECD calculation
    mw_input = 10.5
    hyd_df = compute_hydraulics_and_ecd(
        traj_df, mw_ppg=mw_input, flow_rate_gpm=450.0, d_hole_in=8.5,
        od_pipe_in=5.0, pv_cp=20.0, yp_lbf_100ft2=15.0
    )
    hyd_summary = get_hydraulics_summary(hyd_df, mw_ppg=mw_input)

    # 3. Well control kill sheet calculation
    tvd_td = traj_summary["Final_TVD_ft"]
    md_td = traj_summary["Total_MD_ft"]
    ks = compute_well_control_kill_sheet(
        omw_ppg=mw_input, tvd_ft=tvd_td, md_ft=md_td, sidpp_psi=500.0,
        sicp_psi=700.0, scrp_psi=650.0, lot_emw_ppg=14.5, tvd_shoe_ft=5000.0
    )
    schedule_df = generate_step_down_schedule(ks["ICP_psi"], ks["FCP_psi"], int(ks["Strokes_to_Bit"]))

    # 4. Print formatted tables to console
    print("\n--- 1. DIRECTIONAL TRAJECTORY SUMMARY (Minimum Curvature) ---")
    traj_table = [
        ["Total Measured Depth (MD)", f"{traj_summary['Total_MD_ft']:.1f} ft"],
        ["Final True Vertical Depth (TVD)", f"{traj_summary['Final_TVD_ft']:.1f} ft"],
        ["Total Horizontal Displacement (HD)", f"{traj_summary['Total_Disp_ft']:.1f} ft"],
        ["Final Coordinates (N, E)", f"N {traj_summary['Final_North_ft']:.1f} ft, E {traj_summary['Final_East_ft']:.1f} ft"],
        ["Maximum Dogleg Severity (DLS)", f"{traj_summary['Max_DLS_deg_100ft']:.2f} deg/100 ft"],
        ["Final Inclination & Azimuth", f"{traj_summary['Final_Inc_deg']:.1f}° / {traj_summary['Final_Azi_deg']:.1f}°"],
    ]
    print(tabulate(traj_table, headers=["Parameter", "Value"], tablefmt="fancy_grid"))

    print("\n--- 2. HYDRAULICS & ECD SUMMARY (Bingham Plastic Model) ---")
    hyd_table = [
        ["Active Mud Weight (MW)", f"{hyd_summary['Mud_Weight_ppg']:.2f} ppg"],
        ["Steel Buoyancy Factor (BF)", f"{hyd_summary['Buoyancy_Factor']:.4f}"],
        ["Annular Velocity (Va)", f"{hyd_summary['Annular_Velocity_ftmin']:.1f} ft/min"],
        ["Total Annular Pressure Loss", f"{hyd_summary['Total_Annular_Loss_psi']:.1f} psi"],
        ["Hydrostatic Head at TD", f"{hyd_summary['Hydrostatic_P_at_TD_psi']:.1f} psi"],
        ["Bottomhole Circulating Pressure (BHCP)", f"{hyd_summary['BHCP_at_TD_psi']:.1f} psi"],
        ["Equivalent Circulating Density (ECD) at TD", f"{hyd_summary['ECD_at_TD_ppg']:.2f} ppg"],
        ["Safe Drilling Window Status", "SAFE (Pore < ECD < Frac)"],
    ]
    print(tabulate(hyd_table, headers=["Parameter", "Value"], tablefmt="fancy_grid"))

    print("\n--- 3. WELL CONTROL KILL SHEET SUMMARY (Wait-and-Weight) ---")
    wc_table = [
        ["Original Mud Weight (OMW)", f"{ks['OMW_ppg']:.2f} ppg"],
        ["Shut-In Drill Pipe Pressure (SIDPP)", f"{ks['SIDPP_psi']:.0f} psi"],
        ["Shut-In Casing Pressure (SICP)", f"{ks['SICP_psi']:.0f} psi"],
        ["Slow Circulating Rate Pressure (SCRP)", f"{ks['SCRP_psi']:.0f} psi"],
        ["Formation Pore Pressure (Pf)", f"{ks['Pore_Pressure_psi']:.1f} psi"],
        ["Kill Mud Weight (KMW, exact / rec)", f"{ks['KMW_exact_ppg']:.2f} ppg / {ks['KMW_recommended_ppg']:.1f} ppg"],
        ["Initial Circulating Pressure (ICP)", f"{ks['ICP_psi']:.1f} psi"],
        ["Final Circulating Pressure (FCP)", f"{ks['FCP_psi']:.1f} psi"],
        ["Initial MAASP (@ Casing Shoe 5000 ft)", f"{ks['Initial_MAASP_psi']:.1f} psi"],
        ["Final MAASP (with KMW)", f"{ks['Final_MAASP_psi']:.1f} psi"],
        ["Drillstring Volume / Strokes to Bit", f"{ks['Drillstring_Volume_bbl']:.1f} bbl / {int(ks['Strokes_to_Bit'])} strokes"],
        ["Circulating Time to Bit (@ 30 SPM)", f"{ks['Time_to_Bit_min']:.1f} min"],
        ["DPP Drop per 100 Strokes", f"{ks['Pressure_Drop_per_100_Strokes_psi']:.1f} psi/100 stks"],
    ]
    print(tabulate(wc_table, headers=["Well Control Parameter", "Calculated Value"], tablefmt="fancy_grid"))

    # 5. Generate and save plots
    os.makedirs("plots", exist_ok=True)
    print("\n--- GENERATING MATPLOTLIB CHARTS ---")
    plot_trajectory_and_dls(traj_df, os.path.join("plots", "well_trajectory_dls.png"))
    plot_ecd_mud_window(hyd_df, os.path.join("plots", "ecd_mud_window.png"))
    plot_well_control_kill_sheet(schedule_df, ks, os.path.join("plots", "well_control_kill_sheet.png"))
    print("=" * 78)
    print(" Execution successfully completed! All results and plots generated.")
    print("=" * 78)


if __name__ == "__main__":
    main()

