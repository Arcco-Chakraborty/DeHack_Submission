import json
import math
import heapq
import matplotlib.pyplot as plt
import matplotlib.image as mpimg

# ================= LOAD DATABASE =================
with open("map_data.json", "r") as f:
    db = json.load(f)

buildings = db["buildings"]

# ================= SELECT BUILDING =================
print("Available buildings:", list(buildings.keys()))
building = input("Select building: ").strip()

if building not in buildings:
    print("❌ Invalid building")
    exit()

B = buildings[building]

# ================= GRAPH STORAGE =================
nodes = {}
node_floor = {}
edges = []

def add_node(nid, pos, floor):
    nodes[nid] = pos
    node_floor[nid] = floor

def dist(a, b):
    return math.hypot(
        nodes[a][0] - nodes[b][0],
        nodes[a][1] - nodes[b][1]
    )

# ================= BUILD CORRIDOR NETWORK =================
cid_counter = 0
for c in B["corridors"]:
    prev = None
    for p in c["points"]:
        cid = f"C{cid_counter}"
        add_node(cid, tuple(p), c["floor"])
        if prev:
            edges.append((prev, cid))
        prev = cid
        cid_counter += 1

# auto-connect corridor intersections
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
    add_node(rid, tuple(r["pos"]), r["floor"])

    snap_id = f"{rid}_SNAP"
    add_node(snap_id, tuple(r["snap"]), r["floor"])
    edges.append((rid, snap_id))

    nearest = min(
        [c for c in corridors if node_floor[c] == r["floor"]],
        key=lambda c: math.hypot(
            nodes[c][0] - r["snap"][0],
            nodes[c][1] - r["snap"][1]
        )
    )
    edges.append((snap_id, nearest))

# ================= EXITS (SAME AS ROOMS) =================
for e in B.get("exits", []):
    eid = e["id"]
    add_node(eid, tuple(e["pos"]), e["floor"])

    snap_id = f"{eid}_SNAP"
    add_node(snap_id, tuple(e["snap"]), e["floor"])
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
    add_node(sid, tuple(s["pos"]), s["floor"])
    stairs_by_id.setdefault(s["id"], []).append(sid)

    nearest = min(
        [c for c in corridors if node_floor[c] == s["floor"]],
        key=lambda c: math.hypot(
            nodes[c][0] - s["pos"][0],
            nodes[c][1] - s["pos"][1]
        )
    )
    edges.append((sid, nearest))

# connect stairs vertically
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

# ================= DIJKSTRA =================
def shortest_path(start, end):
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
        print("❌ No path found")
        return []

    path = [end]
    while path[-1] != start:
        path.append(prev[path[-1]])
    return path[::-1]

# ================= USER INPUT =================
rooms = [r["id"] for r in B["rooms"]]
exits = [e["id"] for e in B.get("exits", [])]

print("Rooms:", rooms)
print("Exits:", exits)

start = input("Start (room/exit): ").strip()
end = input("Destination (room/exit): ").strip()

if start not in nodes or end not in nodes:
    print("❌ Invalid start or destination")
    exit()

path = shortest_path(start, end)
if not path:
    exit()

# ================= FLOOR VIEW =================
floors = sorted(B["floors"].keys())
current_floor = floors.index(node_floor[start])

fig, ax = plt.subplots(figsize=(10, 8))

def draw_floor():
    ax.clear()
    floor = floors[current_floor]
    img = mpimg.imread(B["floors"][floor]["image"])
    ax.imshow(img)
    ax.axis("off")
    ax.set_title(f"{building} | Floor {floor} (↑ ↓ to switch)")

    floor_path = [n for n in path if node_floor[n] == floor]
    for i in range(len(floor_path) - 1):
        a, b = floor_path[i], floor_path[i + 1]
        x1, y1 = nodes[a]
        x2, y2 = nodes[b]
        ax.arrow(
            x1, y1,
            x2 - x1,
            y2 - y1,
            color="red",
            linewidth=2,
            head_width=10,
            length_includes_head=True
        )
    plt.draw()

def on_key(event):
    global current_floor
    if event.key == "up":
        current_floor = min(current_floor + 1, len(floors) - 1)
    elif event.key == "down":
        current_floor = max(current_floor - 1, 0)
    elif event.key == "q":
        plt.close()
    draw_floor()

fig.canvas.mpl_connect("key_press_event", on_key)
draw_floor()
plt.show()
