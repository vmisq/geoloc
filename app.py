# Libraries
import dash_leaflet as dl
from dash import Dash, html, Input, Output, State, dcc, no_update, dash_table, ctx
from dash.exceptions import PreventUpdate
import dash_bootstrap_components as dbc
from flask import request
import pandas as pd
from datetime import datetime
import httplib2
from bson.objectid import ObjectId
import os
import math
import json

# definitions
api_url = 'https://vmisq.xyz/datagateway/geoloc/'
user = os.environ['user']
passwd = os.environ['pass']
h = httplib2.Http()
h.add_credentials(user, passwd)
get = lambda x: json.loads(h.request(x, "GET", body="")[1].decode('utf-8'))

url = 'https://tiles.basemaps.cartocdn.com/rastertiles/voyager_nolabels/{z}/{x}/{y}{r}.png'
attribution = '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors &copy; <a href="https://carto.com/attributions">CARTO</a>'
subdomains = 'abcd'
maxZoom = 20

external_stylesheets = [dbc.themes.BOOTSTRAP]


# main data
try:
    cidades = get(api_url + 'get_random_location')['values']
    df = pd.DataFrame(cidades)
    df = df[['cidade', 'pais', 'lat', 'lon']]
except Exception as e:
    print(e)
    df = pd.read_csv('assets/cidades.csv')
    df = df[['cidade', 'pais', 'lat', 'lon']]


#functions
def deg2rad(deg):
    return deg * (math.pi/180)

def getDistanceFromLatLonInKm(lat1, lon1, lat2, lon2):
    R = 6371
    dLat = deg2rad(lat2-lat1)
    dLon = deg2rad(lon2-lon1)
    a = math.sin(dLat/2) * math.sin(dLat/2) + math.cos(deg2rad(lat1)) * \
        math.cos(deg2rad(lat2)) * math.sin(dLon/2) * math.sin(dLon/2)

    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
    d = R * c
    return round(d, 0)

def get_next_location(n_clicks, round_n, lat, lon, hist, score, city, country, cur_lat, cur_lon):
    if city == '-' and country == '-':
        dff = df.copy()
        city, country, cur_lat, cur_lon = dff.sample(n=1).iloc[0]
        try:
            get(api_url + f'insert_player/{request.remote_addr}/{datetime.now()}/inicio/0')
        except Exception as e:
            print(e)
        return city, country, cur_lat, cur_lon, no_update, no_update, no_update, no_update, no_update, no_update, 'Verificar Seleção!'
    else:
        round_n += 1
        dff = df.copy()
        city, country, cur_lat, cur_lon = dff.sample(n=1).iloc[0]
        return city, country, cur_lat, cur_lon, round_n, f"Rodada {round_n:} de 10", no_update, no_update, no_update, [], 'Verificar Seleção!'

def verify_location(n_clicks, round_n, lat, lon, hist, score, city, country, cur_lat, cur_lon):
    if lat != '-' and lon != '-' and city != '-' and country != '-' and cur_lat != '-' and cur_lon != '-':
        new_hist = []
        new_hist.append(html.P(f'{round_n}) {city} - {country}', style={'margin-left': '10px'}))
        new_hist.append(html.P(f'Real: ({cur_lat}, {cur_lon})', style={'margin-left': '10px'}))
        new_hist.append(html.P(f'Você: ({lat}, {lon})', style={'margin-left': '10px'}))
        dif1 = (float(lat) - cur_lat)**2
        dif2 = (float(lon) - cur_lon)**2
        radius = (dif1 + dif2)**0.5
        if radius < 0.1:
            new_score = 100
        else:
            new_score = 100 / (1 + radius/10)
        new_hist.append(html.P(f'Distância: {getDistanceFromLatLonInKm(float(lat), float(lon), cur_lat, cur_lon)} km', style={'margin-left': '10px'}))
        new_hist.append(html.P(f'Pontuação: {int(new_score)}', style={'margin-left': '10px'}))
        new_hist.append(html.Br())
        hist = new_hist + hist
        score = int(score) + int(new_score)
        cur_lat_lng = [cur_lat, cur_lon]
        loc =[
            dl.Marker(
                position=cur_lat_lng,
                children=dl.Tooltip("({:.3f}, {:.3f})".format(*cur_lat_lng))
            ),
            dl.PolylineDecorator(
                children=dl.Polyline(positions=[[float(lat), float(lon)], [cur_lat, cur_lon]]),
                patterns=[dict(offset='100%', repeat='0', arrowHead=dict(pixelSize=15, polygon=False, pathOptions=dict(stroke=True)))]
            )
        ]
        if round_n == 10:
            next_btn = 'Ver Scores!'
        else:
            next_btn = 'Próxima!'
        return no_update, no_update, no_update, no_update, no_update, no_update, hist, score, no_update, loc, next_btn
    else:
        raise PreventUpdate    

