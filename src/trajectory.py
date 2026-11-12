"""
Trajectory Calculation Module: Minimum Curvature Method (MCM)
-------------------------------------------------------------
Standard Industry & Textbook Method (API RP 78 / Bourgoyne et al.)

Computes True Vertical Depth (TVD), Northing, Easting, Horizontal Displacement,
and Dogleg Severity (DLS) from directional survey stations (MD, Inc, Azi).

Textbook Formula References:
- Dogleg Angle:
    cos(beta) = cos(I1)*cos(I2) + sin(I1)*sin(I2)*cos(A2 - A1)
- Ratio Factor:
    RF = (2 / beta) * tan(beta / 2)  [beta in radians; RF = 1.0 if beta < 1e-4]
- Increments:
    dTVD = (dMD / 2) * (cos(I1) + cos(I2)) * RF
    dN   = (dMD / 2) * (sin(I1)*cos(A1) + sin(I2)*cos(A2)) * RF
    dE   = (dMD / 2) * (sin(I1)*sin(A1) + sin(I2)*sin(A2)) * RF
- Dogleg Severity (deg / 100 ft):
    DLS  = (beta_deg / dMD) * 100
"""

from typing import Dict, Tuple
import numpy as np
import pandas as pd


def compute_minimum_curvature(survey_df: pd.DataFrame) -> pd.DataFrame:
    """
    Applies the Minimum Curvature Method to compute the 3D directional wellpath.

    Parameters
    ----------
    survey_df : pd.DataFrame
        DataFrame with required columns: ['MD_ft', 'Inc_deg', 'Azi_deg'].

    Returns
    -------
    pd.DataFrame
        Enriched DataFrame with calculated columns:
        ['TVD_ft', 'North_ft', 'East_ft', 'Disp_ft', 'DLS_deg_100ft',
         'Delta_TVD', 'Delta_N', 'Delta_E', 'Dogleg_deg']
    """
    df = survey_df.copy()
    n_stations = len(df)

    # Initialize output arrays
    tvd = np.zeros(n_stations)
    north = np.zeros(n_stations)
    east = np.zeros(n_stations)
    dls = np.zeros(n_stations)
    d_tvd = np.zeros(n_stations)
    d_north = np.zeros(n_stations)
    d_east = np.zeros(n_stations)
    dogleg_deg = np.zeros(n_stations)

    # Convert survey angles from degrees to radians for trigonometric functions
    # Formula: rad = deg * (pi / 180)
    inc_rad = np.radians(df["Inc_deg"].values)
    azi_rad = np.radians(df["Azi_deg"].values)
    md = df["MD_ft"].values

    for i in range(1, n_stations):
        d_md = md[i] - md[i - 1]
        if d_md <= 0.0:
            continue

        i1, i2 = inc_rad[i - 1], inc_rad[i]
        a1, a2 = azi_rad[i - 1], azi_rad[i]

        # -------------------------------------------------------------
        # 1. Dogleg Angle (beta) in radians
        # Formula: cos(beta) = cos(I1)*cos(I2) + sin(I1)*sin(I2)*cos(A2 - A1)
        # -------------------------------------------------------------
        cos_beta = (np.cos(i1) * np.cos(i2)) + (np.sin(i1) * np.sin(i2) * np.cos(a2 - a1))

        # Numerical clamping to protect arccos from floating-point roundoff
        cos_beta = float(np.clip(cos_beta, -1.0, 1.0))
        beta = np.arccos(cos_beta)
        beta_degrees = np.degrees(beta)
        dogleg_deg[i] = beta_degrees

        # -------------------------------------------------------------
        # 2. Ratio Factor (RF)
        # Formula: RF = (2 / beta) * tan(beta / 2)  [beta in radians]
        # When beta -> 0, RF -> 1.0 (approaches tangential / balanced method)
        # -------------------------------------------------------------
        if beta < 1e-4:
            rf = 1.0
        else:
            rf = (2.0 / beta) * np.tan(beta / 2.0)

        # -------------------------------------------------------------
        # 3. Coordinate Increments (Delta TVD, Delta North, Delta East)
        # Formula: dTVD = (dMD / 2) * (cos(I1) + cos(I2)) * RF
        # Formula: dN   = (dMD / 2) * (sin(I1)*cos(A1) + sin(I2)*cos(A2)) * RF
        # Formula: dE   = (dMD / 2) * (sin(I1)*sin(A1) + sin(I2)*sin(A2)) * RF
        # -------------------------------------------------------------
        d_tvd[i] = (d_md / 2.0) * (np.cos(i1) + np.cos(i2)) * rf
        d_north[i] = (d_md / 2.0) * (np.sin(i1) * np.cos(a1) + np.sin(i2) * np.cos(a2)) * rf
        d_east[i] = (d_md / 2.0) * (np.sin(i1) * np.sin(a1) + np.sin(i2) * np.sin(a2)) * rf

        # -------------------------------------------------------------
        # 4. Dogleg Severity (DLS) normalized to deg / 100 ft
        # Formula: DLS = (beta_deg / dMD) * 100
        # -------------------------------------------------------------
        dls[i] = (beta_degrees / d_md) * 100.0

        # Cumulative position integration
        tvd[i] = tvd[i - 1] + d_tvd[i]
        north[i] = north[i - 1] + d_north[i]
        east[i] = east[i - 1] + d_east[i]

    # -----------------------------------------------------------------
    # 5. Horizontal Displacement / Closure Distance (HD)
    # Formula: HD = sqrt(North^2 + East^2)
    # -----------------------------------------------------------------
    disp = np.sqrt(north**2 + east**2)

    df["Delta_TVD"] = np.round(d_tvd, 2)
    df["Delta_N"] = np.round(d_north, 2)
    df["Delta_E"] = np.round(d_east, 2)
    df["TVD_ft"] = np.round(tvd, 2)
    df["North_ft"] = np.round(north, 2)
    df["East_ft"] = np.round(east, 2)
    df["Disp_ft"] = np.round(disp, 2)
    df["Dogleg_deg"] = np.round(dogleg_deg, 3)
    df["DLS_deg_100ft"] = np.round(dls, 2)

    return df


def load_and_compute_trajectory(csv_path: str) -> pd.DataFrame:
    """
    Loads survey CSV file and executes Minimum Curvature calculation.

    Parameters
    ----------
    csv_path : str
        Path to directional survey CSV file.

    Returns
    -------
    pd.DataFrame
        Calculated directional wellbore trajectory.
    """
    df = pd.read_csv(csv_path)
    return compute_minimum_curvature(df)


def get_trajectory_summary(df: pd.DataFrame) -> Dict[str, float]:
    """
    Returns high-level summary KPIs of the directional wellbore.

    Returns
    -------
    dict
        Total MD, Final TVD, Total Departure, Max DLS, Final Inc, Final Azi.
    """
    last_row = df.iloc[-1]
    return {
        "Total_MD_ft": float(last_row["MD_ft"]),
        "Final_TVD_ft": float(last_row["TVD_ft"]),
        "Total_Disp_ft": float(last_row["Disp_ft"]),
        "Final_North_ft": float(last_row["North_ft"]),
        "Final_East_ft": float(last_row["East_ft"]),
        "Max_DLS_deg_100ft": float(df["DLS_deg_100ft"].max()),
        "Final_Inc_deg": float(last_row["Inc_deg"]),
        "Final_Azi_deg": float(last_row["Azi_deg"]),
    }

