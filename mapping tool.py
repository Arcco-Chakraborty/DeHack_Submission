import matplotlib.pyplot as plt
import matplotlib.image as mpimg
import json
import math
import copy
import os
from tkinter import Tk, simpledialog

# ================== TK ==================
root = Tk()
root.withdraw()

# ================== FILE ==================
FILE = "map_data.json"
MAP_DIR = "maps"

# ================== LOAD DB ==================
try:
    with open(FILE, "r") as f:
        db = json.load(f)
except:
    db = {}

if "buildings" not in db:
    db = {"buildings": {}}

# ================== SELECT BUILDING ==================
building = input("Enter building name: ").strip()
building_path = os.path.join(MAP_DIR, building)

if not os.path.isdir(building_path):
    print(f"❌ Folder {building_path} does not exist")
    print("Create it and add F0.jpeg, F1.jpeg, ...")
    exit()

# ================== AUTO DETECT FLOORS ==================
floors = {}
for file in os.listdir(building_path):
    if file.startswith("F") and file.lower().endswith(".jpeg"):
        floor = file.split(".")[0]
        floors[floor] = {"image": os.path.join(building_path, file)}

if not floors:
    print("❌ No floor images found (F0.jpeg, F1.jpeg, ...)")
    exit()

# ================== INIT BUILDING ==================
if building not in db["buildings"]:
    db["buildings"][building] = {
        "floors": floors,
        "rooms": [],
        "exits": [],
        "corridors": [],
        "stairs": []
    }

data = db["buildings"][building]
data["floors"] = floors

# ================== STATE ==================
undo_stack = []
current_floor = sorted(floors.keys())[0]
mode = "room"
corridor_start = None
selected = None

room_count = 1
exit_count = 1
stair_count = 1

# ================== HELPERS ==================
def save_undo():
    undo_stack.append(copy.deepcopy(data))

def dist(a, b):
    return math.hypot(a[0] - b[0], a[1] - b[1])

def interpolate(a, b, spacing=40):
    L = dist(a, b)
    n = max(2, int(L // spacing))
    return [
        (
            int(a[0] + (b[0] - a[0]) * i / n),
            int(a[1] + (b[1] - a[1]) * i / n)
        )
        for i in range(n + 1)
    ]

def nearest_corridor(pos):
    best, best_d = None, float("inf")
    for c in data["corridors"]:
        if c["floor"] != current_floor:
            continue
        for p in c["points"]:
            d = dist(pos, p)
            if d < best_d:
                best, best_d = p, d
    return best

def clear_current_floor():
    save_undo()
    data["rooms"] = [r for r in data["rooms"] if r["floor"] != current_floor]
    data["exits"] = [e for e in data["exits"] if e["floor"] != current_floor]
    data["corridors"] = [c for c in data["corridors"] if c["floor"] != current_floor]
    data["stairs"] = [s for s in data["stairs"] if s["floor"] != current_floor]

# ================== DRAW ==================
def redraw():
    ax.clear()
    img = mpimg.imread(data["floors"][current_floor]["image"])
    ax.imshow(img)
    ax.axis("off")

    for c in data["corridors"]:
        if c["floor"] == current_floor:
            xs = [p[0] for p in c["points"]]
            ys = [p[1] for p in c["points"]]
            ax.plot(xs, ys, "g", linewidth=2)

    for r in data["rooms"]:
        if r["floor"] == current_floor:
            ax.scatter(*r["pos"], c="blue")
            ax.text(r["pos"][0]+5, r["pos"][1]-5, r["id"], color="blue")
            if r["snap"]:
                ax.plot([r["pos"][0], r["snap"][0]],
                        [r["pos"][1], r["snap"][1]], "b--")

    for e in data["exits"]:
        if e["floor"] == current_floor:
            ax.scatter(*e["pos"], c="red", marker="s")
            ax.text(e["pos"][0]+5, e["pos"][1]-5, e["id"], color="red")
            if e["snap"]:
                ax.plot([e["pos"][0], e["snap"][0]],
                        [e["pos"][1], e["snap"][1]], "r--")

    for s in data["stairs"]:
        if s["floor"] == current_floor:
            ax.scatter(*s["pos"], c="purple")
            ax.text(s["pos"][0]+5, s["pos"][1]-5, s["id"], color="purple")

    ax.set_title(
        f"{building} | {current_floor} | MODE: {mode.upper()} | Undo: {len(undo_stack)}"
    )
    plt.draw()

# ================== CLICK ==================
def onclick(event):
    global corridor_start, selected, mode
    global room_count, exit_count, stair_count

    if event.xdata is None:
        return

    x, y = int(event.xdata), int(event.ydata)

    if mode == "room":
        save_undo()
        name = simpledialog.askstring("Room", "Room number:", initialvalue=f"R{room_count}") or f"R{room_count}"
        data["rooms"].append({
            "id": name,
            "pos": (x, y),
            "floor": current_floor,
            "snap": nearest_corridor((x, y))
        })
        room_count += 1

    elif mode == "exit":
        save_undo()
        name = simpledialog.askstring("Exit", "Exit name:", initialvalue=f"EXIT_{exit_count}") or f"EXIT_{exit_count}"
        data["exits"].append({
            "id": name,
            "pos": (x, y),
            "floor": current_floor,
            "snap": nearest_corridor((x, y))
        })
        exit_count += 1

    elif mode == "stair":
        save_undo()
        name = simpledialog.askstring("Stair", "Stair ID:", initialvalue=f"S{stair_count}") or f"S{stair_count}"
        data["stairs"].append({
            "id": name,
            "pos": (x, y),
            "floor": current_floor
        })
        stair_count += 1

    elif mode == "draw":
        if corridor_start is None:
            corridor_start = (x, y)
        else:
            save_undo()
            data["corridors"].append({
                "floor": current_floor,
                "points": interpolate(corridor_start, (x, y))
            })
            corridor_start = None

    elif mode == "snap":
        if selected is None:
            for r in data["rooms"] + data["exits"]:
                if r["floor"] == current_floor and dist(r["pos"], (x, y)) < 15:
                    selected = r
                    return
        else:
            save_undo()
            selected["snap"] = (x, y)
            selected = None
            mode = "room"

    redraw()

# ================== KEYS ==================
def onkey(event):
    global mode, current_floor

    if event.key == "r":
        mode = "room"
    elif event.key == "e":
        mode = "exit"
    elif event.key == "t":
        mode = "stair"
    elif event.key == "d":
        mode = "draw"
    elif event.key == "m":
        mode = "snap"
    elif event.key == "u":
        if undo_stack:
            data.clear()
            data.update(undo_stack.pop())
    elif event.key == "f":
        keys = sorted(data["floors"].keys())
        current_floor = keys[(keys.index(current_floor) + 1) % len(keys)]
    elif event.key == "x":
        confirm = simpledialog.askstring(
            "Confirm",
            f"Type YES to clear all mappings on {current_floor}:"
        )
        if confirm == "YES":
            clear_current_floor()
            print(f"🧹 Cleared mappings on {current_floor}")
    elif event.key == "s":
        db["buildings"][building] = data
        with open(FILE, "w") as f:
            json.dump(db, f, indent=2)
        print("✅ Saved")
    elif event.key == "q":
        plt.close()

    redraw()

# ================== INIT ==================
fig, ax = plt.subplots(figsize=(10, 8))
fig.canvas.mpl_connect("button_press_event", onclick)
fig.canvas.mpl_connect("key_press_event", onkey)

redraw()
plt.show()
