import json
import os
import re
import time
from os.path import join
from pathlib import Path
from typing import List, Tuple, Optional

import dash
import plotly.graph_objects as go
from cryptography.fernet import Fernet as F
from dash import dcc, html
from dash.dependencies import Input, Output, State
from dash_extensions.enrich import MultiplexerTransform, TriggerTransform, DashProxy

from algorithmics.assets.generate_scatter import generate_path_scatters, generate_graph_scatter, \
    generate_all_scenario_scatters, \
    generate_graph_layout
from algorithmics.enemy.asteroids_zone import AsteroidsZone
from algorithmics.enemy.black_hole import BlackHole
from algorithmics.enemy.enemy import Enemy
from algorithmics.navigator import calculate_path
from algorithmics.utils.coordinate import Coordinate

KEY = b'nNjpIl9Ax2LRtm-p6ryCRZ8lRsL0DtuY0f9JeAe2wG0='


def _extract_scenario_number_from_path(path: str) -> int:
    """Extract the number of a scenario given its name in the file system

    For example, the file
        ../resources/scenarios/scenario_5.json

    Will be converted into the integer 5.

    :param path: path to scenario's JSON in the file system
    :return: scenario's number
    """
    return int(re.match(r'.*scenario_(\d+)\.json', path).group(1))


scenario_groups = os.listdir(Path('../resources/scenarios'))

scenario_paths = {group: sorted(os.listdir(join(Path('../resources/scenarios'), group)),
                                key=lambda path: _extract_scenario_number_from_path(path))
                  for group in scenario_groups}

for group, files in scenario_paths.items():
    scenario_paths[group] = [join(Path('../resources/scenarios'), group, f) for f in files]

scenario_groups = sorted(scenario_groups,
                         key=lambda group: _extract_scenario_number_from_path(scenario_paths[group][0]))

with open('../resources/scenario_names.json', 'r') as f:
    scenario_names = json.load(f)
    scenario_names = {int(number): name for number, name in scenario_names.items()}


def _generate_scenario_label(path: str) -> str:
    scenario_number = _extract_scenario_number_from_path(path)
    return f'Scenario #{scenario_number} - {scenario_names[scenario_number]}'


colors = {
    'background': '#111111',
    'h1': '#7FDBFF',
    'text': '#0099FF'
}

app = DashProxy(__name__, transforms=[TriggerTransform(), MultiplexerTransform()],
                external_stylesheets=[r'./assets/bWLwgP.css'])

app.layout = html.Div([
    html.H1('Lost in deep space: Run your algorithm', style={'text-align': 'center', 'font-family': 'Courier New',
                                                             'font-weight': 'bold', 'font-size': '30px',
                                                             'color': colors['h1']}),
    html.Div(children=[
        dcc.Dropdown(id='scenario-group-dropdown',
                     options=[{'label': group, 'value': group} for group in scenario_groups],
                     value=scenario_groups[0],
                     clearable=False,
                     style={'font-family': 'Courier New', 'font-weight': 'bold', 'color': colors['text'],
                            'margin-bottom': '10px', 'margin-right': '10px', 'font-size': '16px',
                            'width': '100%'}),
        dcc.Dropdown(id='scenario-dropdown',
                     options=[{'label': _generate_scenario_label(filename),
                               'value': filename}
                              for filename in list(scenario_paths.values())[0]],
                     value=list(scenario_paths.values())[0][0],
                     clearable=False,
                     style={'font-family': 'Courier New', 'font-weight': 'bold', 'color': colors['text'],
                            'margin-bottom': '10px', 'margin-right': '10px', 'font-size': '16px',
                            'width': '100%'}),
        html.Button('Run Algorithm!', id='run-button',
                    style={'color': colors['h1'], 'background-color': 'black'},
                    )
    ], style={'display': 'flex'}, className='1 row'),
    dcc.Graph(
        id='graph',
        config={'scrollZoom': True},
        style={'height': '60vh', 'margin-bottom': '10px'}
    ),
    html.Div(
        children=[
            dcc.Checklist(id='graph-toggle',
                          options=[{'label': 'Show Graph', 'value': 'Toggle'}],
                          value=[],
                          style={'font-family': 'Courier New', 'font-weight': 'bold', 'margin-top': '5px',
                                 'margin-bottom': '5px', 'color': '#ffffff', 'display': 'inline-block'}),
        ],
        style={'display': 'flex'}
    ),
    html.Div('Calculated path:',
             style={'font-family': 'Courier New', 'font-weight': 'bold', 'margin-top': '5px',
                    'margin-bottom': '5px', 'color': '#ffffff'}),
    html.Div(
        children=[dcc.Textarea(id='calculated-path',
                               readOnly=True,
                               style={'font-family': 'Courier New', 'font-weight': 'bold', 'background-color': 'black',
                                      'color': 'white', 'width': '100%', 'height': '65px', 'display': 'inline-block'}),

                  html.Button('Download', id='download-path-btn',
                              style={'color': colors['h1'], 'background-color': 'black', 'display': 'inline-block',
                                     'height': '65px'})
                  ],
        style={'display': 'flex'}
    ),
    dcc.Store(id='path-store', data=[]),
    dcc.Store(id='edges-store', data=[]),
    dcc.Store(id='calculation-time-store', data=0),
    dcc.Download(id='download')
], style={'margin-top': '20px', 'margin-left': '10px', 'margin-right': '10px'})


