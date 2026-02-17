import tkinter as tk
from tkinter import messagebox, ttk
import time
import random
import heapq
from queue import Queue

# --- Constants ---
ROWS = 10
COLS = 10
CELL_SIZE = 50
DELAY = 0.05
DYNAMIC_OBS_PROB = 0.05
IDDFS_MAX_DEPTH = 25

# Colors (modern theme)
EMPTY_COLOR = "#0f1724"
WALL_COLOR = "#020617"
START_COLOR = "#00C2A8"
TARGET_COLOR = "#FF6B6B"
FRONTIER_COLOR = "#FFD166"
EXPLORED_COLOR = "#7DD3FC"
PATH_COLOR = "#A78BFA"
OBSTACLE_COLOR = "#475569"

SIDEBAR_BG = "#071129"
BUTTON_COLOR = "#2563EB"
BUTTON_TEXT_COLOR = "white"
LABEL_COLOR = "#94A3B8"
TEXT_COLOR = "#E6EEF8"

MOVES = [
    (-1, 0),  # Up
    (0, 1),   # Right
    (1, 0),   # Down
    (0, -1),  # Left
    (1, 1),   # Bottom-Right
    (-1, -1)  # Top-Left
]

# --- Logic Classes ---
class Node:
    def __init__(self, r, c, parent=None, cost=0, depth=0):
        self.r = r
        self.c = c
        self.parent = parent
        self.cost = cost
        self.depth = depth

class Cell:
    def __init__(self, row, col, canvas_id):
        self.row = row
        self.col = col
        self.canvas_id = canvas_id
        self.type = "empty"

