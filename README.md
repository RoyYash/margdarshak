
# 🧭 MARGDARSHAK

**Smart Traffic & Route Guidance System**

A smart traffic-management prototype with vehicle-aware routes, live traffic simulation, and intelligent rerouting.

The routing dashboard retains its QPSO-inspired optimization algorithm, alongside the GA and ACO comparison.

## What it demonstrates

- Weighted transportation graph
- Dynamic traffic scenarios
- Practical discrete QPSO-inspired search
- Multi-objective fitness: travel time + distance + congestion
- Route visualization
- Classical greedy baseline
- Convergence chart
- "Simulate Accident" -> re-optimization
- Benchmark dashboard
- Vehicle-specific route simulation with road restrictions, animated map movement, and incident rerouting

## Run locally

Python 3.10+ recommended.

```bash
pip install -r requirements.txt
python app.py
```

Open:
http://127.0.0.1:5000

Run the Streamlit traffic-management dashboard in a separate terminal:

```bash
python -m streamlit run routepulse_streamlit.py
```

The dashboard's **Vehicle Route Simulation** section supports 2-wheelers,
3-wheelers, and heavy vehicles; use its pause/resume/reset and incident controls
to demonstrate live movement and vehicle-safe rerouting.

## Deploy

### Vercel

Vercel serves the Flask web app in `app.py` and uses the included `vercel.json`.
Connect this repository to Vercel, or deploy from the project root with the
Vercel CLI:

```bash
npx vercel
npx vercel --prod
```

The Vercel deployment provides the interactive web experience at `/` and the
optimization API at `/api/optimize`.

### Streamlit Community Cloud

For the dashboard and vehicle simulation, create a Streamlit Community Cloud
deployment using `routepulse_streamlit.py` as the main file. The repository's
`requirements.txt` contains the dashboard dependencies.

### GitHub

```bash
git add .
git commit -m "Prepare deployment"
git branch -M main
git push -u origin main
```

## Demo flow

1. Set 12–20 delivery locations and 3 vehicles.
2. Select "Rush Hour".
3. Click RUN QPSO.
4. Explain the graph, metrics, and convergence chart.
5. Click SIMULATE ACCIDENT.
6. Explain that a congested edge is injected and the optimizer recomputes the route.

## Important

This is a hackathon prototype, not a production routing engine. The QPSO module is a discrete, quantum-inspired implementation designed for an interactive demo. For the final submission, benchmark it against OR-Tools and the supplied dataset and report actual experimental results.

## Next upgrades

- Integrate the official dataset.
- Add OR-Tools CVRP baseline.
- Add capacity/time-window constraints.
- Add multiple QPSO seeds and statistical benchmarking.
- Add real map data (OSM/OSRM).
- Add ML traffic prediction.
