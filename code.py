import requests

api_key = "pDdJHwzDwR8Bhch7pq7nMBGGjcHBDnkTRJcDkkmN"
url = f"https://api.nasa.gov/planetary/apod?api_key={api_key}&date=2026-11-20"


response = requests.get(url)
data = response.json()
print(data)   

print("Title:", data["title"])
print("Date:", data["date"])
print("Image URL:", data["url"])

import streamlit as st
import numpy as np
import plotly.graph_objects as go
import heapq

# Page Setup
st.set_page_config(page_title="Pragyan-Path | Lunar Rover Simulator", layout="wide")
st.title("🛰️ Pragyan-Path: Chandrayaan Lunar Safe-Route Simulator")
st.markdown("**Domains:** Indian Space Missions & Lunar Exploration | **Region:** Shiv Shakti Point (Lunar South Pole)")

# Sidebar Controls
st.sidebar.header("🎛️ Rover & Mission Parameters")
max_slope = st.sidebar.slider("Max Safe Rover Slope (Degrees)", min_value=5, max_value=35, value=18)
terrain_seed = st.sidebar.selectbox("Lunar Sector Preset", [1, 2, 3, 4], index=0)

st.sidebar.subheader("📍 Mission Coordinates (0 to 39)")
start_x = st.sidebar.slider("Start X (Lander)", 0, 39, 3)
start_y = st.sidebar.slider("Start Y (Lander)", 0, 39, 3)
goal_x = st.sidebar.slider("Target X (Sample Site)", 0, 39, 35)
goal_y = st.sidebar.slider("Target Y (Sample Site)", 0, 39, 34)

# 1. Generate Realistic Lunar South Pole Terrain (40x40 grid, 1 unit = 10 meters)
np.random.seed(terrain_seed)
grid_size = 40
x = np.arange(grid_size)
y = np.arange(grid_size)
X, Y = np.meshgrid(x, y)

# Base gentle hills
Z = 1.5 * np.sin(X / 6.0) * np.cos(Y / 6.0) + np.random.normal(0, 0.15, (grid_size, grid_size))

# Add Lunar Craters (depressions with raised rims)
craters = [
    (15, 15, 6.0, 5.5),
    (25, 22, 7.0, 6.5),
    (12, 28, 5.0, 4.5),
    (28, 10, 5.5, 5.0),
    (20, 32, 4.5, 4.0)
]
for cx, cy, radius, depth in craters:
    dist = np.sqrt((X - cx)**2 + (Y - cy)**2)
    # Crater bowl
    Z -= depth * np.exp(-(dist**2) / (2 * (radius / 2.2)**2))
    # Raised crater rim
    Z += (depth * 0.25) * np.exp(-((dist - radius)**2) / (2 * (radius / 5.0)**2))

# 2. Calculate Slope (in Degrees) at every point
dy, dx = np.gradient(Z)
slope_deg = np.degrees(np.arctan(np.sqrt(dx**2 + dy**2)))

# 3. A* Pathfinding Algorithm (Avoids slopes > max_slope)
start = (start_y, start_x)
goal = (goal_y, goal_x)

open_set = []
heapq.heappush(open_set, (0, start))
came_from = {}
g_score = {start: 0}
directions = [(-1,0), (1,0), (0,-1), (0,1), (-1,-1), (-1,1), (1,-1), (1,1)]

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
            step_dist = 1.414 if (dr != 0 and dc != 0) else 1.0
            # Penalize steeper slopes so rover prefers flatter ground
            slope_penalty = (slope_deg[nr, nc] / max_slope) * 1.5
            tentative_g = g_score[current] + step_dist + slope_penalty

            if (nr, nc) not in g_score or tentative_g < g_score[(nr, nc)]:
                came_from[(nr, nc)] = current
                g_score[(nr, nc)] = tentative_g
                h = np.sqrt((nr - goal[0])**2 + (nc - goal[1])**2)
                heapq.heappush(open_set, (tentative_g + h, (nr, nc)))

# 4. Display Mission Telemetry Metrics
col1, col2, col3, col4 = st.columns(4)
if path:
    path_coords = np.array(path)
    path_slopes = [slope_deg[r, c] for r, c in path]
    total_dist_m = len(path) * 10
    max_path_slope = max(path_slopes)
    est_battery = round(total_dist_m * 0.08 + max_path_slope * 0.4, 1)

    col1.metric("Route Status", "✅ SAFE PATH FOUND")
    col2.metric("Total Distance", f"{total_dist_m} m")
    col3.metric("Max Slope on Route", f"{max_path_slope:.1f}°")
    col4.metric("Est. Battery Drain", f"{est_battery}%")
else:
    col1.metric("Route Status", "❌ NO SAFE PATH")
    col2.metric("Total Distance", "N/A")
    col3.metric("Max Slope Limit", f"{max_slope}°")
    col4.metric("Recommendation", "Increase Slope Limit")
    st.error("⚠️ Target unreachable! All routes exceed the rover's maximum safe slope limit. Try increasing the slope limit or changing coordinates.")

# 5. Interactive 3D Lunar Terrain + Route Plot
fig = go.Figure()

# Lunar Surface
fig.add_trace(go.Surface(
    z=Z, x=x, y=y,
    colorscale="Gray",
    showscale=False,
    opacity=0.95,
    name="Lunar Terrain"
))

# Plot Safe Route
if path:
    py = [p[0] for p in path]
    px = [p[1] for p in path]
    pz = [Z[p[0], p[1]] + 0.35 for p in path] # Slightly lifted so it's clearly visible

    fig.add_trace(go.Scatter3d(
        x=px, y=py, z=pz,
        mode="lines+markers",
        line=dict(color="#00FFCC", width=6),
        marker=dict(size=3, color="#00FFCC"),
        name="Safe Rover Path"
    ))

# Start & Target Markers
fig.add_trace(go.Scatter3d(
    x=[start_x], y=[start_y], z=[Z[start_y, start_x] + 0.6],
    mode="markers", marker=dict(size=8, color="lime"), name="Vikram Lander (Start)"
))
fig.add_trace(go.Scatter3d(
    x=[goal_x], y=[goal_y], z=[Z[goal_y, goal_x] + 0.6],
    mode="markers", marker=dict(size=8, color="red"), name="Target Site"
))

fig.update_layout(
    title="3D Lunar South Pole Elevation & Autonomous Route",
    scene=dict(
        xaxis_title="East-West (x10m)",
        yaxis_title="North-South (x10m)",
        zaxis_title="Elevation (m)",
        bgcolor="#0B0F19"
    ),
    margin=dict(l=0, r=0, b=0, t=40),
    height=600
)

st.plotly_chart(fig, use_container_width=True)