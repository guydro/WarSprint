from typing import List

from algorithmics.enemy.enemy import Enemy
from algorithmics.enemy.radar import Radar
from algorithmics.utils.coordinate import Coordinate


class Environment:

    def __init__(self, enemies: List[Enemy]):
        self.enemies = enemies
        self.no_entrances = [enemy for enemy in enemies if not isinstance(enemy, Radar)]
        self.radars = [enemy for enemy in enemies if isinstance(enemy, Radar)]

    def is_legal_leg(self, start: Coordinate, end: Coordinate) -> bool:
        """Assert that the movement from start to end is legal, regarding all enemies

        :param start: start of the movement
        :param end: destination of the movement
        :return: True if the leg is legal, False otherwise
        """
        return all(enemy.is_legal_leg(start, end) for enemy in self.enemies)

    def is_leg_legal_only_no_entrances(self, start: Coordinate, end: Coordinate) -> bool:
        """Assert that the movement from start to end is legal, regarding only no-entrances

        :param start: start of the movement
        :param end: destination of the movement
        :param enemies: enemies to be considered
        :return: True if the leg is legal, False otherwise
        """
        return all(enemy.is_legal_leg(start, end) for enemy in self.no_entrances)

    def is_leg_legal_only_radars(self, start: Coordinate, end: Coordinate) -> bool:
        """Assert that the movement from start to end is legal, regarding only radars

        :param start: start of the movement
        :param end: destination of the movement
        :return: True if the leg is legal, False otherwise
        """
        return all(enemy.is_legal_leg(start, end) for enemy in self.radars)

