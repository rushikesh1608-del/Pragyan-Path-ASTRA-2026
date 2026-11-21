# 🛰️ Pragyan-Path — Autonomous Lunar South Pole Safe-Route Simulator
**Team Brahmastra | ASTRA 2026 Hackathon (VIT Bhopal University)**

Autonomous, GPS-free lunar rover navigation simulator modeled around **Shiv Shakti Point (69.37°S, 32.32°E)** for ISRO Chandrayaan-style missions.

## Key Features
- **ISRO DEM Ingestion:** Supports Chandrayaan-2 TMC-2 / OHRC elevation grids (`.csv` / `.tif`) alongside 3 built-in Lunar South Pole presets (Shiv Shakti Point, Shackleton Rim Ridge, Malapert Crater Field).
- **Real-Scale Slope Mapping:** Computes terrain slope gradients in degrees at meter scale to flag >20° rollover hazards.
- **Dynamic Solar Shadow Raycasting:** Simulates freezing (-180 °C) lunar shadows from adjustable sun elevation and azimuth angles.
- **Slope-Penalized A\* Pathfinding:** Computes the safest, sunlit, energy-efficient route and compares it live against an unsafe direct path.
- **Interactive Mission Dashboard:** 3D lunar terrain viewer, 2D hazard map, slope telemetry graph, and live KPIs (distance, max slope, sunlit coverage, drive time, battery estimate).

## Run Locally
```bash
pip install -r requirements.txt
python -m streamlit run app.py
