import dash_leaflet as dl
from dash import Dash, html, Input, Output, State, dcc, no_update, dash_table
from dash.exceptions import PreventUpdate
import dash_bootstrap_components as dbc
from flask import request
import pandas as pd
from datetime import datetime
import requests
from requests.auth import HTTPBasicAuth
from bson.objectid import ObjectId
import os

df = pd.read_csv('cidades.csv')
api_url = 'http://vmisq.xyz/datagateway/geoloc/'
user = os.environ['user']
passwd = os.environ['pass']
image_url = 'https://cdn-icons.flaticon.com/png/512/3218/premium/3218347.png?token=exp=1655159813~hmac=2cc2960a5d97587d0b32e5b5824badcf'
url = 'https://tiles.basemaps.cartocdn.com/rastertiles/voyager_nolabels/{z}/{x}/{y}{r}.png'
attribution = '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors &copy; <a href="https://carto.com/attributions">CARTO</a>'
subdomains = 'abcd'
maxZoom = 20
external_stylesheets = [dbc.themes.BOOTSTRAP]

app = Dash(__name__, external_stylesheets=external_stylesheets)
app.config.suppress_callback_exceptions=True
app.title = 'GeoLoc'
app.layout = html.Div(id='app', children=[
    dbc.Row([
        dbc.Col(
            html.Div([
                html.Div(
                    [
                        html.Div(html.Img(src=image_url, style={'width':'60%', 'margin': 'auto'}), style={'text-align': 'center'}),
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
                dbc.Button("Verificar Selecção!", id="action-button", style={'width': '80%', 'margin': 'auto', "display": "block"}),
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
                        dl.LayerGroup(id="layer")
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
)
def start_game(n_clicks, round_n, lat, lon, hist, score, city, country, cur_lat, cur_lon):
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
        new_hist.append(html.P(f'Pontuação: {int(new_score)}', style={'margin-left': '10px'}))
        new_hist.append(html.Br())
        hist = new_hist + hist
        score = int(score) + int(new_score)        
        if round_n == 10:
            try:
                requests.get(api_url + f'insert_player/{request.remote_addr}/{datetime.now()}/fim/{score}', auth = HTTPBasicAuth(user, passwd))
                x_id = requests.get(api_url + f'insert_score/NONE/{score}/{datetime.now()}', auth = HTTPBasicAuth(user, passwd)).json()['values']
                scores = requests.get(api_url + 'get_scores', auth = HTTPBasicAuth(user, passwd)).json()['values']
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
            return no_update, no_update, no_update, no_update, no_update, no_update, hist, score, app
        else:
            round_n += 1
            try:
                city, country, cur_lat, cur_lon = requests.get(api_url + 'get_random_location', auth = HTTPBasicAuth(user, passwd)).json()['values']
            except Exception as e:
                print(e)
                dff = df.copy()
                city, country, cur_lat, cur_lon = dff.sample(n=1).iloc[0]
            return city, country, cur_lat, cur_lon, round_n, f"Rodada {round_n:} de 10", hist, score, no_update
    elif city == '-' and country == '-':
        try:
            city, country, cur_lat, cur_lon = requests.get(api_url + 'get_random_location', auth = HTTPBasicAuth(user, passwd)).json()['values']
        except Exception as e:
            print(e)
            dff = df.copy()
            city, country, cur_lat, cur_lon = dff.sample(n=1).iloc[0]
        try:
            requests.get(api_url + f'insert_player/{request.remote_addr}/{datetime.now()}/inicio/0', auth = HTTPBasicAuth(user, passwd))
        except Exception as e:
            print(e)
        return city, country, cur_lat, cur_lon, no_update, no_update, no_update, no_update, no_update
    else:
        raise PreventUpdate

@app.callback(
    Output("input2", "style"),
    Input("input2", "value"),
    State("mongo-id", "data"),
    prevent_initial_call=True
)
def update_output(input2, mongo_id):
    try:
        requests.get(api_url + f'update_user_name/{mongo_id}/{input2}', auth = HTTPBasicAuth(user, passwd))
    except Exception as e:
        print(e)
    return no_update


if __name__ == '__main__':
    app.run_server(debug=True)
