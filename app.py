
from flask import Flask, render_template, jsonify, request
import random, math, time

app = Flask(__name__)

# ----------------------------
# Synthetic transportation graph
# ----------------------------
def make_graph(n=35, seed=42, traffic="Rush Hour"):
    rng = random.Random(seed)
    nodes = [{"id": i, "x": rng.uniform(5, 95), "y": rng.uniform(8, 92)} for i in range(n)]
    edges = []
    # connect each node to its nearest 3 nodes
    for i in range(n):
        dists = []
        for j in range(n):
            if i == j: continue
            dx = nodes[i]["x"] - nodes[j]["x"]
            dy = nodes[i]["y"] - nodes[j]["y"]
            dists.append((dx*dx + dy*dy, j))
        for _, j in sorted(dists)[:3]:
            if i < j and not any(e["a"] == j and e["b"] == i for e in edges):
                dist = math.sqrt((nodes[i]["x"]-nodes[j]["x"])**2 + (nodes[i]["y"]-nodes[j]["y"])**2)
                base_speed = rng.uniform(30, 55)
                congestion = {"Low": rng.uniform(.05,.25),
                              "Normal": rng.uniform(.20,.45),
                              "Rush Hour": rng.uniform(.45,.85),
                              "Extreme": rng.uniform(.70,1.0)}[traffic]
                edges.append({
                    "a": i, "b": j, "distance": round(dist, 2),
                    "congestion": round(congestion, 3),
                    "speed": round(base_speed, 1)
                })
    return nodes, edges

def adjacency(edges):
    adj = {}
    for e in edges:
        adj.setdefault(e["a"], []).append(e)
        adj.setdefault(e["b"], []).append(e)
    return adj

def shortest_path(nodes, edges, start, goal, weight="time"):
    # Dijkstra
    adj = adjacency(edges)
    import heapq
    pq = [(0, start, [start])]
    seen = {}
    while pq:
        cost, u, path = heapq.heappop(pq)
        if u in seen and seen[u] <= cost:
            continue
        seen[u] = cost
        if u == goal:
            return path
        for e in adj.get(u, []):
            v = e["b"] if e["a"] == u else e["a"]
            congestion = e["congestion"]
            # traffic increases travel time nonlinearly
            travel_time = e["distance"] / e["speed"] * 60 * (1 + 2.0 * congestion)
            w = travel_time if weight == "time" else e["distance"]
            heapq.heappush(pq, (cost+w, v, path+[v]))
    return [start, goal]

def build_path_cache(nodes, edges):
    import heapq

    adj = adjacency(edges)
    paths = {}
    for node in nodes:
        start = node["id"]
        costs = {start: 0}
        previous = {}
        queue = [(0, start)]
        while queue:
            cost, current = heapq.heappop(queue)
            if cost > costs[current]:
                continue
            for edge in adj.get(current, []):
                neighbor = edge["b"] if edge["a"] == current else edge["a"]
                travel_time = edge["distance"] / edge["speed"] * 60 * (1 + 2.0 * edge["congestion"])
                edge_cost = travel_time + 0.18 * edge["distance"] + 18 * edge["congestion"]
                next_cost = cost + edge_cost
                if next_cost < costs.get(neighbor, float("inf")):
                    costs[neighbor] = next_cost
                    previous[neighbor] = current
                    heapq.heappush(queue, (next_cost, neighbor))
        for goal in costs:
            path = [goal]
            while path[-1] != start:
                path.append(previous[path[-1]])
            paths[(start, goal)] = list(reversed(path))
    return paths

def expand_route(route, path_cache):
    if not route:
        return []
    expanded = [route[0]]
    for start, goal in zip(route, route[1:]):
        path = path_cache.get((start, goal), [start, goal])
        expanded.extend(path[1:])
    return expanded

def route_metrics(route, edge_map, path_cache):
    distance = time_min = congestion = 0
    for start, goal in zip(route, route[1:]):
        metric_key = ("metrics", start, goal)
        if metric_key not in path_cache:
            expanded = expand_route([start, goal], path_cache)
            leg_distance = leg_time = leg_congestion = 0
            for a, b in zip(expanded, expanded[1:]):
                edge = edge_map.get(tuple(sorted((a, b))))
                if edge:
                    leg_distance += edge["distance"]
                    leg_congestion += edge["congestion"]
                    leg_time += edge["distance"] / edge["speed"] * 60 * (1 + 2.0 * edge["congestion"])
            path_cache[metric_key] = (leg_distance, leg_time, leg_congestion)
        leg_distance, leg_time, leg_congestion = path_cache[metric_key]
        distance += leg_distance
        time_min += leg_time
        congestion += leg_congestion
    return distance, time_min, congestion

def two_opt(route, edge_map, path_cache):
    if len(route) < 5:
        return route
    best = route[:]
    best_cost = sum(route_metrics(best, edge_map, path_cache)[:2])
    improved = True
    while improved:
        improved = False
        for i in range(1, len(best)-2):
            for j in range(i+1, len(best)-1):
                cand = best[:i] + best[i:j+1][::-1] + best[j+1:]
                cost = sum(route_metrics(cand, edge_map, path_cache)[:2])
                if cost < best_cost:
                    best, best_cost = cand, cost
                    improved = True
                    break
            if improved: break
    return best

