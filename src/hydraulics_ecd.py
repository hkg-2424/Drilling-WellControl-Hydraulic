"""
Hydraulics and Equivalent Circulating Density (ECD) Module
----------------------------------------------------------
Standard Undergraduate Petroleum Engineering Formulations
(Bourgoyne et al., 'Applied Drilling Engineering' / API RP 13D)

Covers:
1. Steel Buoyancy Factor (BF) & Buoyed Hookload
2. Hydrostatic Pressure (P_hyd)
3. Annular Velocity (Va)
4. Bingham Plastic Laminar Annular Pressure Loss (Delta P_ann)
5. Equivalent Circulating Density (ECD)
6. Safe Drilling Mud Window Evaluation (Pore Pressure vs ECD vs Frac Gradient)
"""

from typing import Dict, Tuple
import numpy as np
import pandas as pd


def calculate_buoyancy_factor(mw_ppg: float) -> float:
    """
    Computes Archimedes buoyancy factor for steel tubulars in drilling mud.

    Textbook Formula:
        BF = 1 - (MW / 65.5)
    Where 65.5 ppg is the density of standard carbon steel (489.5 lb/cu.ft).
    """
    return 1.0 - (mw_ppg / 65.5)


def calculate_buoyed_weight(weight_air_lb: float, mw_ppg: float) -> float:
    """
    Computes buoyed hookload / string weight in mud.

    Textbook Formula:
        W_buoyed = W_air * BF = W_air * (1 - MW / 65.5)
    """
    bf = calculate_buoyancy_factor(mw_ppg)
    return weight_air_lb * bf


def calculate_hydrostatic_pressure(mw_ppg: float, tvd_ft: float) -> float:
    """
    Computes static hydrostatic head pressure exerted by a fluid column.

    Textbook Formula:
        P_hyd (psi) = 0.052 * MW (ppg) * TVD (ft)
    Where 0.052 is the field conversion factor [psi / (ppg * ft)].
    """
    return 0.052 * mw_ppg * tvd_ft


def calculate_annular_velocity(flow_rate_gpm: float, d_hole_in: float, od_pipe_in: float) -> float:
    """
    Computes average annular fluid velocity in feet per minute.

    Textbook Formula:
        Va (ft/min) = (24.51 * Q) / (D_hole^2 - OD_pipe^2)
    Where:
        Q          = Mud circulation rate in gallons per minute (gpm)
        D_hole     = Wellbore / bit diameter in inches
        OD_pipe    = Drill pipe outer diameter in inches
        24.51      = (231 cu.in/gal * 4 / pi) / 12 in/ft
    """
    area_diff = (d_hole_in ** 2) - (od_pipe_in ** 2)
    if area_diff <= 0.0:
        raise ValueError("Hole diameter must be strictly greater than drill pipe OD.")
    return (24.51 * flow_rate_gpm) / area_diff


def calculate_bingham_annular_pressure_loss(
    pv_cp: float,
    yp_lbf_100ft2: float,
    annular_vel_ftmin: float,
    d_hole_in: float,
    od_pipe_in: float,
    delta_md_ft: float,
) -> float:
    """
    Computes laminar frictional pressure loss in the annulus using Bingham Plastic model.

    Textbook Formula:
        Delta P_ann (psi) = [ (PV * Va) / (60,000 * (Dh - Dp)^2)
                            + YP / (200 * (Dh - Dp)) ] * Delta_MD
    Where:
        PV  = Plastic Viscosity (centipoise, cP)
        YP  = Yield Point (lbf / 100 sq.ft)
        Va  = Annular Velocity (ft/min)
        Dh  = Hole Diameter (in)
        Dp  = Drill Pipe OD (in)
        Delta_MD = Measured Depth interval (ft)
    """
    d_hyd = d_hole_in - od_pipe_in
    if d_hyd <= 0.0:
        raise ValueError("Hole diameter must exceed pipe OD.")

    # Viscous shear pressure loss gradient (psi/ft)
    viscous_term = (pv_cp * annular_vel_ftmin) / (60000.0 * (d_hyd ** 2))

    # Yield stress pressure loss gradient (psi/ft)
    yield_term = yp_lbf_100ft2 / (200.0 * d_hyd)

    dp_per_ft = viscous_term + yield_term
    return dp_per_ft * delta_md_ft


