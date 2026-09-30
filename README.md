
# MARGDARSHAK

Smart Traffic & Route Guidance System with vehicle-aware routing, live traffic
simulation, and intelligent rerouting.

This repository contains two interfaces backed by the same routing prototype:

- A Flask web app with a browser UI and JSON optimization API.
- A Streamlit operations dashboard with maps, algorithm comparisons, and vehicle simulation.

## Features

- Weighted transportation graph with dynamic traffic scenarios
- QPSO-inspired route optimization
- Greedy baseline, GA, and ACO comparison
- Multi-objective scoring using travel time, distance, and congestion
- Route visualization with optional OSRM road geometry
- Accident simulation and route re-optimization
- Vehicle-specific road restrictions and rerouting

## Requirements

- Python 3.10 or newer
- Network access is optional. The Streamlit dashboard falls back to synthetic route geometry when OSRM is unavailable.

## Run locally

Create and activate a virtual environment, then install the dependencies:

```bash
python -m venv .venv
# macOS/Linux
source .venv/bin/activate
# Windows PowerShell
.\\.venv\\Scripts\\Activate.ps1
python -m pip install -r requirements.txt
```

### Full website (same app as Vercel)

```bash
python app.py
```

Open `http://localhost:5000`. The API endpoint is `POST /api/optimize`.
This is the same Flask website served at the Vercel deployment URL.

### Streamlit dashboard

Run this in a separate terminal:

```bash
python -m streamlit run streamlit_app.py
```

Open `http://localhost:8501`. The demo login is `admin` / `admin123`.

The **Vehicle Route Simulation** section supports 2-wheelers, 3-wheelers, and
heavy vehicles, with pause, resume, reset, incident, and vehicle-safe rerouting
controls.

## Test

Run the unit tests from the repository root:

```bash
python -m unittest -v
```

GitHub Actions runs this test suite for pushes and pull requests to `main`.

## Project layout

```text
app.py                   Flask app, routing algorithms, and API
routepulse_streamlit.py  Streamlit dashboard
vehicle_simulation.py    Vehicle constraints and route simulation helpers
test_vehicle_simulation.py
templates/index.html     Flask web interface
requirements.txt         Python dependencies
```

## Deploy

### Vercel

Vercel serves the Flask web app in `app.py` and uses the included `vercel.json`.
Connect this repository to Vercel, or deploy from the project root with the
Vercel CLI:

```bash
npx vercel
npx vercel --prod
```

The Vercel deployment provides the Flask web experience at `/` and the
optimization API at `/api/optimize`. Streamlit should be deployed separately
with Streamlit Community Cloud.

### Streamlit Community Cloud

For the dashboard and vehicle simulation, create a Streamlit Community Cloud
deployment using `routepulse_streamlit.py` as the main file. The repository's
`requirements.txt` contains the dashboard dependencies.

## Demo flow

1. Set 12–20 delivery locations and 3 vehicles.
2. Select "Rush Hour".
3. Click RUN QPSO.
4. Explain the graph, metrics, and convergence chart.
5. Click SIMULATE ACCIDENT.
6. Explain that a congested edge is injected and the optimizer recomputes the route.

## Notes

This is a hackathon prototype, not a production routing engine. The QPSO module is a discrete, quantum-inspired implementation designed for an interactive demo. For the final submission, benchmark it against OR-Tools and the supplied dataset and report actual experimental results.

## Next upgrades

- Integrate the official dataset.
- Add OR-Tools CVRP baseline.
- Add capacity/time-window constraints.
- Add multiple QPSO seeds and statistical benchmarking.
- Add real map data (OSM/OSRM).
- Add ML traffic prediction.
