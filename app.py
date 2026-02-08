import json
import math
import heapq
import os
import re
import requests
from collections import defaultdict
from flask import Flask, render_template, request, jsonify

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
SARVAM_API_KEY = "sk_k8qo9hrs_EtCk4gzEpIHSPrjNxklTkPis"

# ================= LOAD DATABASE =================
with open(os.path.join(BASE_DIR, "map_data.json"), "r") as f:
    db = json.load(f)

buildings = db["buildings"]

# ================= SARVAM STT =================
def sarvam_stt(audio_bytes):
    url = "https://api.sarvam.ai/speech-to-text"
    headers = {"Authorization": f"Bearer {SARVAM_API_KEY}"}
    files = {"file": ("audio.webm", audio_bytes)}
    data = {"language": "en-IN"}

    r = requests.post(url, headers=headers, files=files, data=data)
    r.raise_for_status()
    return r.json()["text"]

def extract_room(text):
    text = text.lower()

    # direct digits
    m = re.search(r"\b\d{3,4}\b", text)
    if m:
        return m.group()

    words = {
        "zero":"0","one":"1","two":"2","three":"3","four":"4",
        "five":"5","six":"6","seven":"7","eight":"8","nine":"9"
    }

    digits = [words[w] for w in text.split() if w in words]
    return "".join(digits) if len(digits) >= 3 else None

# ================= GRAPH =================
def build_graph(building):
    B = buildings[building]
    nodes, node_floor, edges = {}, {}, []

    def add_node(nid, pos, floor):
        nodes[nid] = tuple(pos)
        node_floor[nid] = floor

    def dist(a, b):
        return math.hypot(nodes[a][0]-nodes[b][0], nodes[a][1]-nodes[b][1])

    cid = 0
    for c in B["corridors"]:
        prev = None
        for p in c["points"]:
            nid = f"C{cid}"
            add_node(nid, p, c["floor"])
            if prev:
                edges.append((prev, nid))
            prev = nid
            cid += 1

    corridors = [n for n in nodes if n.startswith("C")]

    for i in range(len(corridors)):
        for j in range(i+1, len(corridors)):
            a, b = corridors[i], corridors[j]
            if node_floor[a] == node_floor[b] and dist(a,b) <= 18:
                edges.append((a,b))

    for r in B["rooms"]:
        add_node(r["id"], r["pos"], r["floor"])
        snap = f"{r['id']}_SNAP"
        add_node(snap, r["snap"], r["floor"])
        edges.append((r["id"], snap))

        nearest = min(
            [c for c in corridors if node_floor[c]==r["floor"]],
            key=lambda c: math.hypot(nodes[c][0]-r["snap"][0], nodes[c][1]-r["snap"][1])
        )
        edges.append((snap, nearest))

    stairs = defaultdict(list)
    for s in B["stairs"]:
        sid = f"{s['id']}_{s['floor']}"
        add_node(sid, s["pos"], s["floor"])
        stairs[s["id"]].append(sid)

        nearest = min(
            [c for c in corridors if node_floor[c]==s["floor"]],
            key=lambda c: math.hypot(nodes[c][0]-s["pos"][0], nodes[c][1]-s["pos"][1])
        )
        edges.append((sid, nearest))

    for g in stairs.values():
        for a,b in zip(sorted(g), sorted(g)[1:]):
            edges.append((a,b))

    graph = {n: [] for n in nodes}
    for a,b in edges:
        w = 1 if node_floor[a] != node_floor[b] else dist(a,b)
        graph[a].append((b,w))
        graph[b].append((a,w))

    return nodes, node_floor, graph, B

def shortest_path(graph, start, end):
    pq, prev, cost = [(0,start)], {}, {start:0}

    while pq:
        c,u = heapq.heappop(pq)
        if u == end:
            break
        for v,w in graph[u]:
            nc = c+w
            if v not in cost or nc < cost[v]:
                cost[v] = nc
                prev[v] = u
                heapq.heappush(pq,(nc,v))

    if start != end and end not in prev:
        return []

    path = [end]
    while path[-1] != start:
        path.append(prev[path[-1]])
    return path[::-1]

def navigate(building, start, end):
    nodes, node_floor, graph, B = build_graph(building)
    path = shortest_path(graph, start, end)

    if not path:
        return {}, [], {}, None

    floor_points, floor_order = defaultdict(list), []
    for n in path:
        f = node_floor[n]
        if f not in floor_order:
            floor_order.append(f)
        floor_points[f].extend(nodes[n])

    floor_images = {f: B["floors"][f]["image"] for f in floor_points}
    return floor_points, floor_order, floor_images, node_floor[path[0]]

# ================= FLASK =================
app = Flask(__name__, static_url_path="", static_folder=".")

@app.route("/")
def home():
    return render_template("index.html", buildings=buildings.keys())

@app.route("/navigate", methods=["POST"])
def nav_api():
    d = request.json
    fp, fo, fi, sf = navigate(d["building"], d["start"], d["end"])
    return jsonify({
        "floor_points": fp,
        "floor_order": fo,
        "floor_images": fi,
        "start_floor": sf
    })

# 🎤 VOICE ROOM ENDPOINT
@app.route("/voice-room", methods=["POST"])
def voice_room():
    audio = request.files["audio"].read()
    text = sarvam_stt(audio)
    room = extract_room(text)
    return jsonify({"heard": text, "room": room})

if __name__ == "__main__":
    app.run(debug=True)
