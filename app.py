import streamlit as st
import numpy as np
import plotly.graph_objects as go
import heapq
import io
from PIL import Image

# --- PAGE SETUP ---
st.set_page_config(page_title="Pragyan-Path | Chandrayaan Rover Simulator", layout="wide")
st.title("🛰️ Pragyan-Path: Autonomous Lunar South Pole Safe-Route Simulator")
st.markdown("**ASTRA 2026** | **Domains:** Indian Space Missions (ISRO) & Lunar Exploration | **Site:** Shiv Shakti Point (69.37°S, 32.32°E)")

# --- SIDEBAR CONTROLS ---
st.sidebar.header("🎛️ Mission & Terrain Source")
data_mode = st.sidebar.radio(
    "Elevation Data Source",
    ["Chandrayaan Presets (Simulated)", "Upload Real ISRO DEM (.csv / .tif)"]
)

grid_size = 45
cell_size = 10.0  # 1 grid cell = 10 meters (450m x 450m mission sector)
x = np.arange(grid_size)
y = np.arange(grid_size)
X, Y = np.meshgrid(x, y)

Z = None
sector_name = "Shiv Shakti Point"

if data_mode == "Upload Real ISRO DEM (.csv / .tif)":
    uploaded_file = st.sidebar.file_uploader(
        "Upload Chandrayaan-2 TMC-2 / OHRC DEM",
        type=["csv", "tif", "tiff", "png"]
    )
    if uploaded_file is not None:
        try:
            if uploaded_file.name.endswith(".csv"):
                raw_data = np.loadtxt(uploaded_file, delimiter=",")
            else:
                img = Image.open(uploaded_file).convert("L")
                raw_data = np.array(img, dtype=float)
                # Normalize image pixel values to realistic lunar elevation range (-25m to +15m)
                raw_data = (raw_data - raw_data.min()) / (raw_data.max() - raw_data.min() + 1e-6) * 40.0 - 25.0

            # Resample uploaded DEM to 45x45 grid for real-time 3D & A* performance
            row_idx = np.linspace(0, raw_data.shape[0] - 1, grid_size).astype(int)
            col_idx = np.linspace(0, raw_data.shape[1] - 1, grid_size).astype(int)
            Z = raw_data[np.ix_(row_idx, col_idx)]
            sector_name = f"Uploaded ISRO DEM ({uploaded_file.name})"
            st.sidebar.success("✅ ISRO DEM loaded successfully!")
        except Exception as e:
            st.sidebar.error(f"Could not read file: {e}. Falling back to preset.")

if Z is None:
    presets = {
        "Sector A: Shiv Shakti Point (Chandrayaan-3)": (1, [(16, 16, 6.5, 28.0), (28, 25, 7.5, 34.0), (14, 34, 5.5, 24.0), (33, 12, 6.0, 26.0), (23, 37, 4.5, 20.0)]),
        "Sector B: Shackleton Rim Ridge": (2, [(22, 22, 9.0, 38.0), (11, 18, 5.5, 24.0), (34, 30, 6.5, 28.0), (18, 35, 5.0, 22.0)]),
        "Sector C: Malapert Crater Field": (3, [(13, 13, 6.0, 26.0), (25, 16, 6.0, 29.0), (18, 27, 6.5, 31.0), (32, 29, 6.0, 27.0), (28, 38, 5.0, 22.0)])
    }
    sector_name = st.sidebar.selectbox("Select Lunar Sector", list(presets.keys()))
    seed, craters = presets[sector_name]
    np.random.seed(seed)

    # Gentle lunar plains + micro-roughness
    Z = 4.0 * np.sin(X / 8.0) * np.cos(Y / 8.0) + np.random.normal(0, 0.35, (grid_size, grid_size))

    # Realistic Lunar Craters (bowls + raised ejecta rims)
    for cx, cy, radius_cells, depth_m in craters:
        dist_m = np.sqrt((X - cx)**2 + (Y - cy)**2) * cell_size
        r_m = radius_cells * cell_size
        Z -= depth_m * np.exp(-(dist_m**2) / (2 * (r_m / 2.2)**2))
        Z += (depth_m * 0.22) * np.exp(-((dist_m - r_m)**2) / (2 * (r_m / 4.5)**2))

