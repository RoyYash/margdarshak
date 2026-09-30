"""Vehicle-specific routing helpers for the Streamlit route simulator."""

from __future__ import annotations

import heapq


VEHICLE_CONSTRAINTS = {
    "2-Wheeler": {
        "speed_factor": 1.12,
        "cost_per_km": 5.0,
        "allowed_classes": {"narrow", "medium", "arterial"},
    },
    "3-Wheeler": {
        "speed_factor": 1.0,
        "cost_per_km": 9.0,
        "allowed_classes": {"medium", "arterial"},
    },
    "Heavy Vehicle": {
        "speed_factor": 0.78,
        "cost_per_km": 20.0,
        "allowed_classes": {"arterial"},
    },
}


def get_vehicle_constraints(vehicle_type: str) -> dict:
    """Return the allowed road classes and operating profile for a vehicle."""
    try:
        return VEHICLE_CONSTRAINTS[vehicle_type]
    except KeyError as exc:
        raise ValueError(f"Unsupported vehicle type: {vehicle_type}") from exc


def add_road_metadata(edges: list[dict]) -> list[dict]:
    """Attach stable demo road classes and restrictions to synthetic graph edges."""
    roads = []
    for source in edges:
        road = dict(source)
        a, b = sorted((road["a"], road["b"]))
        class_bucket = (a * 31 + b * 17) % 100
        if class_bucket < 13:
            road_class, width = "narrow", 3.0
        elif class_bucket < 36:
            road_class, width = "medium", 5.5
        else:
            road_class, width = "arterial", 8.0
        restriction_bucket = (a * 11 + b * 29) % 41
        road["road_class"] = road_class
        road["width_m"] = width
        road["restricted"] = restriction_bucket == 0
        road["residential"] = road_class != "arterial" and restriction_bucket in (1, 2)
        road["heavy_allowed"] = (
            road_class == "arterial"
            and not road["restricted"]
            and not road["residential"]
        )
        road["closed"] = False
        roads.append(road)

    adjacency: dict[int, list[tuple[int, tuple[int, int]]]] = {}
    for road in roads:
        key = tuple(sorted((road["a"], road["b"])))
        adjacency.setdefault(road["a"], []).append((road["b"], key))
        adjacency.setdefault(road["b"], []).append((road["a"], key))
    backbone = set()
    visited = set()
    if adjacency:
        pending = [min(adjacency)]
        visited.add(pending[0])
        while pending:
            node = pending.pop()
            for neighbor, edge_key in adjacency.get(node, []):
                if neighbor not in visited:
                    visited.add(neighbor)
                    pending.append(neighbor)
                    backbone.add(edge_key)
    for road in roads:
        if tuple(sorted((road["a"], road["b"]))) in backbone:
            road.update(
                road_class="arterial",
                width_m=8.0,
                restricted=False,
                residential=False,
                heavy_allowed=True,
            )
    return roads


def connect_simulation_components(
    roads: list[dict],
    node_ids: list[int],
    coordinates: dict[int, tuple[float, float]],
    speed_factor: float,
) -> list[dict]:
    """Join disconnected demo-network components with explicitly marked arterial links."""
    result = [dict(road) for road in roads]
    while True:
        adjacency = {node: set() for node in node_ids}
        existing_pairs = {
            tuple(sorted((road["a"], road["b"]))) for road in result
        }
        for road in result:
            if not road.get("closed"):
                adjacency.setdefault(road["a"], set()).add(road["b"])
                adjacency.setdefault(road["b"], set()).add(road["a"])
        components = []
        unseen = set(adjacency)
        while unseen:
            root = unseen.pop()
            component = {root}
            pending = [root]
            while pending:
                current = pending.pop()
                for neighbor in adjacency.get(current, set()) & unseen:
                    unseen.remove(neighbor)
                    component.add(neighbor)
                    pending.append(neighbor)
            components.append(component)
        if len(components) <= 1:
            return result

        closest_pair = None
        closest_distance = float("inf")
        for index, first in enumerate(components):
            for second in components[index + 1 :]:
                for start in first:
                    for end in second:
                        if tuple(sorted((start, end))) in existing_pairs:
                            continue
                        a, b = coordinates[start], coordinates[end]
                        distance = (a[0] - b[0]) ** 2 + (a[1] - b[1]) ** 2
                        if distance < closest_distance:
                            closest_distance = distance
                            closest_pair = (start, end)
        if closest_pair is None:
            raise ValueError("Unable to connect the simulated road network.")
        start, end = closest_pair
        lat1, lon1 = coordinates[start]
        lat2, lon2 = coordinates[end]
        from math import asin, cos, radians, sin, sqrt

        delta_lat, delta_lon = radians(lat2 - lat1), radians(lon2 - lon1)
        haversine = sin(delta_lat / 2) ** 2 + cos(radians(lat1)) * cos(radians(lat2)) * sin(delta_lon / 2) ** 2
        distance_km = 2 * 6371.0 * asin(sqrt(haversine)) * 1.25
        result.append(
            {
                "a": start,
                "b": end,
                "distance": distance_km,
                "speed": 35 * speed_factor,
                "congestion": 0.25,
                "road_class": "arterial",
                "width_m": 8.0,
                "restricted": False,
                "residential": False,
                "heavy_allowed": True,
                "closed": False,
                "simulated_connector": True,
            }
        )


