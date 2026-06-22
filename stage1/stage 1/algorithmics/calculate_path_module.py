import numpy as np
import heapq
import networkx as nx
from shapely.geometry import Polygon, Point, LineString
from algorithmics.enemy.black_hole import BlackHole
from algorithmics.enemy.asteroids_zone import AsteroidsZone

def calculate_path(start_coord, end_coord, enemies):
    count = 0
    start_coord = (start_coord.x, start_coord.y)
    end_coord = (end_coord.x, end_coord.y)
    print(start_coord, end_coord)
    start = a_star_coord(start_coord)
    start.heuristics = euclidian_dist(start_coord, end_coord)
    start.cost = 0
    start.f = start.heuristics + start.cost

    openList = []
    openListCoords = set()
    heapq.heappush(openList, (start.f, count, start))
    count += 1

    closedList = set()

    while len(openList) > 0:
        current = heapq.heappop(openList)[2]

        if (current.coord[0] == end_coord[0]) and (current.coord[1] == end_coord[1]):
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

                heapq.heappush(openList, (neighbor_object.f, count, neighbor_object))
                count += 1
                openListCoords.add(neighbor)
                print(neighbor)

    return False, None

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

                if have_valid_path2(self.coord, (self.coord[0] + dx, self.coord[1] + dy), enemies):
                    if (self.coord[0] + dx >= -5) and (self.coord[0] + dx <= 60) and (self.coord[1] + dy >= -5) and (self.coord[1] + dy <= 60):
                        neighbors.append((self.coord[0] + dx, self.coord[1] + dy))

        return neighbors

    def getCoordinateObject(self):
        coord = Coordinate(self.coord[0], self.coord[1])
        return coord


def construct_path(node):
    lst = [node.getCoordinateObject()]
    while node.parent is not None:
        node = node.parent
        lst.append(node.getCoordinateObject())
    path = lst[::-1]
    return path, create_path_graph_from_coords(path)

def euclidian_dist(coord1: tuple[int, int], coord2) -> int:
    x = coord2[0] - coord1[0]
    y = coord2[1] - coord1[0]
    dist = (x * x + y * y) ** 0.5
    return dist

def have_valid_path(cor_1, cor_2 , enemies):
    line = LineString([cor_1, cor_2])
    for i in enemies:
        if isinstance(i, BlackHole):
            circle_center = Point(i.center[0],i.center[1])
            circle = circle_center.buffer(i.radius)
            if circle.intersects(line):
                return True

        if isinstance(i, AsteroidsZone):
            poli = []
            for k in i.boundary:
                poli.append((k.x, k.y))
            polygon = Polygon(poli)
            if polygon.intersects(line):
                return True
    return False

def have_valid_path2(cor_1, cor_2 , enemies):
    return True

def create_path_graph_from_coords(coords):
    G = nx.Graph()
    for i, coord in enumerate(coords):
        G.add_node(i, pos=coord)
        if i > 0:
            G.add_edge(i - 1, i)

    return G

import math


class Coordinate:
    """User-friendly coordinate class allowing for a broad range of operations

    Some Examples
    ----------------------------

    Creation & Basic Arithmetics
    ============================

    >>> c1 = Coordinate(2, 3)
    >>> c1 *= 2
    >>> c1
    Coordiante(x=4, y=6)

    >>> c1.x = 5
    >>> c1
    Coordinate(x=5, y=6)

    >>> c2 = Coordinate(x=-3, y=2)
    >>> c3 = c1 + c2
    >>> c3
    Coordinate(x=2, y=8)

    >>> c3 /= 2
    >>> c3
    Coordinate(x=1.0, y=4.0)

    Comparions
    ==========

    >>> c1 == Coordinate(5, 6)
    True
    >>> c1 == c3
    False

    Some Functions
    ==============

    >>> c3.distance_to(c2)
    4.47213595499958
    >>> c3.norm()
    4.123105625617661

    >>> import math
    >>> math.degrees(c3.direction_to(c1))
    26.5650511770779

    >>> str(c3), repr(c3)
    ('Coordiante(x=1.0, y=4.0)', 'Coordinate(x=1.0, y=4.0)')
    """

    def __init__(self, x: float, y: float) -> None:
        """Initializes a coordinate given its `x`, `y` values

        :param x: x value of the coordinate
        :param y: y value of the coordinate
        """
        super().__init__()

        self.x = x
        self.y = y

    def __eq__(self, o: object) -> bool:
        if not isinstance(o, Coordinate):
            return False
        return math.fabs(self.x - o.x) <= 1e-6 and math.fabs(self.y - o.y) <= 1e-6

    def __neg__(self) -> 'Coordinate':
        return Coordinate(-self.x, -self.y)

    def __add__(self, other) -> 'Coordinate':
        if not isinstance(other, Coordinate):
            raise TypeError('Addition is allowed only between two coordinates')
        return Coordinate(self.x + other.x, self.y + other.y)

    def __sub__(self, other) -> 'Coordinate':
        if not isinstance(other, Coordinate):
            raise TypeError('Subtraction is allowed only between two coordinates')
        return Coordinate(self.x - other.x, self.y - other.y)

    def __truediv__(self, other) -> 'Coordinate':
        if not isinstance(other, (float, int)):
            raise TypeError('Division on coordinate is only possible with a numerical')
        return Coordinate(self.x / other, self.y / other)

    def __mul__(self, other) -> 'Coordinate':
        if not isinstance(other, (float, int)):
            raise TypeError('Multiplication on coordinate is only possible with a numerical')
        return Coordinate(self.x * other, self.y * other)

    def distance_to(self, other: 'Coordinate') -> float:
        """Computes the euclidean distance to the other coordinate
        """
        return math.sqrt((self.x - other.x) ** 2 + (self.y - other.y) ** 2)

    def direction_to(self, other: 'Coordinate') -> float:
        """Computes the direction to the other coordinate
        """
        return math.atan2(other.y - self.y, other.x - self.x)

    def distance_to_squared(self, other: 'Coordinate') -> float:
        """Computes the square of the euclidean distance to the other coordinate
        """
        return (self.x - other.x) ** 2 + (self.y - other.y) ** 2

    def norm(self) -> float:
        """Computes the norm of this 2d vector
        """
        return math.sqrt(self.x ** 2 + self.y ** 2)

    def __str__(self) -> str:
        return f'Coordinate(x={self.x}, y={self.y})'

    def __repr__(self) -> str:
        return str(self)

    @classmethod
    def from_str(cls, s: str) -> 'Coordinate':
        """Compute coordinate from string representation

        :param s: string representing a coordinate
        :return: coordinate object
        """
        # Remove 'Coordinate' heading and parenthesis
        s = s[11:-1]

        # Split to components
        x, y = s.split(', ')

        # Remove 'x=', 'y=' headers
        x, y = x[2:], y[2:]

        # Convert to floats
        x, y = float(x), float(y)

        # Return coordinate object
        return Coordinate(x, y)

    def __hash__(self) -> int:
        return hash(self.x) ^ hash(self.y)

    def shifted(self, distance: float, bearing: float) -> 'Coordinate':
        dx = distance * math.cos(bearing)
        dy = distance * math.sin(bearing)

        return Coordinate(self.x + dx, self.y + dy)

    def dot(self, other: 'Coordinate') -> float:
        return self.x * other.x + self.y * other.y

    def cross(self, other: 'Coordinate') -> float:
        return self.x * other.y - self.y * other.x

