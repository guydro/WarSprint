from typing import List, Tuple

import networkx as nx

from algorithmics.enemy.enemy import Enemy
from algorithmics.enemy.environment import Environment
from algorithmics.extenders.outline_extender import OutlineExtender
from algorithmics.navigators.simple_navigator import SimpleNavigator
from algorithmics.utils.coordinate import Coordinate


# Navigator


def calculate_path(source: Coordinate, targets: List[Coordinate], enemies: List[Enemy], allowed_detection: float = 0) \
        -> Tuple[List[Coordinate], nx.Graph]:
    """Calculates a path from source to target without any detection

    Note: The path must start at the source coordinate and end at the target coordinate!

    :param source: source coordinate of the spaceship
    :param targets: target coordinate of the spaceship
    :param enemies: list of enemies along the way
    :param allowed_detection: maximum allowed distance of radar detection
    :return: list of calculated path waypoints and the graph constructed
    """

    graph = nx.DiGraph()
    env = Environment(enemies)

    OutlineExtender(env, source, targets).extend(graph)

    path = SimpleNavigator().navigate(graph, source, targets, allowed_detection)
    return path, graph