st.sidebar.markdown("---")
st.sidebar.header("🤖 Pragyan Rover Limits")
max_slope = st.sidebar.slider("Max Safe Slope (Degrees)", 8, 35, 18)
avoid_shadows = st.sidebar.checkbox("Avoid Solar Shadow Zones (Solar Power Safe)", value=True)

st.sidebar.header("☀️ Lunar South Pole Sunlight")
sun_elevation = st.sidebar.slider("Sun Elevation Angle (Degrees)", 4, 35, 14)
sun_azimuth = st.sidebar.slider("Sun Direction / Azimuth (Degrees)", 0, 360, 45)

st.sidebar.header("📍 Coordinates (0 to 44)")
c1, c2 = st.sidebar.columns(2)
start_x = c1.number_input("Start X", 0, grid_size - 1, 4)
start_y = c2.number_input("Start Y", 0, grid_size - 1, 4)
goal_x = c1.number_input("Target X", 0, grid_size - 1, 39)
goal_y = c2.number_input("Target Y", 0, grid_size - 1, 38)

# --- 1. SLOPE CALCULATION (Real Meter Scale) ---
dy, dx = np.gradient(Z, cell_size)
slope_deg = np.degrees(np.arctan(np.sqrt(dx**2 + dy**2)))

# --- 2. SOLAR SHADOW RAYCASTING ---
sun_el_rad = np.radians(sun_elevation)
sun_az_rad = np.radians(sun_azimuth)
step_x = np.cos(sun_az_rad)
step_y = np.sin(sun_az_rad)

in_shadow = np.zeros((grid_size, grid_size), dtype=bool)
for s in range(1, grid_size):
    rx = np.round(X + s * step_x).astype(int)
    ry = np.round(Y + s * step_y).astype(int)
    valid = (rx >= 0) & (rx < grid_size) & (ry >= 0) & (ry < grid_size)
    if not np.any(valid):
        break
    dist_m = s * cell_size
    blocking_height = Z[valid] + dist_m * np.tan(sun_el_rad)
    in_shadow[valid] |= (Z[ry[valid], rx[valid]] > blocking_height)

# --- 3. DIRECT STRAIGHT-LINE PATH (BASELINE FOR COMPARISON) ---
num_direct = max(abs(goal_x - start_x), abs(goal_y - start_y)) + 1
direct_x = np.round(np.linspace(start_x, goal_x, num_direct)).astype(int)
direct_y = np.round(np.linspace(start_y, goal_y, num_direct)).astype(int)
direct_slopes = [slope_deg[r, c] for r, c in zip(direct_y, direct_x)]
direct_shadows = [in_shadow[r, c] for r, c in zip(direct_y, direct_x)]
direct_max_slope = max(direct_slopes)
direct_shadow_pct = (sum(direct_shadows) / len(direct_shadows)) * 100
direct_dist_m = np.sqrt((goal_x - start_x)**2 + (goal_y - start_y)**2) * cell_size
direct_safe = (direct_max_slope <= max_slope) and (not avoid_shadows or direct_shadow_pct == 0)

# --- 4. A* AUTONOMOUS SAFE-ROUTE ALGORITHM ---
start = (int(start_y), int(start_x))
goal = (int(goal_y), int(goal_x))

open_set = []
heapq.heappush(open_set, (0.0, start))
came_from = {}
g_score = {start: 0.0}
directions = [(-1, 0), (1, 0), (0, -1), (0, 1), (-1, -1), (-1, 1), (1, -1), (1, 1)]

