from abc import ABC, abstractmethod

import networkx as nx

from algorithmics.enemy.environment import Environment
from algorithmics.utils.coordinate import Coordinate


class Extender(ABC):
    """Responsible for extending a graph with certain logic"""

    def __init__(self, environment: Environment):
        self.environment = environment

    def _connect_nodes(self, graph: nx.DiGraph, start: Coordinate, end: Coordinate) -> None:
        """Add the edge (start, end) in both directions

        :param graph: graph to be extended
        :param start: start node of the new edge
        :param end: end node of the new edge
        :return: None
        """

        if not self.environment.is_leg_legal_only_no_entrances(start, end):
            return

        dist = start.distance_to(end)
        graph.add_edge(start, end, dist=dist)
        graph.add_edge(end, start, dist=dist)

    @abstractmethod
    def extend(self, graph: nx.DiGraph) -> None:
        pass