def add_vehicle_alternate_roads(
    roads: list[dict],
    node_ids: list[int],
    coordinates: dict[int, tuple[float, float]],
    vehicle_type: str,
) -> list[dict]:
    """Add marked arterial demo links only when restrictions leave no connected route."""
    allowed_roads = [
        road for road in roads if is_road_allowed(road, vehicle_type)
    ]
    connected = connect_simulation_components(
        allowed_roads,
        node_ids,
        coordinates,
        get_vehicle_constraints(vehicle_type)["speed_factor"],
    )
    existing_pairs = {
        tuple(sorted((road["a"], road["b"]))) for road in roads
    }
    return [
        road
        for road in connected
        if road.get("simulated_connector")
        and tuple(sorted((road["a"], road["b"]))) not in existing_pairs
    ]


def is_road_allowed(
    road: dict, vehicle_type: str, closed_edges: set[tuple[int, int]] | None = None
) -> bool:
    """Check vehicle class, restrictions, and closure state before routing."""
    constraints = get_vehicle_constraints(vehicle_type)
    edge_key = tuple(sorted((road["a"], road["b"])))
    if road.get("closed") or edge_key in (closed_edges or set()) or road.get("restricted"):
        return False
    if road.get("road_class") not in constraints["allowed_classes"]:
        return False
    return vehicle_type != "Heavy Vehicle" or road.get("heavy_allowed", False)


def calculate_valid_route(
    start: int,
    destination: int,
    vehicle_type: str,
    edges: list[dict],
    closed_edges: set[tuple[int, int]] | None = None,
) -> list[int] | None:
    """Find a least-cost route using only roads permitted for this vehicle."""
    get_vehicle_constraints(vehicle_type)
    if start == destination:
        return [start]

    adjacency: dict[int, list[tuple[int, dict]]] = {}
    for road in edges:
        if not is_road_allowed(road, vehicle_type, closed_edges):
            continue
        adjacency.setdefault(road["a"], []).append((road["b"], road))
        adjacency.setdefault(road["b"], []).append((road["a"], road))

    queue = [(0.0, start)]
    best = {start: 0.0}
    previous: dict[int, int] = {}
    while queue:
        cost, node = heapq.heappop(queue)
        if cost > best[node]:
            continue
        if node == destination:
            path = [destination]
            while path[-1] != start:
                path.append(previous[path[-1]])
            return list(reversed(path))
        for neighbor, road in adjacency.get(node, []):
            distance = max(0.0, road.get("distance", 0.0))
            speed = max(1.0, road.get("speed", 1.0))
            congestion = min(1.0, max(0.0, road.get("congestion", 0.0)))
            travel_time = distance / speed * 60 * (1 + 2 * congestion)
            travel_cost = distance * get_vehicle_constraints(vehicle_type)["cost_per_km"]
            next_cost = cost + travel_time + 0.18 * distance + 18 * congestion + 0.02 * travel_cost
            if next_cost < best.get(neighbor, float("inf")):
                best[neighbor] = next_cost
                previous[neighbor] = node
                heapq.heappush(queue, (next_cost, neighbor))
    return None


def route_metrics(route: list[int], edges: list[dict], vehicle_type: str) -> dict:
    """Summarize distance, traffic-adjusted time, and travel cost for a route."""
    edge_map = {tuple(sorted((edge["a"], edge["b"]))): edge for edge in edges}
    distance = travel_time = traffic_cost = 0.0
    for start, end in zip(route, route[1:]):
        edge = edge_map.get(tuple(sorted((start, end))))
        if edge is None:
            continue
        leg_distance = max(0.0, edge.get("distance", 0.0))
        congestion = min(1.0, max(0.0, edge.get("congestion", 0.0)))
        distance += leg_distance
        travel_time += leg_distance / max(1.0, edge.get("speed", 1.0)) * 60 * (1 + 2 * congestion)
        traffic_cost += congestion
    return {
        "distance": distance,
        "time": travel_time,
        "traffic_cost": traffic_cost,
        "travel_cost": distance * get_vehicle_constraints(vehicle_type)["cost_per_km"],
    }


def simulate_vehicle_movement(progress: float, edge_count: int, speed: float) -> float:
    """Advance route progress by one timed animation step."""
    return min(float(edge_count), progress + 0.12 * speed)