path = []
while open_set:
    _, current = heapq.heappop(open_set)
    if current == goal:
        while current in came_from:
            path.append(current)
            current = came_from[current]
        path.append(start)
        path.reverse()
        break

    for dr, dc in directions:
        nr, nc = current[0] + dr, current[1] + dc
        if 0 <= nr < grid_size and 0 <= nc < grid_size:
            # Skip hazardous slopes
            if slope_deg[nr, nc] > max_slope:
                continue
            # Skip shadowed pits if solar protection is enabled (allow entering goal/leaving start)
            if avoid_shadows and in_shadow[nr, nc] and (nr, nc) != goal:
                continue

            step_dist = 1.414 if (dr != 0 and dc != 0) else 1.0
            slope_penalty = (slope_deg[nr, nc] / max_slope) * 1.8
            tentative_g = g_score[current] + step_dist + slope_penalty

            if (nr, nc) not in g_score or tentative_g < g_score[(nr, nc)]:
                came_from[(nr, nc)] = current
                g_score[(nr, nc)] = tentative_g
                h = np.sqrt((nr - goal[0])**2 + (nc - goal[1])**2)
                heapq.heappush(open_set, (tentative_g + h, (nr, nc)))

# --- 5. TOP MISSION TELEMETRY KPIs ---
col1, col2, col3, col4, col5 = st.columns(5)
if path:
    path_slopes = [slope_deg[r, c] for r, c in path]
    path_elevs = [Z[r, c] for r, c in path]
    path_shadows = [in_shadow[r, c] for r, c in path]
    # Exact distance in meters
    safe_dist_m = 0.0
    for i in range(1, len(path)):
        dr = path[i][0] - path[i-1][0]
        dc = path[i][1] - path[i-1][1]
        safe_dist_m += (14.14 if (dr != 0 and dc != 0) else 10.0)

    max_path_slope = max(path_slopes)
    shadow_pct = (sum(path_shadows) / len(path_shadows)) * 100
    # Pragyan speed ~ 1 cm/s = 36 m/hour
    est_hours = safe_dist_m / 36.0
    est_battery = min(100.0, round(safe_dist_m * 0.065 + max_path_slope * 0.45 + shadow_pct * 0.3, 1))

    col1.metric("Navigation Status", "✅ SAFE ROUTE")
    col2.metric("Safe Distance", f"{safe_dist_m:.0f} m", delta=f"+{safe_dist_m - direct_dist_m:.0f}m vs direct", delta_color="off")
    col3.metric("Max Route Slope", f"{max_path_slope:.1f}°", delta=f"{max_path_slope - direct_max_slope:.1f}° vs direct", delta_color="inverse")
    col4.metric("Sunlit Coverage", f"{100 - shadow_pct:.0f}%")
    col5.metric("Est. Drive Time", f"{est_hours:.1f} hrs", delta=f"~{est_battery}% Battery", delta_color="off")
else:
    col1.metric("Navigation Status", "❌ BLOCKED")
    col2.metric("Max Slope Limit", f"{max_slope}°")
    col3.metric("Sun Elevation", f"{sun_elevation}°")
    col4.metric("Direct Max Slope", f"{direct_max_slope:.1f}°")
    col5.metric("Action", "Adjust Limits")
    st.error("⚠️ No safe route found! All paths either exceed the rover's slope limit or pass through freezing crater shadows. Try raising **Max Safe Slope**, raising **Sun Elevation Angle**, or unchecking **Avoid Solar Shadow Zones**.")

# --- DIRECT VS SAFE COMPARISON BANNER ---
if path:
    direct_status = "✅ Safe" if direct_safe else "❌ UNSAFE (Crash / Shadow Risk)"
    st.info(
        f"**Route Comparison — Direct Straight Line:** {direct_dist_m:.0f}m | Max Slope: **{direct_max_slope:.1f}°** | Shadow: **{direct_shadow_pct:.0f}%** ({direct_status})  \n"
        f"**Pragyan-Path Autonomous Route:** {safe_dist_m:.0f}m | Max Slope: **{max_path_slope:.1f}°** | Shadow: **{shadow_pct:.0f}%** (✅ Mission-Safe)"
    )