def compute_hydraulics_and_ecd(
    traj_df: pd.DataFrame,
    mw_ppg: float = 10.5,
    flow_rate_gpm: float = 450.0,
    d_hole_in: float = 8.5,
    od_pipe_in: float = 5.0,
    pv_cp: float = 20.0,
    yp_lbf_100ft2: float = 15.0,
    pore_press_grad_ppg: float = 9.0,
    frac_grad_ppg: float = 14.2,
) -> pd.DataFrame:
    """
    Calculates depth-dependent hydraulics, cumulative annular pressure loss,
    and Equivalent Circulating Density (ECD) across all survey stations.

    Textbook Formula for ECD:
        ECD (ppg) = MW + Delta_P_ann_cumulative / (0.052 * TVD)
    """
    df = traj_df.copy()
    n = len(df)

    # 1. Annular Velocity is constant for uniform geometry
    va = calculate_annular_velocity(flow_rate_gpm, d_hole_in, od_pipe_in)

    delta_p_ann = np.zeros(n)
    cum_p_ann = np.zeros(n)
    ecd = np.zeros(n)
    p_hyd = np.zeros(n)
    p_bhcp = np.zeros(n)

    md = df["MD_ft"].values
    tvd = df["TVD_ft"].values

    for i in range(1, n):
        d_md = md[i] - md[i - 1]
        # Incremental Bingham plastic annular friction loss
        dp = calculate_bingham_annular_pressure_loss(
            pv_cp, yp_lbf_100ft2, va, d_hole_in, od_pipe_in, d_md
        )
        delta_p_ann[i] = dp
        cum_p_ann[i] = cum_p_ann[i - 1] + dp

    for i in range(n):
        cur_tvd = tvd[i]
        # Hydrostatic Pressure: P_hyd = 0.052 * MW * TVD
        p_hyd[i] = calculate_hydrostatic_pressure(mw_ppg, cur_tvd)
        # Bottomhole Circulating Pressure (BHCP): BHCP = P_hyd + P_ann_cum
        p_bhcp[i] = p_hyd[i] + cum_p_ann[i]

        # Equivalent Circulating Density (ECD)
        # At surface (TVD = 0), ECD equals static mud weight
        if cur_tvd > 1.0:
            ecd[i] = mw_ppg + (cum_p_ann[i] / (0.052 * cur_tvd))
        else:
            ecd[i] = mw_ppg

    df["Annular_Vel_ftmin"] = np.round(va, 1)
    df["Delta_P_Ann_psi"] = np.round(delta_p_ann, 2)
    df["Cum_P_Ann_psi"] = np.round(cum_p_ann, 2)
    df["Hydrostatic_P_psi"] = np.round(p_hyd, 1)
    df["BHCP_psi"] = np.round(p_bhcp, 1)
    df["ECD_ppg"] = np.round(ecd, 2)

    # Mud Window Boundaries
    df["Pore_Pressure_ppg"] = pore_press_grad_ppg
    df["Frac_Gradient_ppg"] = frac_grad_ppg
    df["Pore_Pressure_psi"] = np.round(0.052 * pore_press_grad_ppg * tvd, 1)
    df["Frac_Pressure_psi"] = np.round(0.052 * frac_grad_ppg * tvd, 1)

    # Mud window checks: True if ECD < Frac and Static MW > Pore Pressure
    df["Safe_Window"] = (df["ECD_ppg"] < frac_grad_ppg) & (mw_ppg > pore_press_grad_ppg)

    return df


def get_hydraulics_summary(df: pd.DataFrame, mw_ppg: float) -> Dict[str, float]:
    """
    Summarizes key bottomhole hydraulic and ECD indicators.
    """
    last_row = df.iloc[-1]
    bf = calculate_buoyancy_factor(mw_ppg)
    return {
        "Mud_Weight_ppg": mw_ppg,
        "Buoyancy_Factor": round(bf, 4),
        "Annular_Velocity_ftmin": float(last_row["Annular_Vel_ftmin"]),
        "Total_Annular_Loss_psi": float(last_row["Cum_P_Ann_psi"]),
        "Hydrostatic_P_at_TD_psi": float(last_row["Hydrostatic_P_psi"]),
        "BHCP_at_TD_psi": float(last_row["BHCP_psi"]),
        "ECD_at_TD_ppg": float(last_row["ECD_ppg"]),
        "ECD_Margin_to_Frac_ppg": round(float(last_row["Frac_Gradient_ppg"] - last_row["ECD_ppg"]), 2),
        "Static_Margin_to_Pore_ppg": round(float(mw_ppg - last_row["Pore_Pressure_ppg"]), 2),
    }

