from itertools import combinations
from typing import List

import networkx as nx

from algorithmics.enemy.asteroids_zone import AsteroidsZone
from algorithmics.enemy.black_hole import BlackHole
from algorithmics.enemy.environment import Environment
from algorithmics.enemy.radar import Radar
from algorithmics.extenders.exntender import Extender
from algorithmics.utils.coordinate import Coordinate


class OutlineExtender(Extender):

    def __init__(self, environment: Environment, source: Coordinate, targets: List[Coordinate]):
        self.source = source
        self.targets = targets
        super().__init__(environment)

    def get_enemies_outlines(self) -> List[Coordinate]:
        """Create list of coordinates defining enemies outline

        :return: None
        """

        coordinates = []

        # For every enemy, add nodes to the graph
        for enemy in self.environment.enemies:

            # If the enemy is an asteroid zone, add its corners
            if isinstance(enemy, AsteroidsZone):
                coordinates.extend(enemy.boundary)

            # If the enemy is an observation post, add its approximation
            if isinstance(enemy, BlackHole) or isinstance(enemy, Radar):
                coordinates.extend(enemy.approximate_boundary())

        return coordinates

    def extend(self, graph: nx.DiGraph) -> None:

        print('Initializing graph')

        coordinates = [self.source] + self.targets + self.get_enemies_outlines()
        graph.add_nodes_from(coordinates)
        for start, end in combinations(coordinates, 2):
            self._connect_nodes(graph, start, end)
