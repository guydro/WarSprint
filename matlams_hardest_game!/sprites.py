"""Game entities: the player square, patrolling enemy circles and coins."""

import math
import pygame

from config import (PLAYER_SIZE, PLAYER_SPEED, BLUE, BLUE_DARK, RED, RED_DARK,
                    YELLOW, YELLOW_DARK, COIN_RADIUS, CHASER, CHASER_DARK)


def circle_rect_hit(cx, cy, r, rect):
    """True if the circle (cx, cy, r) overlaps the pygame Rect."""
    nearest_x = max(rect.left, min(cx, rect.right))
    nearest_y = max(rect.top, min(cy, rect.bottom))
    dx = cx - nearest_x
    dy = cy - nearest_y
    return dx * dx + dy * dy < r * r


class Player:
    """The red square. Smooth, axis-separated movement blocked by walls."""

    def __init__(self, x, y):
        self.size = PLAYER_SIZE
        self.rect = pygame.Rect(0, 0, self.size, self.size)
        self.rect.center = (int(x), int(y))
        self.fx = float(self.rect.x)
        self.fy = float(self.rect.y)

    def set_center(self, x, y):
        self.rect.center = (int(x), int(y))
        self.fx = float(self.rect.x)
        self.fy = float(self.rect.y)

    def update(self, dt, keys, level):
        dx = dy = 0.0
        if keys[pygame.K_LEFT] or keys[pygame.K_a]:
            dx -= 1.0
        if keys[pygame.K_RIGHT] or keys[pygame.K_d]:
            dx += 1.0
        if keys[pygame.K_UP] or keys[pygame.K_w]:
            dy -= 1.0
        if keys[pygame.K_DOWN] or keys[pygame.K_s]:
            dy += 1.0
        if dx and dy:                      # normalize diagonal speed
            dx *= 0.7071067811865476
            dy *= 0.7071067811865476

        step = PLAYER_SPEED * dt

        # Move on each axis independently so the square slides along walls.
        self._move_axis(dx * step, "x", level)
        self._move_axis(dy * step, "y", level)

    def _move_axis(self, amount, axis, level):
        """Advance one axis in <=1px sub-steps, stopping flush against a wall.

        Reverting the whole step on a collision (the old behaviour) left the
        square up to a full frame's travel short of the wall, which felt sticky
        in tight gaps. Sub-stepping lets it settle right against the edge.
        """
        if amount == 0.0:
            return
        sign = 1.0 if amount > 0 else -1.0
        remaining = abs(amount)
        while remaining > 0.0:
            mag = min(1.0, remaining)
            remaining -= mag
            delta = sign * mag
            if axis == "x":
                self.fx += delta
                self.rect.x = round(self.fx)
            else:
                self.fy += delta
                self.rect.y = round(self.fy)
            if not level.rect_walkable(self.rect):
                if axis == "x":
                    self.fx -= delta
                    self.rect.x = round(self.fx)
                else:
                    self.fy -= delta
                    self.rect.y = round(self.fy)
                return

    def draw(self, surf):
        pygame.draw.rect(surf, RED_DARK, self.rect)
        pygame.draw.rect(surf, RED, self.rect.inflate(-6, -6))


