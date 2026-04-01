# ============================================================
# bearing_analysis.py
# FFT with bearing defect frequency harmonic overlays
# Supports: FTF, BSF, BPFO, BPFI
# ============================================================

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

# ============================================================
# CONFIG — edit everything in this section before running
# ============================================================

CSV_PATH   = r"D:\BearingData\Run4\accel.csv"   # path to your session CSV
TIME_COL   = "t_s"                               # time column name
SIGNAL_COL = "accel_1_m_s2"                      # column to analyse

# --- Operating speed ---
SHAFT_SPEED_HZ = 15.0           # shaft rotation frequency (Hz)

# --- Bearing geometry ---
# For ER16 family (replace with your bearing's datasheet values)
NUM_BALLS  = 9                  # number of rolling elements (Z)
PD_MM      = 38.52              # pitch diameter (mm)
BD_MM      = 7.94               # ball/roller diameter (mm)
CONTACT_ANGLE_DEG = 0.0         # contact angle (degrees); 0 for deep-groove

# --- Plot settings ---
NUM_HARMONICS  = 12             # how many harmonics to overlay per defect type
MAX_FREQ_PLOT  = 1000           # Hz — set None for full range
LINE_ALPHA     = 0.85

# ============================================================
# END OF CONFIG
# ============================================================


def estimate_fs(t: np.ndarray) -> float:
    dt = np.diff(t)
    dt_med = np.median(dt[np.isfinite(dt)])
    if not np.isfinite(dt_med) or dt_med <= 0:
        raise ValueError("Bad time column: non-positive or non-finite dt.")
    return 1.0 / dt_med


def amplitude_spectrum(x: np.ndarray, fs: float):
    """Return (frequencies, amplitudes) using a Hann window."""
    x = x - np.mean(x)
    N = len(x)
    w = np.hanning(N)
    X = np.fft.rfft(x * w)
    f = np.fft.rfftfreq(N, d=1.0 / fs)

    coherent_gain = 0.5
    amp = (2.0 / N) * np.abs(X) / coherent_gain
    amp[0] *= 0.5
    return f, amp


def bearing_defect_freqs(fr, Z, ball_d, pitch_d, contact_angle_deg=0.0) -> dict:
    """
    Compute the four fundamental bearing defect frequencies.

    Parameters
    ----------
    fr               : shaft rotation frequency (Hz)
    Z                : number of rolling elements
    ball_d           : ball/roller diameter (mm)
    pitch_d          : pitch diameter (mm)
    contact_angle_deg: contact angle (degrees)

    Returns
    -------
    dict with keys: FTF, BSF, BPFO, BPFI (all in Hz)
    """
    ca  = np.deg2rad(contact_angle_deg)
    c   = (ball_d / pitch_d) * np.cos(ca)
    return {
        "FTF":  0.5 * fr * (1.0 - c),
        "BSF":  (pitch_d / (2.0 * ball_d)) * fr * (1.0 - c**2),
        "BPFO": (Z / 2.0) * fr * (1.0 - c),
        "BPFI": (Z / 2.0) * fr * (1.0 + c),
    }


def overlay_harmonics(ax, f0, n_harm, fmax=None, alpha=0.85):
    for n in range(1, n_harm + 1):
        fn = n * f0
        if fmax is not None and fn > fmax:
            break
        ax.axvline(fn, linestyle=":", linewidth=1.4, alpha=alpha)


def main():
    df = pd.read_csv(CSV_PATH)

    for col in (TIME_COL, SIGNAL_COL):
        if col not in df.columns:
            raise ValueError(f"Column '{col}' not found. Available: {list(df.columns)}")

    t = df[TIME_COL].to_numpy(dtype=float)
    x = df[SIGNAL_COL].to_numpy(dtype=float)

    fs       = estimate_fs(t)
    duration = t[-1] - t[0]
    f, amp   = amplitude_spectrum(x, fs)

    mask = f <= MAX_FREQ_PLOT if MAX_FREQ_PLOT is not None else np.ones(len(f), dtype=bool)
    f_plot, amp_plot = f[mask], amp[mask]

    defect = bearing_defect_freqs(
        fr=SHAFT_SPEED_HZ,
        Z=NUM_BALLS,
        ball_d=BD_MM,
        pitch_d=PD_MM,
        contact_angle_deg=CONTACT_ANGLE_DEG,
    )

    print(f"Estimated fs : {fs:.6f} Hz")
    print(f"Duration     : {duration:.3f} s  |  N = {len(x)}")
    print(f"\nDefect frequencies at fr = {SHAFT_SPEED_HZ} Hz:")
    for name, freq in defect.items():
        print(f"  {name:4s}: {freq:.4f} Hz  ({freq/SHAFT_SPEED_HZ:.4f}×)")

    title_base = (
        f"{SIGNAL_COL} | fs≈{fs:.1f} Hz | "
        f"T≈{duration:.1f} s | fr={SHAFT_SPEED_HZ:.2f} Hz"
    )

    for name, f0 in defect.items():
        fig, ax = plt.subplots(figsize=(10, 4))
        ax.plot(f_plot, amp_plot, linewidth=0.8)
        ax.set_xlabel("Frequency (Hz)")
        ax.set_ylabel("Amplitude (approx.)")
        ax.set_title(f"{name} harmonics — {title_base}\n{name} = {f0:.4f} Hz")
        overlay_harmonics(ax, f0, NUM_HARMONICS, fmax=MAX_FREQ_PLOT, alpha=LINE_ALPHA)
        ax.grid(True)
        fig.tight_layout()

    plt.show()


if __name__ == "__main__":
    main()