# --- 6. VIEW SWITCHER (Replaces st.tabs to prevent 3D WebGL blank bug) ---
view_page = st.radio(
    "Select Mission View",
    ["🌑 3D Lunar Terrain & Path", "🗺️ 2D Hazard Map & Telemetry", "🇮🇳 ISRO Mission & Data Specs"],
    horizontal=True,
    label_visibility="collapsed"
)
st.markdown("---")

if view_page == "🌑 3D Lunar Terrain & Path":
    view_col1, view_col2 = st.columns([2, 1])
    surface_mode = view_col1.radio(
        "3D Surface Overlay Mode",
        ["Lunar Terrain + Solar Shadows", "Slope Hazard Heatmap (Green=Safe, Red=Danger)"],
        horizontal=True
    )
    show_direct = view_col2.checkbox("Show Unsafe Direct Line", value=True)

    fig3d = go.Figure()

    if surface_mode == "Lunar Terrain + Solar Shadows":
        surface_color = np.where(in_shadow, Z.min() - 18.0, Z)
        cscale = "Gray"
        show_bar = False
        bar_title = ""
    else:
        surface_color = slope_deg
        cscale = "RdYlGn_r"
        show_bar = True
        bar_title = "Slope (°)"

    fig3d.add_trace(go.Surface(
        z=Z, x=x * cell_size, y=y * cell_size,
        surfacecolor=surface_color,
        colorscale=cscale,
        showscale=show_bar,
        colorbar=dict(title=bar_title) if show_bar else None,
        opacity=0.96,
        name="Lunar Surface"
    ))

    if show_direct:
        dz = [Z[r, c] + 1.5 for r, c in zip(direct_y, direct_x)]
        fig3d.add_trace(go.Scatter3d(
            x=direct_x * cell_size, y=direct_y * cell_size, z=dz,
            mode="lines",
            line=dict(color="#FF4B4B", width=4, dash="dash"),
            name="Direct Line (Baseline)"
        ))

    if path:
        py = [p[0] * cell_size for p in path]
        px = [p[1] * cell_size for p in path]
        pz = [Z[p[0], p[1]] + 1.8 for p in path]
        fig3d.add_trace(go.Scatter3d(
            x=px, y=py, z=pz,
            mode="lines+markers",
            line=dict(color="#00FFCC", width=7),
            marker=dict(size=3, color="#00FFCC"),
            name="Pragyan-Path Safe Route"
        ))

    fig3d.add_trace(go.Scatter3d(
        x=[start_x * cell_size], y=[start_y * cell_size], z=[Z[start_y, start_x] + 3.0],
        mode="markers", marker=dict(size=9, color="#00FF00"), name="Vikram Lander (Start)"
    ))
    fig3d.add_trace(go.Scatter3d(
        x=[goal_x * cell_size], y=[goal_y * cell_size], z=[Z[goal_y, goal_x] + 3.0],
        mode="markers", marker=dict(size=9, color="#FFD700", symbol="diamond"), name="Target Sample Site"
    ))

    fig3d.update_layout(
        title=f"3D Interactive Lunar Terrain — {sector_name}",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        scene=dict(
            xaxis_title="East-West (m)",
            yaxis_title="North-South (m)",
            zaxis_title="Elevation (m)",
            bgcolor="#070B14",
            aspectratio=dict(x=1, y=1, z=0.35)
        ),
        margin=dict(l=0, r=0, b=0, t=40),
        height=580
    )
    st.plotly_chart(fig3d, use_container_width=True, key="lunar_3d")

