import io
import math
import random
import time
from functools import lru_cache

import folium
import matplotlib.pyplot as plt
import pandas as pd
import requests
import streamlit as st
from folium.plugins import Fullscreen, MarkerCluster
from streamlit_folium import st_folium

from app import build_path_cache, expand_route, flatten_metrics, greedy_baseline, make_graph, qpso_route, route_metrics
from vehicle_simulation import (
    add_vehicle_alternate_roads,
    add_road_metadata,
    calculate_valid_route,
    connect_simulation_components,
    get_vehicle_constraints,
    route_metrics as simulation_route_metrics,
    simulate_vehicle_movement,
)

st.set_page_config(page_title="MARGDARSHAK", page_icon="🧭", layout="wide", initial_sidebar_state="expanded")
if not st.session_state.get("is_authenticated", False):
    st.markdown("""
    <style>
    [data-testid="stAppViewContainer"]{
        min-height:100vh;
        background:
            radial-gradient(ellipse at 18% 12%,rgba(34,111,179,.28),transparent 38%),
            radial-gradient(ellipse at 85% 90%,rgba(27,150,178,.16),transparent 36%),
            repeating-linear-gradient(0deg,transparent 0,transparent 47px,rgba(138,193,228,.035) 48px),
            repeating-linear-gradient(90deg,transparent 0,transparent 47px,rgba(138,193,228,.035) 48px),
            linear-gradient(135deg,#071321,#0b2035 55%,#081725);
    }
    [data-testid="stHeader"],[data-testid="stSidebar"],[data-testid="stFooter"]{display:none}
    .block-container{max-width:100%;min-height:100vh;padding:2rem 1rem;display:flex;flex-direction:column;justify-content:center}
    [data-testid="stVerticalBlockBorderWrapper"]>div{
        border:1px solid rgba(147,192,226,.24);
        border-radius:22px;
        background:rgba(11,28,46,.84);
        box-shadow:0 24px 80px rgba(0,0,0,.38);
        backdrop-filter:blur(16px);
    }
    .login-brand{text-align:center;color:#f4f8ff;font-size:2rem;font-weight:750;letter-spacing:-.04em}
    .login-subtitle{text-align:center;color:#adc1d4;font-size:.9rem;margin:.25rem 0 1.4rem}
    [data-testid="stAppViewContainer"] h2{color:#f4f8ff;text-align:center;margin:.5rem 0 1rem}
    [data-testid="stAppViewContainer"] label,[data-testid="stAppViewContainer"] p{color:#d3e1ee}
    [data-testid="stTextInput"] input{background:rgba(5,17,30,.72);border:1px solid #35516a;border-radius:10px;color:#f4f8ff}
    [data-testid="stTextInput"] input:focus{border-color:#43b9dc;box-shadow:0 0 0 1px #43b9dc}
    [data-testid="stFormSubmitButton"] button{
        width:100%;min-height:2.8rem;border:1px solid rgba(100,204,239,.35);border-radius:11px;
        background:linear-gradient(105deg,#2868cf,#159cb9);color:white;font-weight:700;
        transition:transform .16s ease,box-shadow .16s ease;
    }
    [data-testid="stFormSubmitButton"] button:hover{transform:translateY(-1px);box-shadow:0 8px 24px rgba(24,150,197,.28)}
    .login-demo{text-align:center;color:#9fb5c9;font-size:.82rem}
    @media(max-width:640px){.block-container{padding:1rem}.login-brand{font-size:1.7rem}}
    </style>
    """, unsafe_allow_html=True)

    _, login_column, _ = st.columns([1, 1.05, 1])
    with login_column:
        with st.container(border=True):
            st.markdown(
                '<div class="login-brand">🧭 MARGDARSHAK</div>'
                '<div class="login-subtitle">Smart Traffic &amp; Route Guidance System</div>',
                unsafe_allow_html=True,
            )
            st.subheader("Welcome Back")
            with st.form("margdarshak_login"):
                username = st.text_input("Username / Email", key="login_username")
                password = st.text_input("Password", type="password", key="login_password")
                submitted = st.form_submit_button("🔐 Login", width="stretch")
            st.markdown("---")
            st.markdown(
                '<div class="login-demo"><strong>Demo Login</strong><br>'
                "Username: admin &nbsp; · &nbsp; Password: admin123</div>",
                unsafe_allow_html=True,
            )
            if submitted:
                if username.strip() == "admin" and password == "admin123":
                    st.session_state.is_authenticated = True
                    st.rerun()
                st.error("❌ Invalid username or password")
    st.stop()

st.markdown("""
<style>
[data-testid="stAppViewContainer"]{background:#f4f8f8}[data-testid="stSidebar"]{background:#eef7f7}
.block-container{max-width:1500px;padding-top:1.3rem}.rp-kicker{color:#117f88;font-size:.72rem;font-weight:800;letter-spacing:.14em;text-transform:uppercase}
.rp-hero h1{color:#193642;font-size:2.15rem;margin:.25rem 0}[data-testid="stMetric"]{background:#fff;border:1px solid #d7e6e6;border-left:3px solid #16818a;border-radius:6px;padding:.8rem 1rem}
</style>
""", unsafe_allow_html=True)

