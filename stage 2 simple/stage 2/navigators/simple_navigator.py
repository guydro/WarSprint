from typing import List

import networkx as nx

from algorithmics.navigators.navigator import Navigator
from algorithmics.utils.coordinate import Coordinate


class SimpleNavigator(Navigator):
    """Navigator that deals with single-target in a no-detection case"""

    def compute_path(self, graph: nx.DiGraph, source: Coordinate, targets: List[Coordinate], max_detection: float) -> \
            List[Coordinate]:
        return nx.shortest_path(graph, source, targets[0], weight='dist')

    def assert_input_legality(self, targets: List[Coordinate], max_detection: float) -> None:
        if len(targets) == 1 and max_detection == 0:
            return

        raise ValueError(f'Illegal input for {type(self)}')
