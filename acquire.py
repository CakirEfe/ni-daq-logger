# ============================================================
# acquire.py
# NI USB-6212 | 2x Accelerometers + 1x Microphone Logger
# CSV: accelerometers in m/s², microphone in V (and Pa if set)
# ============================================================

import os
import json
from datetime import datetime

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import nidaqmx as daq
from nidaqmx.constants import Edge, AcquisitionType, TerminalConfiguration

# ============================================================
# CONFIG — edit everything in this section before running
# ============================================================

BASE_SAVE_DIR = r"D:\BearingData"          # root folder for all sessions

# --- DAQ device ---
DEVICE         = "Dev1"                    # NI device name (check NI MAX)
ACCEL_CHANNELS = [f"Dev1/ai0", f"Dev1/ai1"]
ACCEL_NAMES    = ["accel_1", "accel_2"]
MIC_CHANNEL    = "Dev1/ai2"
MIC_NAME       = "mic"

# --- Acquisition ---
FS             = 51200.0    # sample rate (Hz)
DURATION_S     = 10.0       # recording duration (s)
MIN_V          = -10.0      # DAQ input range min (V)
MAX_V          =  10.0      # DAQ input range max (V)
WIRING_MODE    = "differential"  # "differential" | "rse" | "nrse"

# --- Accelerometer sensitivity ---
# Volts per g at the DAQ input (after signal conditioner), e.g. 0.1 for 100 mV/g
ACCEL_V_PER_G  = 0.1        # must be > 0
G0             = 9.80665    # m/s² per g

# --- Microphone conversion (optional — set one or leave both None) ---
MIC_V_PER_PA   = None       # e.g. 0.05 for 50 mV/Pa
MIC_PA_PER_V   = None       # inverse alternative; ignored if MIC_V_PER_PA is set

# --- Preview plot ---
PLOT_SECONDS   = 1.0        # how many seconds to show in the preview
SAVE_PLOT      = True

# ============================================================
# END OF CONFIG
# ============================================================


def resolve_terminal_config(mode: str):
    """Return the TerminalConfiguration enum matching the requested wiring mode."""
    mode = mode.strip().lower()
    candidates = {
        "differential": ["DIFFERENTIAL", "Differential", "DIFF", "Diff",
                         "PSEUDODIFFERENTIAL", "PseudoDiff", "PSEUDO_DIFF"],
        "rse":          ["RSE", "Rse", "REFERENCEDSINGLEENDED", "ReferencedSingleEnded"],
        "nrse":         ["NRSE", "Nrse", "NONREFERENCEDSINGLEENDED", "NonReferencedSingleEnded"],
    }
    for name in candidates.get(mode, []):
        if hasattr(TerminalConfiguration, name):
            return getattr(TerminalConfiguration, name)
    return None


