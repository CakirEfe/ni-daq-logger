# ============================================================
# fft_view.py
# Quick amplitude spectrum viewer for a single CSV channel
# ============================================================

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

# ============================================================
# CONFIG — edit everything in this section before running
# ============================================================

CSV_PATH   = r"D:\BearingData\Run4\accel.csv"   # path to your session CSV
TIME_COL   = "t_s"                               # time column name
SIGNAL_COL = "accel_1_m_s2"                      # column to plot (e.g. accel_1_m_s2, mic_V)
MAX_FREQ   = 1000                                 # Hz — set None for full range

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

    coherent_gain = 0.5          # Hann window coherent gain
    amp = (2.0 / N) * np.abs(X) / coherent_gain
    amp[0] *= 0.5                # DC bin correction
    return f, amp


def main():
    df = pd.read_csv(CSV_PATH)

    t = df[TIME_COL].to_numpy(dtype=float)
    x = df[SIGNAL_COL].to_numpy(dtype=float)

    fs       = estimate_fs(t)
    duration = t[-1] - t[0]
    f, amp   = amplitude_spectrum(x, fs)

    print(f"Estimated fs = {fs:.3f} Hz | duration ≈ {duration:.3f} s | N = {len(x)}")

    mask = f <= MAX_FREQ if MAX_FREQ is not None else np.ones(len(f), dtype=bool)

    plt.figure(figsize=(10, 4))
    plt.plot(f[mask], amp[mask])
    plt.xlabel("Frequency (Hz)")
    plt.ylabel("Amplitude (approx.)")
    plt.title(f"FFT — {SIGNAL_COL}")
    plt.grid(True)
    plt.tight_layout()
    plt.show()


if __name__ == "__main__":
    main()