# ----------------------------
# Quantum-inspired prototype
# ----------------------------
def qpso_route(nodes, edges, stops=12, vehicles=3, iterations=60, seed=7):
    rng = random.Random(seed)
    n = len(nodes)
    edge_map = {tuple(sorted((e["a"], e["b"]))): e for e in edges}
    path_cache = build_path_cache(nodes, edges)
    depot = 0
    candidate_stops = list(range(1, min(n, stops+1)))

    # A practical discrete QPSO-inspired search:
    # particles are permutations; mbest/global-best guide random
    # attraction and mutation. This is intended as a hackathon prototype.
    swarm = []
    pbest = []
    pfit = []
    for _ in range(14):
        p = candidate_stops[:]
        rng.shuffle(p)
        p = [depot] + p + [depot]
        swarm.append(p)
        pbest.append(p[:])
        pfit.append(float("inf"))

    gbest = None
    gfit = float("inf")
    convergence = []

    def fitness(route):
        d,t,c = route_metrics(route, edge_map, path_cache)
        # normalized-ish multiobjective score
        return t + 0.18*d + 18*c

    for it in range(iterations):
        for k, particle in enumerate(swarm):
            repaired = two_opt(particle, edge_map, path_cache)
            f = fitness(repaired)
            if f < pfit[k]:
                pbest[k], pfit[k] = repaired[:], f
            if f < gfit:
                gbest, gfit = repaired[:], f

        convergence.append(round(gfit, 2))
        mbest = [pbest[rng.randrange(len(pbest))][i] for i in range(len(gbest))]

        new_swarm = []
        for particle in swarm:
            candidate = particle[:]
            # quantum-inspired probability of moving toward gbest / mbest
            beta = 0.9 - 0.55*(it/max(1, iterations-1))
            for _ in range(max(1, int(beta*3))):
                if rng.random() < 0.65:
                    i,j = rng.sample(range(1, len(candidate)-1), 2)
                    # use gbest information
                    if rng.random() < 0.7 and gbest:
                        target = gbest[i]
                        if target in candidate[1:-1]:
                            pos = candidate.index(target)
                            candidate[i], candidate[pos] = candidate[pos], candidate[i]
                    else:
                        candidate[i], candidate[j] = candidate[j], candidate[i]
            new_swarm.append(candidate)
        swarm = new_swarm

    # Split one optimized sequence across vehicles
    inner = gbest[1:-1]
    routes = []
    chunk = math.ceil(len(inner)/vehicles)
    for v in range(vehicles):
        part = inner[v*chunk:(v+1)*chunk]
        if part:
            routes.append(expand_route([depot] + part + [depot], path_cache))
    return routes, convergence

def greedy_baseline(nodes, edges, stops=12, vehicles=3):
    edge_map = {tuple(sorted((e["a"], e["b"]))): e for e in edges}
    path_cache = build_path_cache(nodes, edges)
    remaining = list(range(1, min(len(nodes), stops+1)))
    routes=[]
    for _ in range(vehicles):
        if not remaining: break
        r=[0]
        assigned = 0
        stop_limit = math.ceil(stops/vehicles)
        while remaining and assigned < stop_limit:
            last=r[-1]
            nxt=min(remaining, key=lambda x: route_metrics([last,x], edge_map, path_cache)[0])
            r.extend(path_cache.get((last,nxt), [last,nxt])[1:])
            remaining.remove(nxt)
            assigned += 1
        if len(r) > 1:
            r.extend(path_cache.get((r[-1],0), [r[-1],0])[1:])
            routes.append(r)
    return routes

def flatten_metrics(routes, edges, nodes):
    edge_map = {tuple(sorted((e["a"], e["b"]))): e for e in edges}
    path_cache = build_path_cache(nodes, edges)
    vals=[route_metrics(r,edge_map,path_cache) for r in routes]
    return {
        "distance": round(sum(v[0] for v in vals),2),
        "time": round(sum(v[1] for v in vals),2),
        "congestion": round(sum(v[2] for v in vals),2),
    }

@app.get("/")
def home():
    return render_template("index.html")

@app.post("/api/optimize")
def optimize():
    body=request.get_json(silent=True) or {}
    stops=int(body.get("stops",12))
    vehicles=int(body.get("vehicles",3))
    traffic=body.get("traffic","Rush Hour")
    iterations=int(body.get("iterations",60))
    seed=int(body.get("seed",7))

    nodes, edges = make_graph(max(25, stops+5), seed=seed, traffic=traffic)
    start=time.time()
    qroutes, convergence=qpso_route(nodes, edges, stops, vehicles, iterations, seed)
    qtime=(time.time()-start)*1000
    groot=greedy_baseline(nodes, edges, stops, vehicles)
    qm=flatten_metrics(qroutes,edges,nodes)
    gm=flatten_metrics(groot,edges,nodes)

    # A demo accident: increase congestion on a selected high-impact edge
    accident = body.get("accident", False)
    if accident and edges:
        target=max(edges, key=lambda e:e["congestion"]*e["distance"])
        target["congestion"]=min(1.0,target["congestion"]+0.35)
        qroutes2, conv2=qpso_route(nodes, edges, stops, vehicles, iterations, seed+99)
        qm2=flatten_metrics(qroutes2,edges,nodes)
        return jsonify({
            "nodes":nodes,"edges":edges,"routes":qroutes2,"baseline_routes":groot,
            "metrics":qm2,"baseline_metrics":gm,"convergence":conv2,
            "runtime_ms":round(qtime,2),"accident_edge":[target["a"],target["b"]],
            "message":"Traffic incident detected — route re-optimized."
        })

    return jsonify({
        "nodes":nodes,"edges":edges,"routes":qroutes,"baseline_routes":groot,
        "metrics":qm,"baseline_metrics":gm,"convergence":convergence,
        "runtime_ms":round(qtime,2),
        "message":"QPSO-inspired route optimized successfully."
    })

if __name__=="__main__":
    app.run(host="0.0.0.0", port=5000, debug=True, use_reloader=False)