def acquire():
    assert len(ACCEL_CHANNELS) == len(ACCEL_NAMES), \
        "ACCEL_CHANNELS and ACCEL_NAMES must have the same length."
    if not ACCEL_V_PER_G or ACCEL_V_PER_G <= 0:
        raise ValueError("ACCEL_V_PER_G must be a positive number.")

    term_cfg = resolve_terminal_config(WIRING_MODE)
    print("TerminalConfiguration members available:")
    print([x for x in dir(TerminalConfiguration) if not x.startswith("_")])
    print(f"\nRequested wiring mode : {WIRING_MODE}")
    print(f"Resolved terminal_config: {term_cfg if term_cfg is not None else 'DEFAULT (not set)'}")

    all_channels = ACCEL_CHANNELS + [MIC_CHANNEL]
    all_names    = ACCEL_NAMES    + [MIC_NAME]
    N            = int(FS * DURATION_S)

    # --- create session folder ---
    os.makedirs(BASE_SAVE_DIR, exist_ok=True)
    session_name = datetime.now().strftime("%Y%m%d-%H%M%S_usb6212_2accel_1mic")
    session_dir  = os.path.join(BASE_SAVE_DIR, session_name)
    os.makedirs(session_dir, exist_ok=True)

    # --- acquire ---
    with daq.Task() as task:
        for ch in all_channels:
            kwargs = dict(min_val=MIN_V, max_val=MAX_V)
            if term_cfg is not None:
                kwargs["terminal_config"] = term_cfg
            task.ai_channels.add_ai_voltage_chan(ch, **kwargs)

        task.timing.cfg_samp_clk_timing(
            rate=FS,
            source="",
            active_edge=Edge.RISING,
            sample_mode=AcquisitionType.FINITE,
            samps_per_chan=N,
        )
        task.start()
        data = task.read(number_of_samples_per_channel=N,
                         timeout=max(10, DURATION_S + 5))

    data = np.asarray(data, dtype=float)
    if data.ndim == 1:
        data = data.reshape(1, -1)
    if data.shape[0] != len(all_channels):
        raise RuntimeError(f"Expected {len(all_channels)} channels, got {data.shape[0]}")

    accel_V = data[:len(ACCEL_CHANNELS), :]
    mic_V   = data[len(ACCEL_CHANNELS), :]

    print("\nMin/Max per channel (V):")
    for i, name in enumerate(all_names):
        print(f"  {name}: {data[i].min():.6f}  to  {data[i].max():.6f}")

    t = np.arange(N) / FS

    # --- convert ---
    accel_ms2 = (accel_V / ACCEL_V_PER_G) * G0

    if MIC_V_PER_PA is not None and MIC_V_PER_PA > 0:
        mic_Pa         = mic_V / MIC_V_PER_PA
        mic_plot       = mic_Pa
        mic_ylabel     = "Pressure (Pa)"
        mic_plot_suffix = "pa"
    elif MIC_PA_PER_V is not None and MIC_PA_PER_V > 0:
        mic_Pa         = mic_V * MIC_PA_PER_V
        mic_plot       = mic_Pa
        mic_ylabel     = "Pressure (Pa)"
        mic_plot_suffix = "pa"
    else:
        mic_Pa         = None
        mic_plot       = mic_V
        mic_ylabel     = "Voltage (V)  — set MIC_V_PER_PA or MIC_PA_PER_V to get Pa"
        mic_plot_suffix = "volts"

    # --- preview plots ---
    plot_N = min(N, int(PLOT_SECONDS * FS))

    fig1, ax1 = plt.subplots(figsize=(10, 4))
    for i, name in enumerate(ACCEL_NAMES):
        ax1.plot(t[:plot_N], accel_ms2[i, :plot_N], label=name, linewidth=0.8)
    ax1.set_title(f"Accelerometer preview (first {plot_N/FS:.2f} s) | {session_name}")
    ax1.set_xlabel("Time (s)")
    ax1.set_ylabel("Acceleration (m/s²)")
    ax1.grid(True)
    ax1.legend()
    fig1.tight_layout()
    if SAVE_PLOT:
        path = os.path.join(session_dir, "preview_accel_m_s2.png")
        fig1.savefig(path, dpi=200)
        print(f"Saved accel plot: {path}")
    plt.show()

    fig2, ax2 = plt.subplots(figsize=(10, 4))
    ax2.plot(t[:plot_N], mic_plot[:plot_N], label=MIC_NAME, linewidth=0.8)
    ax2.set_title(f"Microphone preview (first {plot_N/FS:.2f} s) | {session_name}")
    ax2.set_xlabel("Time (s)")
    ax2.set_ylabel(mic_ylabel)
    ax2.grid(True)
    ax2.legend()
    fig2.tight_layout()
    if SAVE_PLOT:
        path = os.path.join(session_dir, f"preview_mic_{mic_plot_suffix}.png")
        fig2.savefig(path, dpi=200)
        print(f"Saved mic plot: {path}")
    plt.show()

    # --- save CSV ---
    df = pd.DataFrame({"t_s": t})
    for i, name in enumerate(ACCEL_NAMES):
        df[f"{name}_m_s2"] = accel_ms2[i]
    df[f"{MIC_NAME}_V"] = mic_V
    if mic_Pa is not None:
        df[f"{MIC_NAME}_Pa"] = mic_Pa

    csv_path = os.path.join(session_dir, "accel.csv")
    df.to_csv(csv_path, index=False)

    # --- save raw arrays ---
    np.save(os.path.join(session_dir, "accel_V.npy"),    accel_V)
    np.save(os.path.join(session_dir, "accel_m_s2.npy"), accel_ms2)
    np.save(os.path.join(session_dir, "mic_V.npy"),      mic_V)
    np.save(os.path.join(session_dir, "t_s.npy"),        t)
    if mic_Pa is not None:
        np.save(os.path.join(session_dir, "mic_Pa.npy"), mic_Pa)

    # --- metadata ---
    meta = {
        "device":                DEVICE,
        "accel_channels":        ACCEL_CHANNELS,
        "accel_names":           ACCEL_NAMES,
        "mic_channel":           MIC_CHANNEL,
        "mic_name":              MIC_NAME,
        "fs_hz":                 FS,
        "duration_s":            DURATION_S,
        "samples_per_channel":   N,
        "range_v":               [MIN_V, MAX_V],
        "requested_wiring_mode": WIRING_MODE,
        "resolved_terminal_config": str(term_cfg) if term_cfg is not None else None,
        "accel_v_per_g":         ACCEL_V_PER_G,
        "g0_m_s2":               G0,
        "mic_v_per_pa":          MIC_V_PER_PA,
        "mic_pa_per_v":          MIC_PA_PER_V,
        "base_save_dir":         BASE_SAVE_DIR,
        "session_dir":           session_dir,
        "notes":                 "CSV contains accel in m/s² only; raw volts saved as .npy.",
    }
    with open(os.path.join(session_dir, "meta.json"), "w") as f:
        json.dump(meta, f, indent=2)

    print(f"\nSaved session: {session_dir}")
    print(f"  {csv_path}")
    print("  accel_V.npy, accel_m_s2.npy, mic_V.npy, t_s.npy")
    print("  mic_Pa.npy (if mic conversion set)")
    print("  meta.json")
    print("  preview plots (if SAVE_PLOT=True)")


if __name__ == "__main__":
    acquire()