# --- Main App ---
class GridApp:
    def __init__(self, root):
        self.root = root
        self.root.title("AI Pathfinder - Formatted Version")
        self.mode = "wall"
        self.start_pos = None
        self.target_pos = None
        self.grid = []
        self.algorithm = tk.StringVar(value="BFS")
        self.dls_limit_var = tk.IntVar(value=10)
        self.dynamic_obstacles = tk.BooleanVar(value=False)
        self.stop_flag = False
        self.visit_count = 0
        self.node_visit_map = {}

        # Layout: left sidebar, right canvas, header on top
        root.columnconfigure(0, weight=0)
        root.columnconfigure(1, weight=1)
        root.rowconfigure(0, weight=0)
        root.rowconfigure(1, weight=1)

        header = tk.Frame(root, bg=SIDEBAR_BG)
        header.grid(row=0, column=0, columnspan=2, sticky="ew")
        tk.Label(
            header,
            text="AI Pathfinder",
            bg=SIDEBAR_BG,
            fg=TEXT_COLOR,
            font=("Segoe UI", 14, "bold")
        ).pack(side="left", padx=12, pady=8)

        # Sidebar (left)
        sidebar = tk.Frame(root, bg=SIDEBAR_BG)
        sidebar.grid(row=1, column=0, sticky="ns", padx=8, pady=12)
        sidebar.columnconfigure(0, weight=1)

        tk.Label(
            sidebar,
            text="Node Controls",
            bg=SIDEBAR_BG,
            fg=TEXT_COLOR,
            font=("Segoe UI", 10, "bold")
        ).pack(pady=6)

        tk.Button(
            sidebar,
            text="Set Start Node",
            bg=BUTTON_COLOR,
            fg=BUTTON_TEXT_COLOR,
            command=lambda: self.set_mode("start")
        ).pack(fill="x", pady=4, padx=6)

        tk.Button(
            sidebar,
            text="Set Target Node",
            bg=BUTTON_COLOR,
            fg=BUTTON_TEXT_COLOR,
            command=lambda: self.set_mode("target")
        ).pack(fill="x", pady=4, padx=6)

        tk.Button(
            sidebar,
            text="Place Wall",
            bg=BUTTON_COLOR,
            fg=BUTTON_TEXT_COLOR,
            command=lambda: self.set_mode("wall")
        ).pack(fill="x", pady=4, padx=6)

        tk.Frame(sidebar, height=8, bg=SIDEBAR_BG).pack()

        tk.Button(
            sidebar,
            text="Clear Grid",
            bg="#EF4444",
            fg=BUTTON_TEXT_COLOR,
            command=self.clear_grid
        ).pack(fill="x", pady=4, padx=6)

        tk.Label(
            sidebar,
            text="Select Algorithm:",
            bg=SIDEBAR_BG,
            fg=LABEL_COLOR
        ).pack(pady=(10, 4))

        self.algo_menu = ttk.Combobox(
            sidebar,
            textvariable=self.algorithm,
            state="readonly"
        )
        self.algo_menu['values'] = ("BFS", "DFS", "UCS", "DLS", "IDDFS", "Bidirectional")
        self.algo_menu.pack(fill="x", padx=5)

        tk.Label(sidebar, text="DLS Limit:", bg=SIDEBAR_BG, fg=TEXT_COLOR).pack(pady=(8, 0))
        tk.Spinbox(
            sidebar,
            from_=1,
            to=100,
            textvariable=self.dls_limit_var,
            width=5
        ).pack(pady=4)

        tk.Checkbutton(
            sidebar,
            text="Dynamic Obstacles",
            variable=self.dynamic_obstacles,
            bg=SIDEBAR_BG,
            fg=TEXT_COLOR,
            selectcolor=SIDEBAR_BG
        ).pack(pady=6)

        tk.Button(
            sidebar,
            text="Start Search",
            bg="#10B981",
            fg=BUTTON_TEXT_COLOR,
            font=("Segoe UI", 10, "bold"),
            command=self.start_search
        ).pack(fill="x", pady=(10, 6), padx=6)

        tk.Button(
            sidebar,
            text="Stop Search",
            bg="#F59E0B",
            fg=BUTTON_TEXT_COLOR,
            command=self.stop_search
        ).pack(fill="x", pady=4, padx=6)

        tk.Frame(sidebar, height=20, bg=SIDEBAR_BG).pack()
        tk.Label(
            sidebar,
            text="Search Status:",
            bg=SIDEBAR_BG,
            fg=TEXT_COLOR,
            font=("Segoe UI", 9, "bold")
        ).pack()

        self.status_lbl = tk.Label(
            sidebar,
            text="Ready",
            bg=SIDEBAR_BG,
            fg=TEXT_COLOR,
            relief="sunken",
            width=18,
            anchor="w",
            padx=6
        )
        self.status_lbl.pack(pady=8, padx=6)

        # Canvas Setup (right)
        self.canvas = tk.Canvas(
            root,
            width=COLS * CELL_SIZE,
            height=ROWS * CELL_SIZE,
            bg=EMPTY_COLOR,
            highlightthickness=0
        )
        self.canvas.grid(row=1, column=1, sticky="nsew", padx=12, pady=12)
        self.canvas.bind("<Button-1>", self.cell_clicked)
        self.canvas.bind("<B1-Motion>", self.cell_clicked)

        self.create_grid()

    def set_status(self, text, color="black"):
        self.status_lbl.config(text=text, fg=color)

    def create_grid(self):
        for row in range(ROWS):
            row_cells = []
            for col in range(COLS):
                x1 = col * CELL_SIZE
                y1 = row * CELL_SIZE
                x2 = x1 + CELL_SIZE
                y2 = y1 + CELL_SIZE
                rect = self.canvas.create_rectangle(
                    x1, y1, x2, y2, 
                    fill=EMPTY_COLOR, 
                    outline="gray"
                )
                self.canvas.create_text(
                    x1 + CELL_SIZE // 2, 
                    y1 + CELL_SIZE // 2, 
                    text="", 
                    fill=TEXT_COLOR, 
                    tags=f"text_{row}_{col}"
                )
                row_cells.append(Cell(row, col, rect))
            self.grid.append(row_cells)

    def set_mode(self, mode):
        self.mode = mode

    def cell_clicked(self, event):
        col = event.x // CELL_SIZE
        row = event.y // CELL_SIZE
        if not (0 <= row < ROWS and 0 <= col < COLS):
            return
        cell = self.grid[row][col]
        if self.mode == "start":
            if self.start_pos:
                self.update_cell_type(self.start_pos[0], self.start_pos[1], "empty")
            self.start_pos = (row, col)
            self.update_cell_type(row, col, "start")
        elif self.mode == "target":
            if self.target_pos:
                self.update_cell_type(self.target_pos[0], self.target_pos[1], "empty")
            self.target_pos = (row, col)
            self.update_cell_type(row, col, "target")
        elif self.mode == "wall":
            if (row, col) not in (self.start_pos, self.target_pos):
                self.update_cell_type(row, col, "wall")
        elif self.mode == "clear":
            if (row, col) == self.start_pos:
                self.start_pos = None
            if (row, col) == self.target_pos:
                self.target_pos = None
            self.update_cell_type(row, col, "empty")

    def update_cell_type(self, r, c, type_name):
        self.grid[r][c].type = type_name
        self.update_cell_color(r, c)

    def update_cell_color(self, row, col, number=None):
        cell = self.grid[row][col]
        colors = {
            "empty": EMPTY_COLOR, 
            "wall": WALL_COLOR, 
            "start": START_COLOR, 
            "target": TARGET_COLOR, 
            "explored": EXPLORED_COLOR, 
            "frontier": FRONTIER_COLOR, 
            "path": PATH_COLOR, 
            "obstacle": OBSTACLE_COLOR
        }
        color = colors.get(cell.type, EMPTY_COLOR)
        self.canvas.itemconfig(cell.canvas_id, fill=color)
        self.canvas.delete(f"text_{row}_{col}")
        if number is not None:
            self.canvas.create_text(
                col * CELL_SIZE + CELL_SIZE // 2, 
                row * CELL_SIZE + CELL_SIZE // 2, 
                text=str(number), 
                fill=TEXT_COLOR, 
                tags=f"text_{row}_{col}"
            )

    def get_neighbors(self, r, c):
        neighbors = []
        for dr, dc in MOVES:
            nr = r + dr
            nc = c + dc
            if 0 <= nr < ROWS and 0 <= nc < COLS:
                if self.grid[nr][nc].type not in ("wall", "obstacle"):
                    neighbors.append((nr, nc))
        return neighbors

    def spawn_dynamic_obstacle(self):
        if self.dynamic_obstacles.get() and random.random() < DYNAMIC_OBS_PROB:
            empty_cells = []
            for r in range(ROWS):
                for c in range(COLS):
                    if self.grid[r][c].type == "empty":
                        empty_cells.append(self.grid[r][c])
            if empty_cells:
                cell = random.choice(empty_cells)
                cell.type = "obstacle"
                self.update_cell_color(cell.row, cell.col)

    def animate_node(self, row, col):
        if self.stop_flag:
            raise StopIteration
        cell = self.grid[row][col]
        if (row, col) != self.start_pos and (row, col) != self.target_pos:
            cell.type = "explored"
            self.visit_count += 1
            self.node_visit_map[(row, col)] = self.visit_count 
            self.update_cell_color(row, col, number=self.visit_count)
        
        self.root.update()
        time.sleep(DELAY)
        self.spawn_dynamic_obstacle()

    def clear_grid(self):
        self.start_pos = None
        self.target_pos = None
        self.stop_flag = True
        self.node_visit_map = {}
        self.set_status("Ready")
        for row in self.grid:
            for cell in row:
                cell.type = "empty"
                self.update_cell_color(cell.row, cell.col)

    def clear_path_only(self):
        self.visit_count = 0
        self.node_visit_map = {}
        for row in self.grid:
            for cell in row:
                if cell.type in ("explored", "frontier", "path"):
                    cell.type = "empty"
                    self.update_cell_color(cell.row, cell.col)

    def stop_search(self):
        self.stop_flag = True
        self.set_status("Stopped", "red")

    def reconstruct_path(self, node):
        curr = node
        while curr:
            r = curr.r
            c = curr.c
            if (r, c) != self.start_pos and (r, c) != self.target_pos:
                self.grid[r][c].type = "path"
                num = self.node_visit_map.get((r, c))
                self.update_cell_color(r, c, number=num)
                self.root.update()
                time.sleep(DELAY)
            curr = curr.parent

    def start_search(self):
        if not self.start_pos or not self.target_pos:
            messagebox.showwarning("Warning", "Place Start and Target nodes!")
            return
        self.clear_path_only()
        self.stop_flag = False
        self.set_status("Searching...", "blue")
        algo = self.algorithm.get()
        found_node = None
        try:
            if algo == "BFS":
                found_node = self.run_bfs()
            elif algo == "DFS":
                found_node = self.run_dfs()
            elif algo == "UCS":
                found_node = self.run_ucs()
            elif algo == "DLS":
                found_node = self.run_dls(self.dls_limit_var.get())
            elif algo == "IDDFS":
                found_node = self.run_iddfs()
            elif algo == "Bidirectional":
                found_node = self.run_bidirectional()
            
            if found_node:
                if algo != "Bidirectional":
                    self.reconstruct_path(found_node.parent)
                self.set_status("Path Found!", "green")
            else:
                self.set_status("Not Found", "red")
        except StopIteration:
            pass

    def run_bfs(self):
        q = [Node(*self.start_pos)]
        visited = {self.start_pos}
        while q:
            curr = q.pop(0)
            if (curr.r, curr.c) == self.target_pos:
                return curr
            self.animate_node(curr.r, curr.c)
            for nr, nc in self.get_neighbors(curr.r, curr.c):
                if (nr, nc) not in visited:
                    visited.add((nr, nc))
                    q.append(Node(nr, nc, curr))
        return None

    def run_dfs(self):
        stack = [Node(*self.start_pos)]
        visited = set()
        while stack:
            curr = stack.pop()
            if (curr.r, curr.c) == self.target_pos:
                return curr
            if (curr.r, curr.c) not in visited:
                visited.add((curr.r, curr.c))
                self.animate_node(curr.r, curr.c)
                for nr, nc in reversed(self.get_neighbors(curr.r, curr.c)):
                    if (nr, nc) not in visited:
                        stack.append(Node(nr, nc, curr))
        return None

    def run_ucs(self):
        pq = []
        start_node = Node(*self.start_pos, cost=0)
        heapq.heappush(pq, (0, id(start_node), start_node))
        visited = {}
        while pq:
            cost, _, curr = heapq.heappop(pq)
            if (curr.r, curr.c) == self.target_pos:
                return curr
            if (curr.r, curr.c) in visited and visited[(curr.r, curr.c)] <= cost:
                continue
            visited[(curr.r, curr.c)] = cost
            self.animate_node(curr.r, curr.c)
            for nr, nc in self.get_neighbors(curr.r, curr.c):
                new_cost = cost + 1
                neighbor = Node(nr, nc, curr, new_cost)
                heapq.heappush(pq, (new_cost, id(neighbor), neighbor))
        return None

    def run_dls(self, limit):
        visited = set()
        return self._dls_recursive(Node(*self.start_pos), limit, visited)

    def _dls_recursive(self, curr, limit, visited):
        if self.stop_flag:
            raise StopIteration
        if (curr.r, curr.c) == self.target_pos:
            return curr
        if limit <= 0:
            return None
        visited.add((curr.r, curr.c))
        self.animate_node(curr.r, curr.c)
        for nr, nc in self.get_neighbors(curr.r, curr.c):
            if (nr, nc) not in visited:
                res = self._dls_recursive(Node(nr, nc, curr), limit - 1, visited)
                if res:
                    return res
        return None

    def run_iddfs(self):
        for depth in range(IDDFS_MAX_DEPTH):
            self.clear_path_only()
            self.set_status(f"Searching D:{depth}", "blue")
            res = self.run_dls(depth)
            if res:
                return res
            if self.stop_flag:
                break
        return None

    def run_bidirectional(self):
        v1 = {self.start_pos: Node(*self.start_pos)}
        v2 = {self.target_pos: Node(*self.target_pos)}
        q1 = [v1[self.start_pos]]
        q2 = [v2[self.target_pos]]
        while q1 and q2:
            curr_f = q1.pop(0)
            self.animate_node(curr_f.r, curr_f.c)
            if (curr_f.r, curr_f.c) in v2:
                self.merge_bidir(curr_f, v2[(curr_f.r, curr_f.c)])
                return curr_f
            for n in self.get_neighbors(curr_f.r, curr_f.c):
                if n not in v1:
                    v1[n] = Node(*n, curr_f)
                    q1.append(v1[n])
            curr_b = q2.pop(0)
            self.animate_node(curr_b.r, curr_b.c)
            if (curr_b.r, curr_b.c) in v1:
                self.merge_bidir(v1[(curr_b.r, curr_b.c)], curr_b)
                return curr_b
            for n in self.get_neighbors(curr_b.r, curr_b.c):
                if n not in v2:
                    v2[n] = Node(*n, curr_b)
                    q2.append(v2[n])
        return None

    def merge_bidir(self, node_f, node_b):
        self.reconstruct_path(node_f)
        self.reconstruct_path(node_b)

if __name__ == "__main__":
    root = tk.Tk()
    app = GridApp(root)
    root.mainloop()