def go_to_scoreboard(n_clicks, round_n, lat, lon, hist, score, city, country, cur_lat, cur_lon):
    try:
        get(api_url + f'insert_player/{request.remote_addr}/{datetime.now()}/fim/{score}')
        x_id = get(api_url + f'insert_score/NONE/{score}/{datetime.now()}')['values']
        scores = get(api_url + 'get_scores')['values']
        scoreboard = pd.DataFrame(eval(scores))
        scoreboard.loc[scoreboard['_id']==ObjectId(x_id), 'user_name'] = 'Você!'
        scoreboard['Ranking'] = scoreboard.index + 1
        scoreboard = scoreboard[['Ranking', 'user_name', 'score']]
        scoreboard.columns = ['Ranking', 'Nome', 'Pontuação']
        scoreboard_table = html.Div(
            [
                dash_table.DataTable(
                    scoreboard.to_dict('records'),
                    [{"name": i, "id": i} for i in scoreboard.columns],
                    style_cell={'textAlign': 'center'},
                    style_as_list_view=True,
                ),
                dcc.Store(id='mongo-id', data=str(x_id))
            ], style={'margin-left': '200px', 'margin-right': '200px'}
        )
    except Exception as e:
        print(e)
        scoreboard_table = html.P('Desculpe-me, sem conexão para mostrar o Scoreboard', style={'text-align': 'center'})
    app = html.Div([
        html.H1('Obrigado por jogar!', style={'text-align': 'center'}),
        html.H3('Sua pontuação final foi:', style={'text-align': 'center'}),
        html.H1(f'{score}', style={'text-align': 'center'}),
        html.Br(),
        scoreboard_table,
        html.Br(),
        dcc.Input(id="input2", placeholder="Grave seu nome no Scoreboard!",
            type="text", debounce=True, minLength=1, maxLength=20,
            style={'margin': "auto", "display": "block", 'width': '50%'}),
        html.Br(),
        html.A(
            dbc.Button('Jogar Novamente!', id='play-again'),
            href='/',
            style={'width': '20%', 'height': '10hv', 'margin': "auto", "display": "block"}
        ),
    ])
    return no_update, no_update, no_update, no_update, no_update, no_update, no_update, no_update, app, no_update, no_update


# app
app = Dash(__name__, external_stylesheets=external_stylesheets)
app.config.suppress_callback_exceptions=True
app.title = 'GeoLoc'

server = app.server

