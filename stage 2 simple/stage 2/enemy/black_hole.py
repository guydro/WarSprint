import math
from typing import List

from algorithmics.enemy.asteroids_zone import AsteroidsZone
from algorithmics.utils.coordinate import Coordinate


class BlackHole(AsteroidsZone):

    def __init__(self, center: Coordinate, radius: float):
        """Initializes a new black hole object anchored at the given point

        :param center: the location of the black hole
        :param radius: radius of the post
        """
        self.center = center
        self.radius = radius

        approximated_polygon = self.approximate_boundary()
        super().__init__(approximated_polygon)

    def approximate_boundary(self, n: int = 20) -> List[Coordinate]:
        """Compute polygon approximating the boundary of the post

        The returned polygon will out-bound the circle

        :param n: number of vertices in the approximation polygon
        :return: polygon approximating the circle
        """

        angle_step = math.radians(360 / n)
        buffed_radius = self.radius / math.cos(angle_step / 2)
        return [Coordinate(self.center.x + buffed_radius * math.sin(i * angle_step),
                           self.center.y + buffed_radius * math.cos(i * angle_step))
                for i in range(n)]
