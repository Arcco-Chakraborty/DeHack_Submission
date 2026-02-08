import json
import math
import heapq
import os
from collections import defaultdict
from flask import Flask, render_template, request, jsonify

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# ================= LOAD DATABASE =================
with open(os.path.join(BASE_DIR, "map_data.json"), "r") as f:
    db = json.load(f)

buildings = db["buildings"]

# ================= GRAPH BUILD =================
def build_graph(building):
    B = buildings[building]

    nodes = {}
    node_floor = {}
    edges = []

    def add_node(nid, pos, floor):
        nodes[nid] = tuple(pos)
        node_floor[nid] = floor

    def dist(a, b):
        return math.hypot(
            nodes[a][0] - nodes[b][0],
            nodes[a][1] - nodes[b][1]
        )

    # ================= BUILD CORRIDORS =================
    cid_counter = 0
    for c in B["corridors"]:
        prev = None
        for p in c["points"]:
            cid = f"C{cid_counter}"
            add_node(cid, p, c["floor"])
            if prev:
                edges.append((prev, cid))
            prev = cid
            cid_counter += 1

    CORRIDOR_SNAP_DIST = 18
    corridors = [n for n in nodes if n.startswith("C")]

    for i in range(len(corridors)):
        for j in range(i + 1, len(corridors)):
            a, b = corridors[i], corridors[j]
            if node_floor[a] == node_floor[b] and dist(a, b) <= CORRIDOR_SNAP_DIST:
                edges.append((a, b))

    # ================= ROOMS =================
    for r in B["rooms"]:
        rid = r["id"]
        add_node(rid, r["pos"], r["floor"])

        snap_id = f"{rid}_SNAP"
        add_node(snap_id, r["snap"], r["floor"])
        edges.append((rid, snap_id))

        nearest = min(
            [c for c in corridors if node_floor[c] == r["floor"]],
            key=lambda c: math.hypot(
                nodes[c][0] - r["snap"][0],
                nodes[c][1] - r["snap"][1]
            )
        )
        edges.append((snap_id, nearest))

    # ================= EXITS =================
    for e in B.get("exits", []):
        eid = e["id"]
        add_node(eid, e["pos"], e["floor"])

        snap_id = f"{eid}_SNAP"
        add_node(snap_id, e["snap"], e["floor"])
        edges.append((eid, snap_id))

        nearest = min(
            [c for c in corridors if node_floor[c] == e["floor"]],
            key=lambda c: math.hypot(
                nodes[c][0] - e["snap"][0],
                nodes[c][1] - e["snap"][1]
            )
        )
        edges.append((snap_id, nearest))

    # ================= STAIRS =================
    stairs_by_id = {}

    for s in B["stairs"]:
        sid = f"{s['id']}_{s['floor']}"
        add_node(sid, s["pos"], s["floor"])
        stairs_by_id.setdefault(s["id"], []).append(sid)

        nearest = min(
            [c for c in corridors if node_floor[c] == s["floor"]],
            key=lambda c: math.hypot(
                nodes[c][0] - s["pos"][0],
                nodes[c][1] - s["pos"][1]
            )
        )
        edges.append((sid, nearest))

    for stair_nodes in stairs_by_id.values():
        stair_nodes.sort()
        for a, b in zip(stair_nodes, stair_nodes[1:]):
            edges.append((a, b))

    # ================= BUILD GRAPH =================
    graph = {n: [] for n in nodes}

    for a, b in edges:
        w = 1 if node_floor[a] != node_floor[b] else dist(a, b)
        graph[a].append((b, w))
        graph[b].append((a, w))

    return nodes, node_floor, graph, B

# ================= DIJKSTRA =================
def shortest_path(graph, start, end):
    pq = [(0, start)]
    prev = {}
    cost = {start: 0}

    while pq:
        c, u = heapq.heappop(pq)
        if u == end:
            break
        for v, w in graph[u]:
            nc = c + w
            if v not in cost or nc < cost[v]:
                cost[v] = nc
                prev[v] = u
                heapq.heappush(pq, (nc, v))

    if start != end and end not in prev:
        return []

    path = [end]
    while path[-1] != start:
        path.append(prev[path[-1]])
    return path[::-1]

# ================= PUBLIC API =================
BUILDINGS = {
    b: {
        "rooms": [r["id"] for r in buildings[b]["rooms"]] +
                 [e["id"] for e in buildings[b].get("exits", [])],
        "floors": sorted(buildings[b]["floors"].keys())
    }
    for b in buildings
}

def navigate(building, start, end):
    nodes, node_floor, graph, B = build_graph(building)
    path = shortest_path(graph, start, end)

    if not path:
        return {}, [], {}, None

    start_floor = node_floor[path[0]]
    floor_points = defaultdict(list)
    floor_order = []

    for n in path:
        f = node_floor[n]
        if f not in floor_order:
            floor_order.append(f)
        x, y = nodes[n]
        floor_points[f].extend([x, y])

    floor_images = {
        f: B["floors"][f]["image"]
        for f in floor_points
    }

    return floor_points, floor_order, floor_images, start_floor

# ================= FLASK =================
app = Flask(__name__, static_url_path="", static_folder=".")

@app.route("/")
def home():
    return render_template("index.html", buildings=BUILDINGS)

@app.route("/navigate", methods=["POST"])
def nav_api():
    data = request.json
    return jsonify(dict(zip(
        ["floor_points", "floor_order", "floor_images", "start_floor"],
        navigate(data["building"], data["start"], data["end"])
    )))

if __name__ == "__main__":
    app.run(debug=True)