app.layout = html.Div(id='app', children=[
    dbc.Row([
        dbc.Col(
            html.Div([
                html.Div(
                    [
                        html.Div(
                            html.Img(
                                src=app.get_asset_url('geoloc.png'),
                                style={'width':'60%', 'margin': 'auto'}
                            ),
                            style={'text-align': 'center'}
                        ),
                        html.H1('GeoLoc', style={'text-align': 'center'}), 
                    ],
                    style={'height': '20hv'}
                ),
                html.P(id='round-n', children='Rodada 1 de 10', style={'text-align': 'center'}),
                html.P('Cidade', style={'margin-left': '10px'}),
                html.P(id='city', children='-', style={'text-align': 'center'}),
                html.P('País', style={'margin-left': '10px'}),
                html.P(id='country', children='-', style={'text-align': 'center'}),
                html.P('Sua Latitude', style={'margin-left': '10px'}),
                html.P(id='lat', children='-', style={'text-align': 'center'}),
                html.P('Sua Longitude', style={'margin-left': '10px'}),
                html.P(id='lon', children='-', style={'text-align': 'center'}),
                dbc.Button("Começar!", id="action-button", style={'width': '80%', 'margin': 'auto', "display": "block"}),
                dcc.Store(id='round_n', data=1),
                dcc.Store(id='cur_lat', data='-'),
                dcc.Store(id='cur_lon', data='-'),
            ]),
            width=2
        ),
        dbc.Col(
            html.Div([
                dl.Map(
                    [
                        dl.TileLayer(url=url, attribution=attribution, subdomains=subdomains, maxZoom=maxZoom),
                        dl.LayerGroup(id="layer"),
                        dl.LayerGroup(id="layer2"),
                    ],
                    id="map",
                    style={'width': '100%', 'height': '100vh', 'margin': "auto", "display": "block"}
                ),
            ]),
            width=8
        ),
        dbc.Col(
            html.Div([
                html.H3('Pontuação', style={'text-align': 'center', 'height': '5vh'}),
                html.H1(id='score', children='0', style={'text-align': 'center', 'height': '10vh'}),
                html.H3('Histórico', style={'text-align': 'center', 'height': '5vh'}),
                html.Div(id='hist', children=[], style={"overflow-y": "auto", 'height': '75vh'}),
            ]),
            width=2
        ),
    ], className="g-0")
])


# Callbacks
@app.callback(
    Output("layer", "children"),
    Output("lat", "children"),
    Output("lon", "children"),
    Input("map", "click_lat_lng"),
    prevent_initial_call=True
)
def map_click(click_lat_lng):
    return [
        dl.Marker(
            position=click_lat_lng,
            children=dl.Tooltip("({:.3f}, {:.3f})".format(*click_lat_lng))
        )], "{:.4f}".format(click_lat_lng[0]), "{:.4f}".format(click_lat_lng[1])

@app.callback(
    Output("city", "children"),
    Output("country", "children"),
    Output("cur_lat", "data"),
    Output("cur_lon", "data"),
    Output("round_n", "data"),
    Output("round-n", "children"),
    Output("hist", "children"),
    Output("score", "children"),
    Output("app", "children"),
    Output("layer2", "children"),
    Output("action-button", "children"),
    Input("action-button", "n_clicks"),
    State("round_n", "data"),
    State("lat", "children"),
    State("lon", "children"),
    State("hist", "children"),
    State("score", "children"),
    State("city", "children"),
    State("country", "children"),
    State("cur_lat", "data"),
    State("cur_lon", "data"),
    State("action-button", "children"),
)
def start_game(n_clicks, round_n, lat, lon, hist, score, city, country, cur_lat, cur_lon, btn):
    if btn == 'Verificar Seleção!':
        x = verify_location(n_clicks, round_n, lat, lon, hist, score, city, country, cur_lat, cur_lon)
        return x
    elif btn == 'Ver Scores!':
        x = go_to_scoreboard(n_clicks, round_n, lat, lon, hist, score, city, country, cur_lat, cur_lon)
        return x
    else:
        x = get_next_location(n_clicks, round_n, lat, lon, hist, score, city, country, cur_lat, cur_lon)
        return x

@app.callback(
    Output("input2", "style"),
    Input("input2", "value"),
    State("mongo-id", "data"),
    prevent_initial_call=True
)
def update_output(input2, mongo_id):
    try:
        get(api_url + f'update_user_name/{mongo_id}/{input2}')
    except Exception as e:
        print(e)
    return no_update


if __name__ == '__main__':
    app.run_server(debug=True)
