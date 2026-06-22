import math
from typing import List, Tuple, Optional

from algorithmics.enemy.asteroids_zone import AsteroidsZone
from algorithmics.enemy.black_hole import BlackHole
from algorithmics.enemy.enemy import Enemy
from algorithmics.enemy.radar import Radar

try:
    import plotly.graph_objects as go
except:
    import plotly.graph_objs as go

from algorithmics.utils.coordinate import Coordinate


def generate_coordinate_scatter(coordinate: Coordinate, color: str = '#ff5500', hovertext=None, symbol: str = 'circle') \
        -> go.Scatter:
    """Converts the give coordinate into a displayable plotly scatter

    :param coordinate: coordinate to display
    :param color: color of the coordinate
    :param hovertext: text to appear on mouse hover
    :return: plotly scatter graphics object containing the circle
    """
    return go.Scatter(x=[coordinate.x], y=[coordinate.y], mode='markers+text',
                      hoverinfo='skip' if hovertext is None else 'name', name=hovertext,
                      textposition='top center',
                      marker=go.scatter.Marker(color=color, size=13, symbol=symbol))


def generate_circle_scatter(center: Coordinate, radius: float, vertices_amount: int = 60,
                            color: str = '#ff5500', hover_text=None) -> go.Scatter:
    """Converts the given circle into a displayable plotly scatter

    :param center: circle's center
    :param radius: circle's radius
    :param vertices_amount: how many vertices the calculated circle will have (discretization factor)
    :return: plotly scatter graphics object containing the circle
    """
    xs = []
    ys = []
    for i in list(range(vertices_amount)) + [0]:  # Iterate again over 0 to close the circle
        angle = (360.0 / vertices_amount) * i
        delta_x = math.sin(math.radians(angle)) * radius
        delta_y = math.cos(math.radians(angle)) * radius

        xs.append(center.x + delta_x)
        ys.append(center.y + delta_y)

    return go.Scatter(x=xs, y=ys,
                      hoveron='fills',
                      hoverinfo='skip' if hover_text is None else 'text',
                      text=hover_text,
                      fill='toself',
                      fillcolor=f'rgba{(*_hex_to_rgb(color), 0.3)}',
                      line=go.scatter.Line(color=color, width=3))


def generate_path_scatters(path: List[Coordinate], color: str = '#47d147',
                           detected_segments: Optional[List[Tuple[Coordinate, Coordinate]]] = None) -> List[go.Scatter]:
    """Converts a path into a displayable plotly scatter

    :param path: path to be converted
    :param color: scatter's color
    :param detected_segments: path parts to be colored red
    :return: plotly scatter graphics object displaying the path
    """
    xs = [coordinate.x for coordinate in path]
    ys = [coordinate.y for coordinate in path]

    scatters = [go.Scatter(x=xs, y=ys, hoverinfo='skip', mode='lines+markers',
                           line=go.scatter.Line(color=color, width=3))]

    if detected_segments is None:
        return scatters

    for segment in detected_segments:
        start, end = segment
        scatters.append(go.Scatter(x=[start.x, end.x], y=[start.y, end.y], hoverinfo='skip', mode='lines',
                                   line=go.scatter.Line(color='#e61010', width=3)))

    return scatters

def generate_graph_scatter(edges: List[Tuple[float, float, float, float]], color: str = '#0099FF') -> go.Scatter:
    """Converts a path into a displayable plotly scatter

    :param edges: list of edges
    :param color: scatter's color
    :return: plotly scatter graphics object displaying the path
    """
    xs = [x for pairs in [[edge[0], edge[2], None] for edge in edges] for x in pairs]
    ys = [y for pairs in [[edge[1], edge[3], None] for edge in edges] for y in pairs]

    return go.Scatter(x=xs, y=ys, hoverinfo='skip', mode='lines+markers',
                      line=go.scatter.Line(color=color, width=3))


def generate_polygon_scatter(boundary: List[Coordinate], color: str = '#00ff00', hover_text=None) -> go.Scatter:
    """Converts the given polygon into a displayable plotly scatter

    :param boundary: polygon's boundary
    :param color: scatter's color
    :return: plotly scatter graphics object displaying the path
    """
    xs = [coordinate.x for coordinate in boundary] + [boundary[0].x]
    ys = [coordinate.y for coordinate in boundary] + [boundary[0].y]

    return go.Scatter(x=xs, y=ys,
                      hoverinfo='skip' if hover_text is None else 'text',
                      text=hover_text, fill='toself', mode='lines',
                      fillcolor=f'rgba{(*_hex_to_rgb(color), 0.3)}',
                      line=go.scatter.Line(color=color, width=3))


def generate_all_scenario_scatters(source: Coordinate, targets: List[Coordinate], enemies: List[Enemy]) -> \
        List[go.Scatter]:
    """Generate all scatter objects needed for a given scenario"""

    holes = [generate_circle_scatter(post.center, post.radius, color='#ffa31a', hover_text=f'Black Hole {i + 1}')
             for i, post in enumerate(e for e in enemies if isinstance(e, BlackHole))]
    zones = [generate_polygon_scatter(zone.boundary, color='#4dc3ff', hover_text=f'Asteroids Zone {i + 1}')
             for i, zone in enumerate(e for e in enemies if isinstance(e, AsteroidsZone)
                                      and not isinstance(e, BlackHole))]
    radars = [generate_circle_scatter(radar.center, radar.radius, color='#ff0080', hover_text=f'Radar {i + 1}')
              for i, radar in enumerate(e for e in enemies if isinstance(e, Radar))]
    source = [generate_coordinate_scatter(source, color='#bfff80', hovertext='source', symbol='triangle-ne')]
    targets = [generate_coordinate_scatter(target, color='#ff704d', hovertext='target', symbol='diamond')
               for target in targets]

    return holes + zones + radars + source + targets


def generate_graph_layout() -> go.Layout:
    """Generate layout for the graph

    :return: graph layout
    """
    return go.Layout(dragmode='pan',
                     yaxis={'scaleanchor': 'x'},
                     showlegend=False,
                     template='plotly_dark',
                     margin=go.layout.Margin(l=0, r=0, b=0, t=0))


def _hex_to_rgb(hex_color: str) -> Tuple[int, int, int]:
    """Converts a color in hex-string representation to a tuple of (R,G,B) values in decimals

    :param hex_color: color hex value as a string in the form of `#RRGGBB` or `#RGB`
    :return: decimal representation of the color as a tuple
    """
    hex_color = hex_color.lstrip("#")
    if len(hex_color) == 3:
        hex_color = hex_color * 2
    return int(hex_color[0:2], 16), int(hex_color[2:4], 16), int(hex_color[4:6], 16)
