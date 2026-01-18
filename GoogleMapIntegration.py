import tkinter as tk
from tkinter import messagebox
from tkintermapview import TkinterMapView

import osmnx as ox
import networkx as nx
from shapely.geometry import LineString
import math


# -------------------------------------------------
# Distance helper (meters)
# -------------------------------------------------
def haversine_m(lat1, lon1, lat2, lon2):
    R = 6371000
    p1 = math.radians(lat1)
    p2 = math.radians(lat2)
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = math.sin(dlat / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dlon / 2) ** 2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return R * c


# -------------------------------------------------
# Load Crescent Road/Walk Graph using OSMnx
# -------------------------------------------------
def load_crescent_graph():
    # Crescent Institute approx center
    center = (12.8746, 80.0862)

    # Small radius for campus area (meters)
    dist = 1200  # 1.2 km around campus

    # network_type:
    # "walk" gives walkable paths (best for campus)
    # "drive" gives roads only
    G = ox.graph_from_point(center, dist=dist, network_type="walk", simplify=True)

    # Add edge length (meters)
    G = ox.distance.add_edge_lengths(G)

    return G


# -------------------------------------------------
# Tkinter App
# -------------------------------------------------
class CrescentModuleRouting:
    def __init__(self, root):
        self.root = root
        self.root.title("Crescent Campus Routing (OSMnx + NetworkX)")
        self.root.geometry("1300x750")

        self.center_lat = 12.8746
        self.center_lon = 80.0862

        self.mode = None
        self.start = None
        self.end = None

        self.start_marker = None
        self.end_marker = None
        self.route_path = None

        # Load graph once (module-based road/path data)
        self.status_text = "Loading campus graph..."
        self.graph = None
        self.load_graph()

        self.build_ui()

    def load_graph(self):
        try:
            self.graph = load_crescent_graph()
        except Exception as e:
            messagebox.showerror("Graph Load Error", str(e))
            self.graph = None

    def build_ui(self):
        left = tk.Frame(self.root, width=350, bg="#f6f6f6")
        left.pack(side="left", fill="y")

        title = tk.Label(left, text="🧭 Crescent Campus Routing", font=("Arial", 17, "bold"), bg="#f6f6f6")
        title.pack(pady=12)

        self.status_label = tk.Label(left, text="Status: Ready", font=("Arial", 12, "bold"), bg="#f6f6f6")
        self.status_label.pack(pady=5)

        self.btn_start = tk.Button(left, text="📍 Set Start", height=2, command=self.set_start_mode)
        self.btn_end = tk.Button(left, text="🎯 Set End", height=2, command=self.set_end_mode)
        self.btn_route = tk.Button(left, text="🧠 Calculate Shortest Path", height=2, command=self.route_now)
        self.btn_clear = tk.Button(left, text="🧹 Clear", height=2, command=self.clear_all)

        self.btn_start.pack(fill="x", padx=15, pady=6)
        self.btn_end.pack(fill="x", padx=15, pady=6)
        self.btn_route.pack(fill="x", padx=15, pady=6)
        self.btn_clear.pack(fill="x", padx=15, pady=6)

        self.start_info = tk.Label(left, text="Start: not set", font=("Arial", 11), bg="#f6f6f6")
        self.end_info = tk.Label(left, text="End: not set", font=("Arial", 11), bg="#f6f6f6")
        self.summary_info = tk.Label(left, text="Distance: -", font=("Arial", 11, "bold"), bg="#f6f6f6")

        self.start_info.pack(pady=10)
        self.end_info.pack(pady=5)
        self.summary_info.pack(pady=10)

        self.map_widget = TkinterMapView(self.root, corner_radius=0)
        self.map_widget.pack(side="right", fill="both", expand=True)

        self.map_widget.set_position(self.center_lat, self.center_lon)
        self.map_widget.set_zoom(16)
        self.map_widget.add_left_click_map_command(self.on_click)

        self.map_widget.set_marker(self.center_lat, self.center_lon, text="Crescent University")

        if self.graph is None:
            self.status_label.config(text="Status: ❌ Graph not loaded (check internet)")

    def set_start_mode(self):
        self.mode = "start"
        self.status_label.config(text="Status: Click map to set START")

    def set_end_mode(self):
        self.mode = "end"
        self.status_label.config(text="Status: Click map to set END")

    def on_click(self, coords):
        lat, lon = coords

        if self.mode == "start":
            self.start = (lat, lon)
            self.start_info.config(text=f"Start: {lat:.6f}, {lon:.6f}")
            self.status_label.config(text="Status: ✅ Start set")
            self.mode = None

            if self.start_marker:
                self.start_marker.delete()
            self.start_marker = self.map_widget.set_marker(lat, lon, text="START")

        elif self.mode == "end":
            self.end = (lat, lon)
            self.end_info.config(text=f"End: {lat:.6f}, {lon:.6f}")
            self.status_label.config(text="Status: ✅ End set")
            self.mode = None

            if self.end_marker:
                self.end_marker.delete()
            self.end_marker = self.map_widget.set_marker(lat, lon, text="END")

    def route_now(self):
        if self.graph is None:
            messagebox.showerror("Graph Error", "Graph not loaded. Check internet or try again.")
            return

        if not self.start or not self.end:
            messagebox.showwarning("Missing Points", "Please set both Start and End.")
            return

        self.status_label.config(text="Status: ⏳ Computing shortest path...")
        self.root.update_idletasks()

        try:
            # Find nearest graph nodes
            start_node = ox.distance.nearest_nodes(self.graph, X=self.start[1], Y=self.start[0])
            end_node = ox.distance.nearest_nodes(self.graph, X=self.end[1], Y=self.end[0])

            # Compute shortest path using NetworkX (module)
            route_nodes = nx.shortest_path(self.graph, start_node, end_node, weight="length")

            # Convert route nodes to lat/lon list
            route_coords = []
            total_dist_m = 0.0

            for i in range(len(route_nodes) - 1):
                u = route_nodes[i]
                v = route_nodes[i + 1]

                lat1 = self.graph.nodes[u]["y"]
                lon1 = self.graph.nodes[u]["x"]
                lat2 = self.graph.nodes[v]["y"]
                lon2 = self.graph.nodes[v]["x"]

                route_coords.append((lat1, lon1))

                # Add distance from edge length
                edge_data = self.graph.get_edge_data(u, v)
                if edge_data:
                    # take the first edge
                    key = list(edge_data.keys())[0]
                    total_dist_m += edge_data[key].get("length", haversine_m(lat1, lon1, lat2, lon2))
                else:
                    total_dist_m += haversine_m(lat1, lon1, lat2, lon2)

            # add last node
            last = route_nodes[-1]
            route_coords.append((self.graph.nodes[last]["y"], self.graph.nodes[last]["x"]))

            dist_km = total_dist_m / 1000.0

            # Draw on map
            if self.route_path:
                self.route_path.delete()

            self.route_path = self.map_widget.set_path(route_coords)

            self.summary_info.config(text=f"Distance: {dist_km:.3f} km")
            self.status_label.config(text="Status: ✅ Path found (NetworkX shortest path)")

        except Exception as e:
            self.status_label.config(text="Status: ❌ Pathfinding failed")
            messagebox.showerror("Pathfinding Error", str(e))

    def clear_all(self):
        self.mode = None
        self.start = None
        self.end = None

        self.start_info.config(text="Start: not set")
        self.end_info.config(text="End: not set")
        self.summary_info.config(text="Distance: -")
        self.status_label.config(text="Status: Ready")

        if self.start_marker:
            self.start_marker.delete()
            self.start_marker = None

        if self.end_marker:
            self.end_marker.delete()
            self.end_marker = None

        if self.route_path:
            self.route_path.delete()
            self.route_path = None


if __name__ == "__main__":
    root = tk.Tk()
    app = CrescentModuleRouting(root)
    root.mainloop()
