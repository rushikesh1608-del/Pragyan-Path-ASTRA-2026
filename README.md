# 🛰️ Pragyan-Path — Autonomous Lunar South Pole Safe-Route Simulator
**Team Brahmastra | ASTRA 2026 Hackathon (VIT Bhopal University)**

Autonomous, GPS-free lunar rover navigation simulator modeled around **Shiv Shakti Point (69.37°S, 32.32°E)** for ISRO Chandrayaan-style missions.

## Key Features
- **ISRO DEM Ingestion:** Supports Chandrayaan-2 TMC-2 / OHRC elevation grids (`.csv` / `.tif`) alongside 3 built-in Lunar South Pole presets (Shiv Shakti Point, Shackleton Rim Ridge, Malapert Crater Field).
- **Real-Scale Slope Mapping:** Computes terrain slope gradients in degrees at meter scale to flag >20° rollover hazards.
- **Dynamic Solar Shadow Raycasting:** Simulates freezing (-180 °C) lunar shadows from adjustable sun elevation and azimuth angles.
- **Slope-Penalized A* Pathfinding:** Computes the safest, sunlit, energy-efficient route and compares it live against an unsafe direct path.
- **Interactive Mission Dashboard:** 3D lunar terrain viewer, 2D hazard map, slope telemetry graph, and live KPIs (distance, max slope, sunlit coverage, drive time, battery estimate).

## Run Locally
```bash
pip install -r requirements.txt
python -m streamlit run app.py
*(If you'd rather skip editing the README for now, just click **`Cancel changes`** in the top-right corner[span_4](start_span)[span_4](end_span).)*

---

### Step 2: Upload `app.py` and `requirements.txt`
Once you are back on your main **`Pragyan-Path-ASTRA-2026`** repo page:
1. Click the **`Add file`** dropdown button (on the right side, next to the green **`<> Code`** button) → select **`Upload files`**.
2. Drag and drop **only** these two files from `C:\Astra`:
   * **`app.py`**
   * **`requirements.txt`** *(make sure it contains `streamlit`, `numpy`, `plotly`, `pillow` on 4 separate lines)*
   *(Skip `code.py`, `app_flag.py`, and preview PNGs so the repo stays clean and doesn't expose your NASA API key.)*
3. Scroll down and click the green **`Commit changes`** button.

---

### Step 3: Deploy Your Mandatory Live Link[span_5](start_span)[span_5](end_span)
1. Open **[share.streamlit.io](https://share.streamlit.io)** and sign in with the same GitHub account (`rushikesh1608-del`[span_6](start_span)[span_6](end_span)).
2. Click **Create app** → **Deploy a public app from GitHub**.
3. Pick **`rushikesh1608-del/Pragyan-Path-ASTRA-2026`**[span_7](start_span)[span_7](end_span), branch **`main`**[span_8](start_span)[span_8](end_span), Main file path **`app.py`**, and click **Deploy**.

Wait ~60 seconds for it to build and grab your live `.streamlit.app` link. Let me know once it goes live (or send a photo if Streamlit shows any error)!