CITY = {"name": "Bengaluru, Karnataka", "center": (12.9716, 77.5946)}
# Replace these sample GPS points with real depot/customer coordinates when available.
LOCATION_COORDINATES = {
    0:(12.9716,77.5946),1:(12.9752,77.6050),2:(12.9784,77.6408),3:(12.9352,77.6245),
    4:(12.9116,77.6389),5:(12.9166,77.6101),6:(12.9250,77.5838),7:(12.9537,77.5685),
    8:(13.0035,77.5700),9:(13.0285,77.5407),10:(12.9911,77.5547),11:(13.0358,77.5970),
    12:(12.9698,77.7500),13:(12.9591,77.6974),14:(12.9258,77.6760),15:(12.8452,77.6602),
    16:(12.9177,77.4830),17:(12.9719,77.5348),18:(12.9255,77.5648),19:(12.9063,77.5857),
    20:(12.9406,77.5681),21:(13.0329,77.5250),22:(12.9980,77.6190),23:(12.9870,77.6030),
    24:(12.9480,77.6100),25:(12.9620,77.5800),26:(12.9860,77.6300),
}
TRAFFIC = {1:("#16a34a","Low"),2:("#2563eb","Normal"),3:("#eab308","Medium"),4:("#f97316","Heavy"),5:("#dc2626","Very heavy")}
ROUTE_COLORS = ["#087f8c", "#7c3aed", "#c2410c", "#15803d", "#be185d", "#1d4ed8"]
RUPEES_PER_KM = 13
VEHICLE_PROFILES = {
    "Two-wheeler": {"capacity": 8, "speed_factor": 1.12},
    "Three-wheeler": {"capacity": 20, "speed_factor": 1.0},
    "Heavy truck": {"capacity": 50, "speed_factor": .78},
}


def name(node, stops):
    if node == 0: return "Depot"
    if node <= min(stops, 26): return f"Customer {chr(64 + node)}"
    return f"Road junction {node}"


def gps(node):
    if node in LOCATION_COORDINATES: return LOCATION_COORDINATES[node]
    rng = random.Random(7000 + node)
    return CITY["center"][0] + rng.uniform(-.045,.045), CITY["center"][1] + rng.uniform(-.05,.05)