class Enemy:
    """A blue circle with one of several movement behaviours.

    Kinds:
      "linear"  ping-pong along a single axis (vmover / hmover)
      "circle"  orbit a centre at constant radius (orbit / windmill spokes)
      "diag"    ping-pong along an arbitrary line between two points
      "patrol"  loop one-directionally around a closed list of waypoints
      "chase"   home in on the player at a capped speed

    All measurements are in screen pixels; the level converts tile data first.
    """

    def __init__(self, kind, radius, axis=None, fixed=0.0, pmin=0.0, pmax=0.0,
                 speed=0.0, phase=0.0, cx=0.0, cy=0.0, orbit_r=0.0,
                 p0=None, p1=None, points=None):
        self.kind = kind
        self.radius = radius
        self.speed = speed
        self.pos = pygame.Vector2(0.0, 0.0)

        if kind == "linear":
            self.axis = axis
            self.fixed = fixed
            self.pmin = pmin
            self.pmax = pmax
            span = max(0.0, pmax - pmin)
            # phase (0..1) offsets the start along the full there-and-back cycle.
            travel = (phase % 1.0) * 2.0 * span
            if travel <= span:
                self.p = pmin + travel
                self.dir = 1.0
            else:
                self.p = pmax - (travel - span)
                self.dir = -1.0
        elif kind == "circle":
            self.cx = cx
            self.cy = cy
            self.orbit_r = orbit_r
            self.angle = phase * 2.0 * math.pi
        elif kind == "diag":
            # Ping-pong parameter t in [0, 1] along the segment p0 -> p1.
            self.p0 = pygame.Vector2(p0)
            self.p1 = pygame.Vector2(p1)
            self.length = max(1.0, self.p0.distance_to(self.p1))
            cycle = (phase % 1.0) * 2.0      # 0..2 over there-and-back
            if cycle <= 1.0:
                self.t, self.dir = cycle, 1.0
            else:
                self.t, self.dir = 2.0 - cycle, -1.0
        elif kind == "patrol":
            # Closed loop of waypoints; cursor d travels the perimeter.
            self.points = [pygame.Vector2(pt) for pt in points]
            self.seglen = [self.points[i].distance_to(self.points[(i + 1) % len(self.points)])
                           for i in range(len(self.points))]
            self.perimeter = max(1.0, sum(self.seglen))
            self.d = (phase % 1.0) * self.perimeter
        else:  # "chase"
            self.home = pygame.Vector2(cx, cy)
            self.pos.update(self.home)
        self._sync()

    def update(self, dt, target=None):
        if self.kind == "linear":
            self.p += self.dir * self.speed * dt
            if self.p < self.pmin:
                self.p = self.pmin + (self.pmin - self.p)
                self.dir = 1.0
            elif self.p > self.pmax:
                self.p = self.pmax - (self.p - self.pmax)
                self.dir = -1.0
            self.p = max(self.pmin, min(self.pmax, self.p))
        elif self.kind == "circle":
            self.angle += self.speed * dt
        elif self.kind == "diag":
            self.t += self.dir * (self.speed / self.length) * dt
            if self.t < 0.0:
                self.t = -self.t
                self.dir = 1.0
            elif self.t > 1.0:
                self.t = 2.0 - self.t
                self.dir = -1.0
            self.t = max(0.0, min(1.0, self.t))
        elif self.kind == "patrol":
            self.d = (self.d + self.speed * dt) % self.perimeter
        elif self.kind == "chase" and target is not None:
            to = pygame.Vector2(target) - self.pos
            dist = to.length()
            step = self.speed * dt
            self.pos += to * (step / dist) if dist > step else to
        self._sync()

    def reset(self):
        """Return a chaser to its starting point (called on player respawn)."""
        if self.kind == "chase":
            self.pos.update(self.home)

    def _sync(self):
        if self.kind == "linear":
            if self.axis == "h":
                self.pos.update(self.p, self.fixed)
            else:
                self.pos.update(self.fixed, self.p)
        elif self.kind == "circle":
            self.pos.update(self.cx + math.cos(self.angle) * self.orbit_r,
                            self.cy + math.sin(self.angle) * self.orbit_r)
        elif self.kind == "diag":
            self.pos.update(self.p0.lerp(self.p1, self.t))
        elif self.kind == "patrol":
            d = self.d
            for i, seg in enumerate(self.seglen):
                if d <= seg or i == len(self.seglen) - 1:
                    a = self.points[i]
                    b = self.points[(i + 1) % len(self.points)]
                    self.pos.update(a.lerp(b, d / seg if seg else 0.0))
                    return
                d -= seg
        # "chase" sets self.pos directly in update().

    def hits(self, rect):
        return circle_rect_hit(self.pos.x, self.pos.y, self.radius, rect)

    def draw(self, surf):
        if self.kind == "chase":
            fill, edge = CHASER, CHASER_DARK
        else:
            fill, edge = BLUE, BLUE_DARK
        pygame.draw.circle(surf, edge, self.pos, self.radius)
        pygame.draw.circle(surf, fill, self.pos, max(1, self.radius - 3))


class Coin:
    """A yellow coin the player must collect before the goal opens."""

    def __init__(self, x, y):
        self.pos = pygame.Vector2(x, y)
        self.radius = COIN_RADIUS
        self.collected = False

    def hits(self, rect):
        return circle_rect_hit(self.pos.x, self.pos.y, self.radius, rect)

    def draw(self, surf):
        if self.collected:
            return
        pygame.draw.circle(surf, YELLOW_DARK, self.pos, self.radius)
        pygame.draw.circle(surf, YELLOW, self.pos, max(1, self.radius - 2))
