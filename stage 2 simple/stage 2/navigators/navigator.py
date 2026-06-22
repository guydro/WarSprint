from abc import ABC, abstractmethod
from typing import List

import networkx as nx

from algorithmics.utils.coordinate import Coordinate


class Navigator(ABC):

    def navigate(self, graph: nx.DiGraph, source: Coordinate, targets: List[Coordinate], max_detection: float) -> \
            List[Coordinate]:
        """Find path in the graph

        :param graph: graph to be searched
        :param source: source of the path
        :param targets: visit-required targets of the path
        :param max_detection: maximal allowed detection in path
        :return: computed path
        """

        self.assert_input_legality(targets, max_detection)

        try:
            print('Computing path')
            path = self.compute_path(graph, source, targets, max_detection)
        # If not path exists, return an empty path
        except nx.NetworkXNoPath:
            path = []

        print('Returning path')
        return path

    @abstractmethod
    def compute_path(self, graph: nx.DiGraph, source: Coordinate, targets: List[Coordinate], max_detection: float) -> \
            List[Coordinate]:
        """Perform the path search algorithm

        :param graph: graph to be searched
        :param source: source of the path
        :param targets: visit-required targets of the path
        :param max_detection: maximal allowed detection in path
        :return: computed path
        """
        pass

    @abstractmethod
    def assert_input_legality(self, targets: List[Coordinate], max_detection: float) -> None:
        """Verify that the input matches assumptions of the navigator

        :param targets: visit-required targets of the path
        :param max_detection: maximal allowed detection in path
        :return: None
        :raise: ValueError, if input doesn't match the navigator assumptions
        """
        pass
