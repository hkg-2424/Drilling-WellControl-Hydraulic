"""
Well Control Module: Kill Sheet & Circulating Pressure Schedules
----------------------------------------------------------------
Standard IADC / IWCF Undergraduate Petroleum Engineering Formulations
(Adams, 'Well Control Problems & Solutions' / Bourgoyne et al.)

Covers:
1. Formation Pore Pressure (P_f)
2. Kill Mud Weight (KMW)
3. Initial Circulating Pressure (ICP)
4. Final Circulating Pressure (FCP)
5. Maximum Allowable Annular Surface Pressure (MAASP)
6. Drillstring Capacity, Strokes, and Time to Bit
7. Linear Drillpipe Pressure Step-Down Schedule (Wait & Weight Method)
8. Driller's Method vs Wait-and-Weight Operational Comparison
"""

from typing import Dict, List, Tuple
import numpy as np
import pandas as pd


def calculate_pore_pressure(omw_ppg: float, tvd_ft: float, sidpp_psi: float) -> float:
    """
    Computes bottomhole formation pore pressure from Shut-In Drill Pipe Pressure.

    Textbook Formula:
        P_f (psi) = (0.052 * OMW * TVD) + SIDPP
    Where:
        OMW   = Original Mud Weight (ppg)
        TVD   = True Vertical Depth of the wellbore (ft)
        SIDPP = Shut-In Drill Pipe Pressure (psi)
    """
    p_hyd = 0.052 * omw_ppg * tvd_ft
    return p_hyd + sidpp_psi


def calculate_kill_mud_weight(omw_ppg: float, tvd_ft: float, sidpp_psi: float) -> float:
    """
    Computes Kill Mud Weight (KMW) required to balance formation pore pressure.

    Textbook Formula:
        KMW (ppg) = OMW + [ SIDPP / (0.052 * TVD) ]
    """
    if tvd_ft <= 0.0:
        raise ValueError("TVD must be strictly positive.")
    kmw_increment = sidpp_psi / (0.052 * tvd_ft)
    return omw_ppg + kmw_increment


def calculate_icp(sidpp_psi: float, scrp_psi: float) -> float:
    """
    Computes Initial Circulating Pressure (ICP) on drillpipe gauge at kill rate.

    Textbook Formula:
        ICP (psi) = SIDPP + SCRP
    Where:
        SIDPP = Shut-In Drill Pipe Pressure (psi)
        SCRP  = Slow Circulating Rate Pressure / Kill Rate Friction (psi)
    """
    return sidpp_psi + scrp_psi


def calculate_fcp(scrp_psi: float, kmw_ppg: float, omw_ppg: float) -> float:
    """
    Computes Final Circulating Pressure (FCP) once kill mud fills the drillstring.

    Textbook Formula:
        FCP (psi) = SCRP * (KMW / OMW)
    Because turbulent frictional pressure loss is directly proportional to fluid density.
    """
    if omw_ppg <= 0.0:
        raise ValueError("OMW must be strictly positive.")
    return scrp_psi * (kmw_ppg / omw_ppg)


def calculate_maasp(lot_emw_ppg: float, current_mw_ppg: float, tvd_shoe_ft: float) -> float:
    """
    Computes Maximum Allowable Annular Surface Pressure (MAASP) at casing shoe.

    Textbook Formula:
        MAASP (psi) = 0.052 * (LOT - Current_MW) * TVD_shoe
    Where:
        LOT          = Leak-Off Test Equivalent Mud Weight (ppg)
        Current_MW   = Active mud weight in wellbore (ppg)
        TVD_shoe     = Casing shoe True Vertical Depth (ft)
    """
    return 0.052 * (lot_emw_ppg - current_mw_ppg) * tvd_shoe_ft


def calculate_drillstring_volume_and_strokes(
    md_ft: float,
    pipe_capacity_bbl_ft: float = 0.01776,
    pump_output_bbl_stk: float = 0.10,
    kill_rate_spm: float = 30.0,
) -> Tuple[float, int, float]:
    """
    Computes drillstring internal volume, total pump strokes to bit, and pump time.

    Textbook Formulas:
        V_string (bbl)   = Pipe_Capacity (bbl/ft) * MD (ft)
        Strokes_to_bit   = V_string / Pump_Output (bbl/stroke)
        Time_to_bit (min)= Strokes_to_bit / Kill_Rate (SPM)
    """
    v_string_bbl = pipe_capacity_bbl_ft * md_ft
    strokes_to_bit = int(np.ceil(v_string_bbl / pump_output_bbl_stk))
    time_to_bit_min = strokes_to_bit / kill_rate_spm if kill_rate_spm > 0 else 0.0
    return v_string_bbl, strokes_to_bit, time_to_bit_min


