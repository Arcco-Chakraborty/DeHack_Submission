#test github
import matplotlib.pyplot as plt
from collections import deque

# ---------------- GRAPH ---------------- #

class Nav:
    def __init__(self):
        self.g = {}
        self.pos = {}

    def add(self, r, x, y):
        self.g.setdefault(r, [])
        self.pos[r] = (x, y)

    def link(self, a, b):
        self.g[a].append(b)
        self.g[b].append(a)

    def shortest(self, s, e):
        q = deque([[s]])
        seen = set()
        while q:
            p = q.popleft()
            r = p[-1]
            if r == e:
                return p
            if r not in seen:
                seen.add(r)
                for n in self.g[r]:
                    q.append(p + [n])
        return []


nav = Nav()

# ---------------- MAP (RED CORRIDORS) ---------------- #

# Top corridor 1108–1116
for i, r in enumerate(range(1108, 1117)):
    nav.add(r, i, 10)
    if r > 1108:
        nav.link(r, r - 1)

# Bottom corridor 1133–1128
for i, r in enumerate(range(1133, 1127, -1)):
    nav.add(r, i, 0)
    if r < 1133:
        nav.link(r, r + 1)

# Left vertical corridor
left_rooms = [1108,1107,1106,1105,1104,1103,1102,1101]
for i, r in enumerate(left_rooms):
    nav.add(r, -1, 10 - i)
    if i > 0:
        nav.link(r, left_rooms[i-1])

# Right vertical corridor
right_rooms = [1116,1117,1118,1119,1120,1121,1122,1123,1124,1128]
for i, r in enumerate(right_rooms):
    nav.add(r, 9, 10 - i)
    if i > 0:
        nav.link(r, right_rooms[i-1])

# Middle empty corridor (1104 ↔ 1120)
nav.link(1104, 1120)

# ---------------- USER INPUT ---------------- #

start = int(input("Enter start room: "))
end = int(input("Enter destination room: "))

if start not in nav.g or end not in nav.g:
    print("Invalid room number")
    exit()

path = nav.shortest(start, end)
print("Shortest path:", path)

# ---------------- DRAW ---------------- #

# Corridors
for a in nav.g:
    for b in nav.g[a]:
        x1, y1 = nav.pos[a]
        x2, y2 = nav.pos[b]
        plt.plot([x1, x2], [y1, y2])

# Rooms
for r, (x, y) in nav.pos.items():
    plt.scatter(x, y)
    plt.text(x, y + 0.2, str(r), ha="center", fontsize=8)

# Path
px = [nav.pos[r][0] for r in path]
py = [nav.pos[r][1] for r in path]
plt.plot(px, py, linewidth=4)

plt.scatter(*nav.pos[start], s=120)
plt.scatter(*nav.pos[end], s=120)

plt.title("Faculty Division I – Shortest Corridor Path")
plt.axis("equal")
plt.show()