# Bearing Data Logger

Data acquisition and analysis scripts for a bearing test rig using an **NI USB-6212** DAQ with two accelerometers and one microphone.

---

## Scripts

| File | Purpose |
|---|---|
| `acquire.py` | Acquires data from the DAQ and saves it to a timestamped session folder |
| `fft_view.py` | Plots the amplitude spectrum of any column in a saved CSV |
| `bearing_analysis.py` | Overlays bearing defect frequency harmonics (FTF, BSF, BPFO, BPFI) on the FFT |

---

## Hardware

- **DAQ**: NI USB-6212
- **Channels used**: `ai0` (accel 1), `ai1` (accel 2), `ai2` (mic)
- **Accelerometers**: ICP/IEPE type — connect through a signal conditioner; set `ACCEL_V_PER_G` to match conditioner output sensitivity
- **Microphone**: Voltage output mic; optionally set `MIC_V_PER_PA` or `MIC_PA_PER_V` for Pa conversion

---

## Requirements

```
nidaqmx
numpy
pandas
matplotlib
```

Install with:

```bash
pip install nidaqmx numpy pandas matplotlib
```

NI-DAQmx driver also required — download from [ni.com/downloads](https://www.ni.com/en/support/downloads/drivers/download.ni-daq-mx.html).

---

## Quickstart

### 1. Acquire data

Open `acquire.py` and set the **CONFIG** section at the top:

```python
BASE_SAVE_DIR  = r"D:\BearingData"   # where sessions are saved
DEVICE         = "Dev1"              # NI device name — check NI MAX
ACCEL_V_PER_G  = 0.1                 # conditioner sensitivity (V/g)
FS             = 51200.0             # sample rate (Hz)
DURATION_S     = 10.0                # recording length (s)
WIRING_MODE    = "differential"      # "differential" | "rse" | "nrse"
```

Run it:

```bash
python acquire.py
```

Each run creates a timestamped subfolder under `BASE_SAVE_DIR`, e.g.:

```
D:\BearingData\
└── 20250401-143022_usb6212_2accel_1mic\
    ├── accel.csv          # time + accel (m/s²) + mic (V, Pa)
    ├── accel_V.npy        # raw voltages, shape (2, N)
    ├── accel_m_s2.npy     # converted accelerations, shape (2, N)
    ├── mic_V.npy          # mic voltage, shape (N,)
    ├── t_s.npy            # time vector, shape (N,)
    ├── mic_Pa.npy         # mic pressure (only if conversion set)
    ├── meta.json          # all acquisition parameters
    ├── preview_accel_m_s2.png
    └── preview_mic_*.png
```

### 2. View the FFT

Open `fft_view.py` and set the path and column:

```python
CSV_PATH   = r"D:\BearingData\Run4\accel.csv"
SIGNAL_COL = "accel_1_m_s2"
MAX_FREQ   = 1000    # Hz
```

```bash
python fft_view.py
```

### 3. Bearing defect analysis

Open `bearing_analysis.py` and set your bearing geometry and shaft speed:

```python
SHAFT_SPEED_HZ    = 15.0    # Hz
NUM_BALLS         = 9
PD_MM             = 38.52   # pitch diameter (mm)
BD_MM             = 7.94    # ball diameter (mm)
CONTACT_ANGLE_DEG = 0.0
```

```bash
python bearing_analysis.py
```

Four separate plots are produced — one per defect type (FTF, BSF, BPFO, BPFI) — with harmonic marker lines overlaid on the amplitude spectrum.

---

## Output CSV columns

| Column | Unit | Description |
|---|---|---|
| `t_s` | s | Time |
| `accel_1_m_s2` | m/s² | Accelerometer 1 |
| `accel_2_m_s2` | m/s² | Accelerometer 2 |
| `mic_V` | V | Microphone voltage |
| `mic_Pa` | Pa | Microphone pressure *(only if conversion set)* |

Raw voltage arrays are also saved as `.npy` for auditing or reprocessing.

---

## Notes

- Device name (`Dev1`) can be verified and changed in **NI Measurement & Automation Explorer (NI MAX)**.
- `ACCEL_V_PER_G` must match the output sensitivity of your signal conditioner, not the sensor's own spec sheet value.
- The FFT uses a **Hann window** with coherent-gain correction. Amplitudes are approximate — suitable for relative comparison and peak identification, not absolute calibrated measurement.
