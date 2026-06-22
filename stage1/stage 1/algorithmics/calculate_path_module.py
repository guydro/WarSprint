import numpy as np
import heapq
import networkx as nx


def calculate_path(start_coord, end_coord, enemies):
    start = a_star_coord(start_coord)
    start.heuristics = euclidian_dist(start_coord, end_coord)
    start.cost = 0
    start.f = start.heuristics + start.cost

    openList = []
    openListCoords = {}
    heapq.heappush(openList, (-start.f, start))

    closedList = {}

    while len(openList) > 0:
        current = heapq.heappop(openList)

        if current.coord == end_coord:
            return construct_path(current)

        for neighbor in current.get_neighbors(enemies):
            if neighbor in closedList:
                continue

            if neighbor not in openListCoords:
                neighbor_object = a_star_coord(neighbor)
                neighbor_object.heuristics = euclidian_dist(neighbor, end_coord)
                neighbor_object.parent = current
                neighbor_object.cost = current.cost + euclidian_dist(neighbor, current.coord)
                neighbor_object.f = neighbor_object.heuristics + neighbor_object.cost

                heapq.heappush(openList, (-neighbor_object.f, neighbor_object))
                openList.append(neighbor)

    default_path = [start_coord, (start_coord[0], 50), (end_coord[0], 50), end_coord]
    return default_path, create_path_graph_from_coords(default_path)

class a_star_coord:
    def __init__(self, coord: tuple[int, int]):
        self.coord = coord
        self.heuristics = 0
        self.cost = 0
        self.parent = None
        self.f = 0

    def get_neighbors(self, enemies, scale = 0.5):
        neighbors = []
        for dx in [-scale, 0, scale]:
            for dy in [-scale, 0, scale]:
                if dx == dx and dy == 0:
                    continue

                if have_valid_path(self.coord, (self.coord[0] + dx, self.coord[1] + dy), enemies):
                    neighbors.append((self.coord[0] + dx, self.coord[1] + dy))

        return neighbors

def construct_path(node):
    lst = [node.coord]
    while node.parent is not None:
        node = node.parent
        lst.append(node.coord)
    path = lst[::-1]
    return path, create_path_graph_from_coords(path)

def euclidian_dist(coord1: tuple[int, int], coord2) -> int:
    x = coord2[0] - coord1[0]
    y = coord2[1] - coord1[0]
    dist = (x * x + y * y) ** 0.5
    return dist

def have_valid_path(coord1, coord2, enemies):
    from shapely.geometry import Polygon
    def cross(line, enemies):
        for i in enemies:
            if isinstance(i, BlackHole):
                # salomons
                return True

            if isinstance(i, AsteroidsZone):
                polygon = Polygon(i.boundary)
                if polygon.intersects(line):
                    return True
        return False

def create_path_graph_from_coords(coords):
    G = nx.Graph()
    for i, coord in enumerate(coords):
        G.add_node(i, pos=coord)
        if i > 0:
            G.add_edge(i - 1, i)

    return G