def road_distance_km(start, end):
    earth_radius_km = 6371.0
    lat1, lon1 = map(math.radians, start)
    lat2, lon2 = map(math.radians, end)
    delta_lat, delta_lon = lat2 - lat1, lon2 - lon1
    haversine = math.sin(delta_lat / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin(delta_lon / 2) ** 2
    return 2 * earth_radius_km * math.asin(math.sqrt(haversine))


def level(congestion):
    return min(5, max(1, int(congestion * 5) + 1))


@lru_cache(maxsize=128)
def osrm_geometry(waypoints):
    if len(waypoints) < 2: return None
    coords = ";".join(f"{lon:.6f},{lat:.6f}" for lat,lon in waypoints)
    try:
        response = requests.get(f"https://router.project-osrm.org/route/v1/driving/{coords}", params={"overview":"simplified","geometries":"geojson","steps":"false"}, timeout=2)
        response.raise_for_status()
        routes = response.json().get("routes",[])
        points = routes[0]["geometry"]["coordinates"] if routes else []
        return tuple((lat,lon) for lon,lat in points) or None
    except (requests.RequestException, ValueError, KeyError, IndexError, TypeError):
        return None


def create_map(data, stops, capacity, use_osrm):
    nodes, edges, routes = data["nodes"], data["edges"], data["routes"]
    coords = {node["id"]:gps(node["id"]) for node in nodes}
    demand = {i:(i*3)%5+1 for i in range(1,min(stops,len(nodes)-1)+1)}
    assigned = {}
    for vehicle,route in enumerate(routes,1):
        for node in route:
            if node in demand: assigned.setdefault(node,vehicle)
    m = folium.Map(location=CITY["center"],zoom_start=12,tiles="OpenStreetMap",control_scale=True,prefer_canvas=True)
    m.fit_bounds(list(coords.values()),padding=(18,18)); Fullscreen(position="topright").add_to(m)
    traffic_layer=folium.FeatureGroup(name="Traffic roads",show=True)
    customer_layer=folium.FeatureGroup(name="Customer locations",show=True)
    route_layer=folium.FeatureGroup(name="Optimized vehicle routes",show=True)
    incident_layer=folium.FeatureGroup(name="Incidents / road closures",show=True)
    affected=data.get("affected")
    blocked=tuple(sorted((affected["a"],affected["b"]))) if affected and affected.get("closed") else None
    for edge in edges:
        if tuple(sorted((edge["a"],edge["b"])))==blocked: continue
        traffic_level=level(edge["congestion"])
        folium.PolyLine([coords[edge["a"]],coords[edge["b"]]],color=TRAFFIC[traffic_level][0],weight=4,opacity=.8,
          tooltip=f"{name(edge['a'],stops)} ↔ {name(edge['b'],stops)} · {TRAFFIC[traffic_level][1]} ({traffic_level}/5)").add_to(traffic_layer)
    traffic_layer.add_to(m)
    cluster=MarkerCluster(name="Customer cluster",control=False).add_to(customer_layer)
    for node,need in demand.items():
        nearby=[e["congestion"] for e in edges if node in (e["a"],e["b"])]
        if affected and node in (affected["a"],affected["b"]): nearby.append(affected.get("after_congestion",1))
        traffic_level=level(sum(nearby)/len(nearby)) if nearby else 1
        vehicle=assigned.get(node); assigned_text=f"Vehicle {vehicle}" if vehicle else "Unassigned"
        status=f"Planned · {assigned_text}" if vehicle else "Pending assignment"
        popup=f"<b>{name(node,stops)}</b><br>Demand: {need} parcels<br>Assigned vehicle: {assigned_text}<br>Traffic: {TRAFFIC[traffic_level][1]} ({traffic_level}/5)<br>Delivery status: {status}"
        folium.Marker(coords[node],tooltip=f"{name(node,stops)} · {need} parcels",popup=folium.Popup(popup,max_width=300),icon=folium.Icon(color="blue",icon="shopping-bag",prefix="glyphicon")).add_to(cluster)
    folium.Marker(coords[0],tooltip="Depot",popup=f"Depot · {CITY['name']} · Fleet start and return",icon=folium.Icon(color="darkgreen",icon="home",prefix="glyphicon")).add_to(customer_layer)
    customer_layer.add_to(m)
    osrm_used=False
    for vehicle,route in enumerate(routes,1):
        route_nodes=[node for node in route if node in coords]
        service=[]
        for node in route_nodes:
            if node==0 or node<=stops:
                if not service or service[-1]!=node: service.append(node)
        if len(service)<2: continue
        geometry=osrm_geometry(tuple(coords[node] for node in service)) if use_osrm else None
        points=list(geometry) if geometry else [coords[node] for node in route_nodes]
        osrm_used=osrm_used or bool(geometry)
        route_text=" → ".join(name(node,stops) for node in service)
        color=ROUTE_COLORS[(vehicle-1)%len(ROUTE_COLORS)]
        folium.PolyLine(points,color=color,weight=7,opacity=.92,tooltip=f"Vehicle {vehicle}: {route_text}",popup=folium.Popup(route_text,max_width=360)).add_to(route_layer)
        load=sum(demand[node] for node in set(service) if node in demand and assigned.get(node)==vehicle)
        vehicle_metrics=flatten_metrics([route],edges,nodes)
        trip_cost=vehicle_metrics["distance"]*RUPEES_PER_KM
        mid=points[len(points)//2]
        folium.Marker(mid,tooltip=f"Vehicle {vehicle}",popup=f"Vehicle {vehicle}<br>Route: {route_text}<br>Load: {load}/{capacity}<br>Utilization: {load/capacity*100 if capacity else 0:.0f}%<br>Distance: {vehicle_metrics['distance']:.2f} km<br>Estimated cost: ₹{trip_cost:.2f}",icon=folium.DivIcon(html='<div style="font-size:22px;text-shadow:0 1px 2px #fff">🚚</div>')).add_to(route_layer)
    route_layer.add_to(m)
    if affected:
        a,b=affected["a"],affected["b"]; old=level(affected.get("before_congestion",0)); new="Blocked" if affected.get("closed") else level(affected.get("after_congestion",1))
        road=f"{name(a,stops)} ↔ {name(b,stops)}"; popup=f"⚠️ Traffic incident<br>Road: {road}<br>Traffic: {old} → {new}<br>Rerouting triggered"
        folium.PolyLine([coords[a],coords[b]],color="#111827" if affected.get("closed") else "#ea580c",weight=9,dash_array="10, 8",tooltip=popup,popup=folium.Popup(popup,max_width=320)).add_to(incident_layer)
        mid=((coords[a][0]+coords[b][0])/2,(coords[a][1]+coords[b][1])/2)
        folium.Marker(mid,tooltip="Incident / closure",popup=popup,icon=folium.Icon(color="black" if affected.get("closed") else "red",icon="warning-sign",prefix="glyphicon")).add_to(incident_layer)
    incident_layer.add_to(m); folium.LayerControl(collapsed=False).add_to(m)
    legend="".join(f'<div><i style="display:inline-block;width:12px;height:8px;background:{color};margin-right:6px"></i>{text}</div>' for color,text in TRAFFIC.values())
    m.get_root().html.add_child(folium.Element(f'<div style="position:fixed;bottom:25px;left:15px;z-index:9999;background:white;padding:9px 12px;border:1px solid #ccd;border-radius:5px;font:12px Arial"><b>Traffic</b>{legend}</div>'))
    return m,osrm_used


def draw_simulation_map(data, progress):
    """Draw the constrained road network and the animated vehicle position."""
    nodes, roads, route = data["nodes"], data["roads"], data["route"]
    coordinates = {node["id"]: gps(node["id"]) for node in nodes}
    current_edge_index = min(int(progress), max(0, len(route) - 2))
    fraction = min(1.0, max(0.0, progress - current_edge_index))
    start_point = coordinates[route[current_edge_index]]
    end_point = coordinates[route[current_edge_index + 1]]
    vehicle_point = (
        start_point[0] + (end_point[0] - start_point[0]) * fraction,
        start_point[1] + (end_point[1] - start_point[1]) * fraction,
    )

    route_map = folium.Map(location=vehicle_point, zoom_start=12, tiles="OpenStreetMap", control_scale=True)
    for road in roads:
        start, end = coordinates[road["a"]], coordinates[road["b"]]
        if road.get("closed"):
            color, dash, status = "#111827", "8, 8", "Closed"
        else:
            congestion = road.get("congestion", 0)
            color = "#16a34a" if congestion < 0.25 else "#eab308" if congestion < 0.55 else "#dc2626"
            dash, status = None, f"Traffic {level(congestion)}/5"
        folium.PolyLine(
            [start, end],
            color=color,
            weight=5 if road.get("closed") else 3,
            dash_array=dash,
            opacity=0.9,
            tooltip=f"{name(road['a'], data['stops'])} ↔ {name(road['b'], data['stops'])} · "
            f"{road['road_class']} · {status}",
        ).add_to(route_map)

    previous_route = data.get("previous_route")
    if previous_route:
        folium.PolyLine(
            [coordinates[node] for node in previous_route],
            color="#f97316",
            weight=5,
            opacity=0.75,
            dash_array="8, 7",
            tooltip="Previous route",
        ).add_to(route_map)
    folium.PolyLine(
        [coordinates[node] for node in route],
        color="#2563eb",
        weight=7,
        opacity=0.95,
        tooltip="Selected vehicle route",
    ).add_to(route_map)

    vehicle_icons = {"2-Wheeler": "🛵", "3-Wheeler": "🛺", "Heavy Vehicle": "🚛"}
    folium.Marker(
        coordinates[route[0]],
        tooltip=f"Start · {name(route[0], data['stops'])}",
        icon=folium.Icon(color="green", icon="play", prefix="glyphicon"),
    ).add_to(route_map)
    folium.Marker(
        coordinates[route[-1]],
        tooltip=f"Destination · {name(route[-1], data['stops'])}",
        icon=folium.Icon(color="red", icon="flag", prefix="glyphicon"),
    ).add_to(route_map)
    folium.Marker(
        vehicle_point,
        tooltip=f"{data['vehicle_type']} · {name(route[current_edge_index], data['stops'])}",
        icon=folium.DivIcon(
            html=f'<div style="font-size:25px;text-shadow:0 1px 2px #fff">{vehicle_icons[data["vehicle_type"]]}</div>'
        ),
    ).add_to(route_map)
    route_map.fit_bounds([coordinates[node] for node in route], padding=(24, 24))
    return route_map, current_edge_index, fraction


def render_vehicle_simulation():
    """Advance the session-state simulation and render its live map/status."""
    state = st.session_state.vehicle_simulation
    if state is None:
        st.info("Choose a vehicle and locations, then run a simulation to see it move on the map.")
        return

    if state["running"] and not state["paused"]:
        state["progress"] = simulate_vehicle_movement(
            state["progress"], len(state["route"]) - 1, state["speed"]
        )
        if state["progress"] >= len(state["route"]) - 1:
            state["progress"] = float(len(state["route"]) - 1)
            state["running"] = False
            state["completed"] = True
            state["status"] = "Simulation Completed"

    route_map, edge_index, fraction = draw_simulation_map(state, state["progress"])
    edge = next(
        (
            road
            for road in state["roads"]
            if tuple(sorted((road["a"], road["b"])))
            == tuple(sorted((state["route"][edge_index], state["route"][edge_index + 1])))
        ),
        None,
    )
    current_location = (
        name(state["route"][edge_index], state["stops"])
        if fraction < 0.5
        else name(state["route"][edge_index + 1], state["stops"])
    )
    remaining = simulation_route_metrics(
        state["route"][edge_index + 1 :], state["roads"], state["vehicle_type"]
    )
    if edge and not edge.get("closed"):
        remaining["distance"] += edge.get("distance", 0) * (1 - fraction)
        remaining["time"] += (
            edge.get("distance", 0)
            / max(1.0, edge.get("speed", 1))
            * 60
            * (1 + 2 * edge.get("congestion", 0))
            * (1 - fraction)
        )
    current_speed = edge.get("speed", 0) if edge else 0
    traffic_label = "Closed" if edge and edge.get("closed") else TRAFFIC[level(edge["congestion"])][1] if edge else "Low"
    route_text = " → ".join(name(node, state["stops"]) for node in state["route"])
    map_col, info_col = st.columns([1.7, 1], gap="large")
    with map_col:
        st_folium(
            route_map,
            width=None,
            height=520,
            key=f"vehicle-simulation-map-{int(state['progress'] * 100)}-{state['reroutes']}",
            returned_objects=[],
        )
        st.caption("Green: low traffic · Yellow: medium · Red: heavy · Black dashed: closed · Blue: selected route")
    with info_col:
        st.subheader("Live simulation")
        st.metric("Vehicle", state["vehicle_type"])
        st.metric("Current location", current_location)
        st.metric("Destination", name(state["destination"], state["stops"]))
        st.metric("Traffic level", traffic_label)
        st.metric("Current speed", f"{current_speed:.0f} km/h")
        st.metric("Distance remaining", f"{remaining['distance']:.2f} km")
        st.metric("Estimated time remaining", f"{remaining['time']:.1f} min")
        st.metric("Route status", state["status"])
        st.caption(f"Current route: {route_text}")
        st.caption(f"Reroutes: {state['reroutes']} · Progress: {state['progress']:.2f} / {len(state['route']) - 1} road segments")
        if state.get("notice"):
            st.info(state["notice"])
        if state["completed"]:
            summary = simulation_route_metrics(state["route"], state["roads"], state["vehicle_type"])
            st.success("✅ Simulation Completed")
            st.dataframe(
                pd.DataFrame(
                    [
                        {"Metric": "Vehicle Type", "Result": state["vehicle_type"]},
                        {"Metric": "Start", "Result": name(state["start"], state["stops"])},
                        {"Metric": "Destination", "Result": name(state["destination"], state["stops"])},
                        {"Metric": "Final Route", "Result": route_text},
                        {"Metric": "Total Distance", "Result": f"{summary['distance']:.2f} km"},
                        {"Metric": "Total Travel Time", "Result": f"{summary['time']:.1f} min"},
                        {"Metric": "Traffic Cost", "Result": f"{summary['traffic_cost']:.2f}"},
                        {"Metric": "Estimated Travel Cost", "Result": f"₹{summary['travel_cost']:.2f}"},
                        {"Metric": "Number of Reroutes", "Result": state["reroutes"]},
                        {"Metric": "Final Traffic Condition", "Result": traffic_label},
                    ]
                ),
                hide_index=True,
                width="stretch",
            )


def route_table(routes, capacity, stops, edges, nodes):
    rows=[]
    for vehicle,route in enumerate(routes,1):
        customers={node for node in route if 1<=node<=stops}; load=sum((node*3)%5+1 for node in customers)
        metrics=flatten_metrics([route],edges,nodes)
        rows.append({"Vehicle":vehicle,"Route":" → ".join(name(node,stops) for node in route),"Load":load,"Capacity":capacity,"Utilization %":round(load/capacity*100,1) if capacity else 0,"Distance (km)":metrics["distance"],"Trip cost (₹)":round(metrics["distance"]*RUPEES_PER_KM,2)})
    return pd.DataFrame(rows)


@st.cache_data(show_spinner=False, max_entries=48)
def compare_algorithms(nodes,edges,qpso_routes,qpso_runtime,stops,vehicles,iterations,seed):
    edge_map={tuple(sorted((e["a"],e["b"]))):e for e in edges}; cache=build_path_cache(nodes,edges)
    def fitness(order):
        d,t,c=route_metrics([0]+order+[0],edge_map,cache); return t+.18*d+18*c
    candidates=list(range(1,min(len(nodes),stops+1)))
    rng=random.Random(seed+17); population=[]
    for _ in range(18):
        order=candidates[:];rng.shuffle(order);population.append(order)
    start=time.perf_counter()
    for _ in range(iterations):
        population.sort(key=fitness); children=population[:4]
        while len(children)<len(population):
            a,b=rng.sample(population[:9],2); cut=rng.randrange(1,len(candidates)); child=a[:cut]+[x for x in b if x not in a[:cut]]
            if rng.random()<.2:
                i,j=rng.sample(range(len(child)),2);child[i],child[j]=child[j],child[i]
            children.append(child)
        population=children
    ga_order=min(population,key=fitness); ga_ms=(time.perf_counter()-start)*1000
    rng=random.Random(seed+31); pheromone={(a,b):1.0 for a in [0]+candidates for b in candidates if a!=b}; best=candidates[:];start=time.perf_counter()
    for _ in range(iterations):
        ants=[]
        for _ in range(12):
            order=[];current=0;remaining=candidates[:]
            while remaining:
                weights=[]
                for node in remaining:
                    d,t,c=route_metrics([current,node],edge_map,cache);weights.append(pheromone.get((current,node),1)**1.2*(1/max(.01,t+.18*d+18*c))**2)
                choice=rng.choices(remaining,weights=weights,k=1)[0];order.append(choice);remaining.remove(choice);current=choice
            ants.append(order)
        ants.sort(key=fitness)
        if fitness(ants[0])<fitness(best):best=ants[0]
        pheromone={key:value*.88 for key,value in pheromone.items()}
        for order in ants[:3]:
            for a,b in zip([0]+order,order+[0]):pheromone[(a,b)]=pheromone.get((a,b),1)+100/max(.01,fitness(order))
    aco_ms=(time.perf_counter()-start)*1000
    def split(order):
        chunk=math.ceil(len(order)/vehicles);return [expand_route([0]+order[i:i+chunk]+[0],cache) for i in range(0,len(order),chunk)]
    outputs={"QPSO":(qpso_routes,qpso_runtime),"GA":(split(ga_order),ga_ms),"ACO":(split(best),aco_ms)};rows=[]
    for algorithm,(routes,runtime) in outputs.items():
        m=flatten_metrics(routes,edges,nodes);rows.append({"Algorithm":algorithm,"Fitness":round(m["time"]+.18*m["distance"]+18*m["congestion"],2),"Distance (km)":m["distance"],"Traffic cost":m["congestion"],"Trip cost (₹)":round(m["distance"]*RUPEES_PER_KM,2),"Runtime (ms)":round(runtime,2)})
    return outputs,pd.DataFrame(rows)


@st.cache_data(show_spinner=False,max_entries=48)
def simulate(stops,vehicles,capacity,vehicle_type,traffic,iterations,seed,incident=None,increase=0,closure=False):
    nodes,edges=make_graph(max(25,stops+5),seed=seed,traffic=traffic);affected=None
    vehicle_profile=VEHICLE_PROFILES[vehicle_type]
    for edge in edges:
        edge["distance"]=round(road_distance_km(gps(edge["a"]),gps(edge["b"])),3)
        edge["speed"]=round(edge["speed"]*vehicle_profile["speed_factor"],1)
    if incident is not None:
        target=next((e for e in edges if tuple(sorted((e["a"],e["b"])))==tuple(sorted(incident))),None)
        if target:
            before=target["congestion"]
            if closure:
                edges.remove(target);affected={**target,"before_congestion":before,"after_congestion":1.0,"closed":True}
            else:
                target["congestion"]=min(1.0,before+.07*increase);affected={**target,"before_congestion":before,"after_congestion":target["congestion"],"closed":False}
    start=time.perf_counter();routes,convergence=qpso_route(nodes,edges,stops,vehicles,iterations,seed+(1 if incident else 0));runtime=(time.perf_counter()-start)*1000
    return {"nodes":nodes,"edges":edges,"routes":routes,"convergence":convergence,"runtime_ms":runtime,"metrics":flatten_metrics(routes,edges,nodes),"baseline_routes":greedy_baseline(nodes,edges,stops,vehicles),"affected":affected}


with st.sidebar:
    st.title("🧭 MARGDARSHAK");st.caption("Smart Traffic & Route Guidance System")
    vehicles=st.slider("Number of vehicles",1,6,3)
    vehicle_type=st.selectbox("Vehicle type (applies to fleet)",list(VEHICLE_PROFILES))
    vehicle_profile=VEHICLE_PROFILES[vehicle_type]
    if st.session_state.get("capacity_vehicle_type") != vehicle_type:
        st.session_state.capacity_vehicle_type=vehicle_type
        st.session_state.vehicle_capacity=vehicle_profile["capacity"]
    capacity=st.slider("Capacity per vehicle (parcels)",1,vehicle_profile["capacity"],key="vehicle_capacity")
    st.caption(f"{vehicle_type}: up to {vehicle_profile['capacity']} parcels · speed factor {vehicle_profile['speed_factor']:.2f}×")
    stops=st.slider("Delivery locations",8,22,12)
    traffic=st.selectbox("Traffic profile",["Low","Normal","Rush Hour","Extreme"],index=2);seed=st.number_input("Random seed",1,9999,42);iterations=st.selectbox("QPSO iterations",[30,60,100],index=1)
    use_osrm=st.checkbox("Use OSRM road geometry",value=True,help="Falls back to sample routes if public OSRM is unavailable.")
    run_qpso=st.button("Run QPSO Route Optimization",type="primary",width="stretch")
if run_qpso or "scenario" not in st.session_state:
    with st.spinner("Simulating traffic and optimizing routes..."):
        st.session_state.scenario=simulate(stops,vehicles,capacity,vehicle_type,traffic,iterations,int(seed));st.session_state.pop("after",None);st.session_state.map_rev=st.session_state.get("map_rev",0)+1
scenario=st.session_state.scenario;active=st.session_state.get("after",scenario);metric=active["metrics"]
st.session_state.setdefault("vehicle_simulation", None)

st.markdown('<div class="rp-kicker">Operations control center</div><div class="rp-hero"><h1>🧭 MARGDARSHAK</h1><p>Smart Traffic &amp; Route Guidance System</p></div>',unsafe_allow_html=True)
with st.container(horizontal=True):
    st.metric("Delivery demand",f"{stops} locations",border=True);st.metric("Fleet capacity",f"{vehicles*capacity} parcels",border=True);st.metric("Optimized distance",f"{metric['distance']:.2f} km",border=True);st.metric("Estimated trip cost",f"₹{metric['distance']*RUPEES_PER_KM:.2f}",f"₹{RUPEES_PER_KM}/km",border=True)

st.header("🚗 Vehicle Route Simulation")
simulation_type = st.selectbox(
    "Vehicle Type",
    ["2-Wheeler", "3-Wheeler", "Heavy Vehicle"],
    key="simulation_vehicle_type",
)
location_options = list(range(min(stops, len(scenario["nodes"]) - 1) + 1))
location_labels = {node: name(node, stops) for node in location_options}
if st.session_state.get("simulation_start") not in location_options:
    st.session_state["simulation_start"] = location_options[0]
start_col, destination_col = st.columns(2)
with start_col:
    simulation_start = st.selectbox(
        "Start",
        location_options,
        format_func=lambda node: location_labels[node],
        key="simulation_start",
    )
destination_options = [node for node in location_options if node != simulation_start]
if st.session_state.get("simulation_destination") not in destination_options:
    st.session_state["simulation_destination"] = destination_options[0]
with destination_col:
    simulation_destination = st.selectbox(
        "Destination",
        destination_options,
        format_func=lambda node: location_labels[node],
        key="simulation_destination",
    )
control_col, speed_col = st.columns([2, 1])
with control_col:
    run_vehicle_simulation = st.button("▶ Run Simulation", type="primary", key="run_vehicle_simulation")
with speed_col:
    simulation_speed = st.selectbox("Simulation Speed", [0.5, 1, 2, 5], index=1, format_func=lambda speed: f"{speed}x", key="vehicle_simulation_speed")

if run_vehicle_simulation:
    st.session_state.vehicle_simulation = None
    simulation_profile = get_vehicle_constraints(simulation_type)
    roads = add_road_metadata(active["edges"])
    present_edges = {tuple(sorted((road["a"], road["b"]))) for road in roads}
    for base_road in scenario["edges"]:
        key = tuple(sorted((base_road["a"], base_road["b"])))
        if key not in present_edges:
            roads.extend(add_road_metadata([base_road]))
            present_edges.add(key)
    source_speed_factor = VEHICLE_PROFILES[vehicle_type]["speed_factor"]
    for road in roads:
        road["speed"] = max(
            1.0,
            road["speed"] / source_speed_factor * simulation_profile["speed_factor"],
        )
    initial_closed = set()
    affected = active.get("affected")
    if affected and affected.get("closed"):
        initial_closed.add(tuple(sorted((affected["a"], affected["b"]))))
        for road in roads:
            if tuple(sorted((road["a"], road["b"]))) in initial_closed:
                road["closed"] = True
    roads = connect_simulation_components(
        roads,
        [node["id"] for node in scenario["nodes"]],
        {node["id"]: gps(node["id"]) for node in scenario["nodes"]},
        simulation_profile["speed_factor"],
    )
    valid_route = calculate_valid_route(
        simulation_start,
        simulation_destination,
        simulation_type,
        roads,
        initial_closed,
    )
    if valid_route is None:
        st.error(
            "No valid route exists for this vehicle under the current road restrictions and closures. "
            "Try another destination or clear the closure."
        )
    else:
        st.session_state.vehicle_simulation = {
            "nodes": scenario["nodes"],
            "roads": roads,
            "closed_edges": initial_closed,
            "route": valid_route,
            "previous_route": None,
            "start": simulation_start,
            "destination": simulation_destination,
            "stops": stops,
            "vehicle_type": simulation_type,
            "progress": 0.0,
            "speed": simulation_speed,
            "running": True,
            "paused": False,
            "completed": False,
            "reroutes": 0,
            "status": "Normal",
            "notice": "",
        }

state = st.session_state.vehicle_simulation
if state:
    state["speed"] = simulation_speed
    pause_col, resume_col, reset_col = st.columns(3)
    with pause_col:
        if st.button("⏸ Pause", key="pause_vehicle_simulation", disabled=not state["running"]):
            state["paused"] = True
            state["status"] = "Paused"
    with resume_col:
        if st.button("▶ Resume", key="resume_vehicle_simulation", disabled=not state["paused"]):
            state["paused"] = False
            state["status"] = "Normal"
    with reset_col:
        if st.button("🔄 Reset Simulation", key="reset_vehicle_simulation"):
            st.session_state.vehicle_simulation = None
            state = None

if state:
    incident_controls = st.columns([2, 1, 1])
    incident_labels = {
        f"{name(road['a'], state['stops'])} ↔ {name(road['b'], state['stops'])} "
        f"({road['road_class']})": tuple(sorted((road["a"], road["b"])))
        for road in state["roads"]
    }
    with incident_controls[0]:
        selected_incident = st.selectbox(
            "Inject incident on road",
            list(incident_labels),
            key="vehicle_simulation_incident_road",
        )
    with incident_controls[1]:
        incident_kind = st.selectbox(
            "Incident type",
            ["Traffic increase", "Road closure"],
            key="vehicle_simulation_incident_kind",
        )
    with incident_controls[2]:
        inject_incident = st.button(
            "⚠️ Apply & reroute",
            key="apply_vehicle_simulation_incident",
            disabled=not (state["running"] or state["paused"]),
        )
    if inject_incident:
        affected_edge = incident_labels[selected_incident]
        st.info("⚠️ Traffic detected on current route. 🔄 Calculating alternate route...")
        current_index = min(
            int(state["progress"] + 0.5),
            len(state["route"]) - 1,
        )
        current_node = state["route"][current_index]
        for road in state["roads"]:
            if tuple(sorted((road["a"], road["b"]))) == affected_edge:
                if incident_kind == "Road closure":
                    road["closed"] = True
                    state["closed_edges"].add(affected_edge)
                else:
                    road["congestion"] = min(1.0, road.get("congestion", 0.0) + 0.35)
        alternate = calculate_valid_route(
            current_node,
            state["destination"],
            state["vehicle_type"],
            state["roads"],
            state["closed_edges"],
        )
        if alternate is None:
            alternate_roads = add_vehicle_alternate_roads(
                state["roads"],
                [node["id"] for node in state["nodes"]],
                {node["id"]: gps(node["id"]) for node in state["nodes"]},
                state["vehicle_type"],
            )
            state["roads"].extend(alternate_roads)
            alternate = calculate_valid_route(
                current_node,
                state["destination"],
                state["vehicle_type"],
                state["roads"],
                state["closed_edges"],
            )
        state["reroutes"] += 1
        if alternate is None:
            state["running"] = False
            state["paused"] = False
            state["status"] = "No valid route"
            state["notice"] = "No permitted alternate route is available from the current location."
        else:
            state["previous_route"] = state["route"]
            state["route"] = state["route"][: current_index + 1] + alternate[1:]
            state["progress"] = float(current_index)
            state["status"] = "Re-routed"
            old_text = " → ".join(name(node, state["stops"]) for node in state["previous_route"])
            new_text = " → ".join(name(node, state["stops"]) for node in state["route"])
            state["notice"] = f"✅ New route calculated. Old route: {old_text}. New route: {new_text}."

@st.fragment(run_every="1s", key="vehicle-simulation-live")
def vehicle_simulation_live():
    render_vehicle_simulation()

vehicle_simulation_live()

st.subheader(":material/map: Live Traffic & Route Map")
route_map,osrm_used=create_map(active,stops,capacity,use_osrm);st_folium(route_map,width=1200,height=620,key=f"route-map-{st.session_state.get('map_rev',0)}",returned_objects=[])
st.caption(f"OpenStreetMap · {CITY['name']} sample GPS · {'OSRM road geometry' if osrm_used else 'sample graph fallback'} · simulated traffic")

map_tab,qpso_tab,compare_tab,benchmark_tab,reroute_tab,fleet_tab,export_tab=st.tabs(["Network & traffic","QPSO Route Optimization","QPSO vs GA vs ACO","Statistical benchmark","Dynamic rerouting","Fleet analysis","Export"])
with map_tab:
    st.subheader("Traffic road conditions")
    st.dataframe(pd.DataFrame([{"Road":f"{name(e['a'],stops)} ↔ {name(e['b'],stops)}","Traffic":f"{level(e['congestion'])}/5 {TRAFFIC[level(e['congestion'])][1]}","Speed":e["speed"]} for e in active["edges"]]),hide_index=True,width="stretch",height=300)
    st.caption("Replace LOCATION_COORDINATES with customer GPS coordinates to map a real service area.")
with qpso_tab:
    st.caption("QPSO uses the existing route optimizer from app.py.")
    a,b=st.columns([1,1.5])
    with a:
        st.metric("Fitness",f"{metric['time']+.18*metric['distance']+18*metric['congestion']:.2f}");st.metric("Distance",f"{metric['distance']:.2f} km");st.metric("Congestion index",f"{metric['congestion']:.2f}");st.metric("Estimated trip cost",f"₹{metric['distance']*RUPEES_PER_KM:.2f}",f"₹{RUPEES_PER_KM}/km");st.caption(f"Runtime: {active['runtime_ms']/1000:.3f}s · Vehicle: {vehicle_type}")
        for vehicle,route in enumerate(active["routes"],1):st.info(f"Vehicle {vehicle}: "+" → ".join(name(node,stops) for node in route))
    with b:st.line_chart(pd.DataFrame({"Best fitness":active["convergence"]}),height=300)
with compare_tab:
    with st.spinner("Evaluating QPSO, GA, and ACO..."):outputs,comparison=compare_algorithms(scenario["nodes"],scenario["edges"],scenario["routes"],scenario["runtime_ms"],stops,vehicles,iterations,int(seed))
    st.dataframe(comparison,hide_index=True,width="stretch");c1,c2=st.columns(2)
    with c1:st.bar_chart(comparison.set_index("Algorithm")["Fitness"],height=260)
    with c2:st.bar_chart(comparison.set_index("Algorithm")["Distance (km)"],height=260)
    st.caption("Fitness combines travel time, distance, and traffic; results are measured rather than assumed.")
with benchmark_tab:
    runs=st.number_input("Benchmark runs",2,10,3)
    if st.button("Run QPSO / GA / ACO benchmark",key="benchmark_run"):
        observations={key:[] for key in ["QPSO","GA","ACO"]}
        with st.spinner("Running repeated seeds..."):
            for offset in range(int(runs)):
                sample=simulate(stops,vehicles,capacity,vehicle_type,traffic,min(iterations,60),int(seed)+offset)
                _,table=compare_algorithms(sample["nodes"],sample["edges"],sample["routes"],sample["runtime_ms"],stops,vehicles,min(iterations,60),int(seed)+offset)
                for _,row in table.iterrows():observations[row["Algorithm"]].append(float(row["Fitness"]))
        st.session_state.benchmark_table=pd.DataFrame([{"Algorithm":k,"Mean fitness":round(sum(v)/len(v),2),"Best":round(min(v),2),"Worst":round(max(v),2),"Std. dev.":round(pd.Series(v).std(),2)} for k,v in observations.items()])
    if "benchmark_table" in st.session_state:
        st.dataframe(st.session_state.benchmark_table,hide_index=True,width="stretch")
        st.bar_chart(st.session_state.benchmark_table.set_index("Algorithm")["Mean fitness"])
    else:st.info("Run repeated seeds to compare QPSO, GA, and ACO.")
with reroute_tab:
    choices={"Auto-select highest-impact road":None}
    for e in scenario["edges"]:choices[f"{name(e['a'],stops)} ↔ {name(e['b'],stops)}"]=(e["a"],e["b"])
    selected=st.selectbox("Incident road",list(choices));increase=st.slider("Traffic increase",1,5,3);left,right=st.columns(2)
    with left:incident=st.button("Simulate traffic incident",key="incident")
    with right:closure=st.button("Simulate road closure",key="closure")
    if incident or closure:
        edge=choices[selected]
        if edge is None:
            e=max(scenario["edges"],key=lambda item:item["congestion"]*item["distance"]);edge=(e["a"],e["b"])
        st.session_state.after=simulate(stops,vehicles,capacity,vehicle_type,traffic,iterations,int(seed),edge,increase,closure);st.session_state.map_rev=st.session_state.get("map_rev",0)+1;st.rerun()
    if "after" in st.session_state:
        after=st.session_state.after;impact=after["affected"];old=level(impact["before_congestion"]);new="Blocked" if impact["closed"] else level(impact["after_congestion"])
        st.warning(f"Affected road: {name(impact['a'],stops)} ↔ {name(impact['b'],stops)} · traffic {old} → {new}; rerouting triggered.")
        before,after_metric=scenario["metrics"],after["metrics"]
        st.dataframe(pd.DataFrame([{"Metric":"Fitness","Before":round(before["time"]+.18*before["distance"]+18*before["congestion"],2),"After":round(after_metric["time"]+.18*after_metric["distance"]+18*after_metric["congestion"],2)},{"Metric":"Distance","Before":before["distance"],"After":after_metric["distance"]},{"Metric":"Traffic cost","Before":before["congestion"],"After":after_metric["congestion"]}]),hide_index=True,width="stretch")
        st.success("Route automatically updated because traffic conditions changed.")
with fleet_tab:
    fleet=route_table(active["routes"],capacity,stops,active["edges"],active["nodes"]);st.dataframe(fleet,hide_index=True,width="stretch")
    if not fleet.empty:
        st.bar_chart(fleet.set_index("Vehicle")["Utilization %"],height=260)
    served={node for route in active["routes"] for node in route if 1<=node<=stops}
    st.subheader("Constraint validation")
    st.dataframe(pd.DataFrame([{"Constraint":"Depot start / return","Status":"PASS" if all(r[0]==0 and r[-1]==0 for r in active["routes"]) else "CHECK"},{"Constraint":"Delivery coverage","Status":"PASS" if len(served)==stops else "CHECK"},{"Constraint":"Vehicle limit","Status":"PASS" if len(active["routes"])<=vehicles else "CHECK"},{"Constraint":"Estimated capacity","Status":"PASS" if fleet.empty or (fleet["Load"]<=fleet["Capacity"]).all() else "CHECK"}]),hide_index=True,width="stretch")
with export_tab:
    _,comparison=compare_algorithms(scenario["nodes"],scenario["edges"],scenario["routes"],scenario["runtime_ms"],stops,vehicles,iterations,int(seed));st.dataframe(comparison,hide_index=True,width="stretch")
    data=io.StringIO();comparison.to_csv(data,index=False);st.download_button("Download QPSO / GA / ACO results",data.getvalue(),"algorithm_results.csv","text/csv")
    routes=io.StringIO();route_table(scenario["routes"],capacity,stops,scenario["edges"],scenario["nodes"]).to_csv(routes,index=False);st.download_button("Download QPSO vehicle routes",routes.getvalue(),"vehicle_routes.csv","text/csv")