@app.callback(Output('calculated-path', 'value'),
              Input('path-store', 'data'),
              prevent_initial_call=True)
def update_path_text(path: List[Tuple[float, float]]) -> str:
    if not path:
        return 'No path returned, error occured in calculation'
    coordinates = [f'({coordinate[0]}, {coordinate[1]})' for coordinate in path]
    return ', '.join(coordinates)


def _parse_coordinate(values: List[float]) -> Coordinate:
    return Coordinate(values[0], values[1])


def _load_scenario(scenario_path: str) -> tuple[Coordinate, list[Coordinate], list[Enemy]]:
    with open(scenario_path, 'r') as f:
        raw_scenario = json.load(f)

    # Parse scenario JSON
    source = _parse_coordinate(raw_scenario['source'])
    targets = [_parse_coordinate(target) for target in raw_scenario['targets']]
    enemies: List[Enemy] = []
    enemies += [BlackHole(_parse_coordinate(hole['center']), hole['radius'])
                for hole in raw_scenario['black_holes']]
    enemies += [AsteroidsZone([_parse_coordinate(c) for c in raw_zone['boundary']])
                for raw_zone in raw_scenario['asteroids_zones']]

    return source, targets, enemies


@app.callback(Output('scenario-dropdown', 'options'),
              Output('scenario-dropdown', 'value'),
              Input('scenario-group-dropdown', 'value'),
              prevent_initial_call=True)
def update_scenario_list(scenario_group) -> Tuple[List, str]:
    options = [{'label': _generate_scenario_label(filename),
                'value': filename} for filename in scenario_paths[scenario_group]]
    return options, options[0]['value']


@app.callback(Output('calculated-path', 'value'),
              Input('scenario-dropdown', 'value'))
def reset_path_panel(scenario: str) -> Optional[str]:
    return ''


@app.callback(Output('graph', 'figure'),
              Input('scenario-dropdown', 'value'),
              Input('path-store', 'data'),
              Input('edges-store', 'data'),
              Input('graph-toggle', 'value'))
def update_map(scenario_path: str, path: List[Tuple[float, float]],
               edges: List[Tuple[float, float, float, float]], graph_on: str) -> go.Figure:
    source, targets, enemies = _load_scenario(scenario_path)

    # If only scenario was changed, path and graph are empty
    if dash.callback_context.triggered[0]['prop_id'].split('.')[0] == 'scenario-dropdown':
        draw_path, edges_scatter = [], []

    # Otherwise, parse path and graph
    else:
        draw_path = [Coordinate(c[0], c[1]) for c in path]
        edges_scatter = [generate_graph_scatter(edges)] if len(graph_on) > 0 else []

    data = generate_all_scenario_scatters(source, targets, enemies) + \
           generate_path_scatters(draw_path, color='#cccccc') + edges_scatter
    return go.Figure(data=data, layout=generate_graph_layout())


@app.callback(Output('path-store', 'data'),
              Output('edges-store', 'data'),
              Output('calculation-time-store', 'data'),
              Input('run-button', 'n_clicks'),
              State('scenario-dropdown', 'value'),
              prevent_initial_call=True)
def run_button_n_clicks_changed(n_clicks: int, scenario_path: str) -> \
        Tuple[List[Tuple[float, float]], List[Tuple[float, ...]], float]:
    source, targets, enemies = _load_scenario(scenario_path)

    # Dash doesn't support custom return types from callbacks, so we convert the path into a list of tuples
    start_time = time.time()
    path, graph = calculate_path(source, targets[0], enemies)
    calculation_time = time.time() - start_time
    return [(c.x, c.y) for c in path], [(edge[0].x, edge[0].y, edge[1].x, edge[1].y) for edge in
                                        graph.edges], calculation_time


@app.callback(
    Output('download', 'data'),
    Input('download-path-btn', 'n_clicks'),
    State('path-store', 'data'),
    State('calculation-time-store', 'data'),
    State('scenario-dropdown', 'value'),
    prevent_initial_call=True
)
def download_path(n_clicks: int, path: List[Tuple[float, float]], calculation_time: float, scenario_path: str):
    return dict(content=generate_path_file(path, calculation_time),
                filename=f'scenario{_extract_scenario_number_from_path(scenario_path)}.txt')


def generate_path_file(path: List[Tuple[float, float]], calculation_time: float) -> str:
    # file can only be encrypted when in bytes format
    to_encript: bytes = json.dumps({'path': path, 'calculation_time': calculation_time}).encode()
    # encrypt and convert to str
    return str(F(KEY).encrypt(to_encript), 'utf-8')


if __name__ == '__main__':
    app.run_server(host='127.0.0.1', port=7324, dev_tools_silence_routes_logging=True)