def generate_step_down_schedule(
    icp_psi: float,
    fcp_psi: float,
    strokes_to_bit: int,
    total_strokes_well: int = 0,
    stroke_interval: int = 100,
) -> pd.DataFrame:
    """
    Generates the Wait-and-Weight Drill Pipe Pressure step-down schedule.

    Textbook Formula:
        DPP(s) = ICP - [ (ICP - FCP) / Strokes_to_bit ] * s    (for s <= Strokes_to_bit)
        DPP(s) = FCP                                           (for s > Strokes_to_bit)
    """
    if strokes_to_bit <= 0:
        raise ValueError("Strokes to bit must be positive.")

    if total_strokes_well <= strokes_to_bit:
        # Default annular strokes to ~2.5x string strokes if unspecified
        total_strokes_well = int(strokes_to_bit * 2.5)

    stroke_points = list(range(0, strokes_to_bit, stroke_interval))
    if strokes_to_bit not in stroke_points:
        stroke_points.append(strokes_to_bit)

    # Add points after bit to illustrate holding FCP constant in the annulus
    annular_points = list(range(strokes_to_bit + stroke_interval, total_strokes_well + 1, stroke_interval))
    all_strokes = sorted(stroke_points + annular_points)

    dpp_values = []
    location_desc = []

    slope = (icp_psi - fcp_psi) / float(strokes_to_bit)

    for s in all_strokes:
        if s <= strokes_to_bit:
            # Linear step-down inside the drillstring
            dpp = icp_psi - (slope * s)
            loc = "Kill Mud in Drillstring (Step-Down)" if s < strokes_to_bit else "Kill Mud at Bit"
        else:
            # Held constant while kill mud displaces the annulus
            dpp = fcp_psi
            loc = "Kill Mud in Annulus (Constant FCP)"

        dpp_values.append(round(dpp, 1))
        location_desc.append(loc)

    schedule_df = pd.DataFrame({
        "Pump_Strokes": all_strokes,
        "DPP_psi": dpp_values,
        "Status": location_desc,
    })
    return schedule_df


def compute_well_control_kill_sheet(
    omw_ppg: float = 10.5,
    tvd_ft: float = 8695.74,
    md_ft: float = 10000.0,
    sidpp_psi: float = 500.0,
    sicp_psi: float = 700.0,
    scrp_psi: float = 650.0,
    lot_emw_ppg: float = 14.5,
    tvd_shoe_ft: float = 5000.0,
    pipe_capacity_bbl_ft: float = 0.01776,
    pump_output_bbl_stk: float = 0.10,
    kill_rate_spm: float = 30.0,
) -> Dict[str, float]:
    """
    Computes full well control kill sheet parameters.
    """
    p_pore = calculate_pore_pressure(omw_ppg, tvd_ft, sidpp_psi)
    kmw_exact = calculate_kill_mud_weight(omw_ppg, tvd_ft, sidpp_psi)
    kmw_rounded = float(np.ceil(kmw_exact * 10.0) / 10.0)  # Common rig practice +0.1 margin
    icp = calculate_icp(sidpp_psi, scrp_psi)
    fcp = calculate_fcp(scrp_psi, kmw_exact, omw_ppg)
    maasp_initial = calculate_maasp(lot_emw_ppg, omw_ppg, tvd_shoe_ft)
    maasp_kill = calculate_maasp(lot_emw_ppg, kmw_exact, tvd_shoe_ft)

    v_str, stks_bit, t_bit = calculate_drillstring_volume_and_strokes(
        md_ft, pipe_capacity_bbl_ft, pump_output_bbl_stk, kill_rate_spm
    )
    dp_per_100_stks = ((icp - fcp) / stks_bit) * 100.0 if stks_bit > 0 else 0.0

    return {
        "OMW_ppg": omw_ppg,
        "Pore_Pressure_psi": round(p_pore, 1),
        "KMW_exact_ppg": round(kmw_exact, 2),
        "KMW_recommended_ppg": round(kmw_rounded, 1),
        "SIDPP_psi": sidpp_psi,
        "SICP_psi": sicp_psi,
        "SCRP_psi": scrp_psi,
        "ICP_psi": round(icp, 1),
        "FCP_psi": round(fcp, 1),
        "Initial_MAASP_psi": round(maasp_initial, 1),
        "Final_MAASP_psi": round(maasp_kill, 1),
        "Drillstring_Volume_bbl": round(v_str, 2),
        "Strokes_to_Bit": stks_bit,
        "Time_to_Bit_min": round(t_bit, 1),
        "Pressure_Drop_per_100_Strokes_psi": round(dp_per_100_stks, 1),
    }
