from typing import List

from algorithmics.enemy.enemy import Enemy
from algorithmics.utils.coordinate import Coordinate


class AsteroidsZone(Enemy):

    def __init__(self, boundary: List[Coordinate]):
        """Initializes a new asteroids zone area

        :param boundary: list of coordiantes representing the boundary of the asteroids zone
        """
        self.boundary = boundary