elif view_page == "🗺️ 2D Hazard Map & Telemetry":
    map_col, chart_col = st.columns(2)

    with map_col:
        hazard_grid = np.zeros((grid_size, grid_size))
        hazard_grid[in_shadow] = 1
        hazard_grid[slope_deg > max_slope] = 2

        fig2d = go.Figure()
        fig2d.add_trace(go.Heatmap(
            z=hazard_grid,
            x=x * cell_size,
            y=y * cell_size,
            colorscale=[[0.0, "#1E4D2B"], [0.5, "#1B2A4A"], [1.0, "#B91C1C"]],
            showscale=False,
            hovertemplate="X: %{x}m<br>Y: %{y}m<br>Zone Code: %{z}<extra></extra>"
        ))

        fig2d.add_trace(go.Scatter(
            x=direct_x * cell_size, y=direct_y * cell_size,
            mode="lines", line=dict(color="#FF6B6B", width=2, dash="dash"),
            name="Direct Line"
        ))

        if path:
            fig2d.add_trace(go.Scatter(
                x=[p[1] * cell_size for p in path],
                y=[p[0] * cell_size for p in path],
                mode="lines", line=dict(color="#00FFCC", width=4),
                name="Safe Route"
            ))

        fig2d.add_trace(go.Scatter(
            x=[start_x * cell_size, goal_x * cell_size],
            y=[start_y * cell_size, goal_y * cell_size],
            mode="markers",
            marker=dict(size=12, color=["#00FF00", "#FFD700"]),
            name="Start / Target"
        ))

        fig2d.update_layout(
            title="2D Hazard Classification (Green=Safe | Navy=Shadow | Red=Steep)",
            xaxis_title="East-West (m)",
            yaxis_title="North-South (m)",
            height=480
        )
        st.plotly_chart(fig2d, use_container_width=True, key="lunar_2d")

    with chart_col:
        if path:
            steps_m = np.linspace(0, safe_dist_m, len(path))
            fig_prof = go.Figure()
            fig_prof.add_trace(go.Scatter(
                x=steps_m, y=path_slopes,
                mode="lines", name="Safe Route Slope (°)",
                line=dict(color="#00FFCC", width=3),
                fill="tozeroy", fillcolor="rgba(0, 255, 204, 0.15)"
            ))
            fig_prof.add_hline(
                y=max_slope, line_dash="dash", line_color="#FF4B4B",
                annotation_text=f"Rover Max Safe Limit ({max_slope}°)"
            )
            fig_prof.update_layout(
                title="Slope Telemetry Along Safe Rover Path",
                xaxis_title="Distance Traveled (m)",
                yaxis_title="Terrain Slope (Degrees)",
                height=480
            )
            st.plotly_chart(fig_prof, use_container_width=True, key="lunar_prof")
        else:
            st.warning("Generate a valid safe path to view route slope telemetry.")

else:
    st.subheader("🇮🇳 Alignment with ISRO Chandrayaan Missions")
    st.markdown("""
    * **Target Region:** Modeled around **Shiv Shakti Point (69.37°S, 32.32°E)**, Chandrayaan-3's historic Lunar South Pole landing site, and candidate regions for **Chandrayaan-4 / LUPEX**.
    * **ISRO Data Compatibility:** Supports ingesting Digital Elevation Models (DEMs) in `.tif` or `.csv` formats from **ISRO's ISSDC PRADAN** portal (Chandrayaan-2 **TMC-2** Terrain Mapping Camera & **OHRC** High Resolution Camera).
    * **Real Pragyan Rover Engineering Constraints:**
        * **Mass & Drive:** 26 kg, 6-wheel rocker-bogie suspension (~1 cm/s max traverse speed).
        * **Slope Hazard Limit:** Steep crater walls (>20°) risk wheel slippage or rollover in loose lunar regolith.
        * **Solar Shadow Constraint:** At the Lunar South Pole, low sun elevation angles (5°–15°) create long freezing shadows (-180°C) where solar-powered rovers lose power.
    """)

    csv_buffer = io.StringIO()
    np.savetxt(csv_buffer, Z, delimiter=",", fmt="%.2f")
    st.download_button(
        label="⬇️ Download Current Terrain as Sample DEM (.csv)",
        data=csv_buffer.getvalue(),
        file_name="chandrayaan_sample_dem.csv",
        mime="text/csv"
    )
