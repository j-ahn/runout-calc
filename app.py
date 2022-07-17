# -*- coding: utf-8 -*-
"""
Run-out calculator

Author : Jiwoo Ahn

16/07/2022

"""
import math
import numpy as np

import dash
import dash_core_components as dcc
import dash_html_components as html
from dash.dependencies import Input, Output , State

from shapely.ops import split, linemerge
from shapely.geometry import LineString, Polygon, Point

import plotly.graph_objects as go
import plotly.io as pio
pio.renderers.default='browser'

# Initiate the app
external_stylesheets = ["https://codepen.io/chriddyp/pen/bWLwgP.css"]
app = dash.Dash(__name__, external_stylesheets=external_stylesheets)
server = app.server
app.title = 'Runout Calculator'

colors = {
    'background': '#000000',
    'text': '#5d76a9',
    'label': '#f5b112'
}

def minimum_distance(x0, y0, xl, yl):
    dis = [((x0-x)**2+(y0-y)**2)**0.5 for x, y in zip(xl, yl)]
    return dis.index(min(dis))
    
def round_list(list0):
    list0_ = list0.split(',')
    return [round(float(x),1) for x in list0_]

def merge(list1, list2):
    merged_list = tuple(zip(list1, list2)) 
    return merged_list

def polygon_to_patch(polygon):
    x, y = polygon.exterior.xy
    xn, yn = np.array(x), np.array(y)
    return xn, yn

def plot_runout(standoff, swell_factor, bund_height, runout_angle, spx, spy, fsx, fsy, direction, project):
    sp_x = round_list(spx)
    sp_y = round_list(spy)
    fs_x = round_list(fsx)
    fs_y = round_list(fsy)
    
    fig = go.Figure()
    fig.update_layout(template='simple_white')
    
    # Calculated Parameters
    bund_width = 2*bund_height/math.tan(math.radians(37))
    # bund co-ordinates
    
    if direction == 'left':
        b_x = [-standoff+sp_x[0]]
    else:
        b_x = [standoff+sp_x[0]]
        
    b_y = [sp_y[0]]
    # Start of run-out
    if bund_height > 0:
        if direction == 'left':
            b_x.extend([b_x[0]+0.5*bund_width,
                   b_x[0]+1.0*bund_width])
        else:
            b_x.extend([b_x[0]-0.5*bund_width,
                   b_x[0]-1.0*bund_width])
            
        b_y.extend([b_y[0]+bund_height, b_y[0]])
        bt_x, bt_y = b_x[1], b_y[1]

    else:
        bt_x, bt_y = b_x[0], b_y[0]
        
    # Runout line
    runout_length = 1000
    
    if direction == 'right':
        runout_angle = 180-runout_angle
    
    ro_x = [bt_x, bt_x+runout_length*math.cos(math.radians(runout_angle))]
    ro_y = [bt_y, bt_y+runout_length*math.sin(math.radians(runout_angle))]
    
    # Slope profile
    fig.add_trace(go.Scatter(x=sp_x, y=sp_y, name = 'Slope', mode='lines', line=dict(color='black'), opacity=1.0, marker_size=0))
    
    # Failure surface
    fig.add_trace(go.Scatter(x=fs_x, y=fs_y, name = 'Failure', mode='lines', line=dict(color='red'), opacity=1.0, marker_size=0))
    
    if bund_height > 0:
        fig.add_trace(go.Scatter(x=b_x, y=b_y, name = "Bund = {0:.1f} m".format(bund_height), mode='lines', line=dict(color='orange'), opacity=0.2, marker_size=0, fillcolor='orange', fill='toself', hoverinfo='skip'))
    
    line_combined = LineString(merge(sp_x, sp_y))
    
    try:
        # FAILURE VOLUME
        i_start = minimum_distance(fs_x[0], fs_y[0], sp_x, sp_y)
        ix1, iy1 = sp_x[i_start], sp_y[i_start]
        fs_x[0], fs_y[0] = ix1, iy1
        i1 = Point(ix1, iy1)
        
        i_end = minimum_distance(fs_x[-1], fs_y[-1], sp_x, sp_y)
        ix2, iy2 = sp_x[i_end], sp_y[i_end]
        fs_x[-1], fs_y[-1] = ix2, iy2
        i2 = Point(ix2, iy2)
        
        fs_ls = LineString(merge(fs_x, fs_y))
        
        # failure volume
        sp_ls = LineString(merge(sp_x, sp_y))
        sp_ls1, sp_ls2 = split(sp_ls, i1)
       
        try:
            sp_ls3, sp_ls4 = split(sp_ls2, i2)
            if project == "yes":
                line_combined = LineString(linemerge([sp_ls1, fs_ls, sp_ls4]))
        except:
            sp_ls3 = sp_ls2
            if project == "yes":
                line_combined = LineString(linemerge([sp_ls1, fs_ls]))
        
        failure_volume = Polygon(linemerge([fs_ls, sp_ls3]))
        fv_x_p, fv_y_p = polygon_to_patch(failure_volume)
        fig.add_trace(go.Scatter(x=fv_x_p, y=fv_y_p, name = "Failure volume = {0:.1f} m³/m".format(failure_volume.area*swell_factor), mode='lines', line=dict(color='red'), opacity=0.2, marker_size=0, fillcolor='red', fill='toself', hoverinfo='skip'))
    
    except:
        print('Intersection error')

    try:
        # CATCH CAPACITY
        line_runout = LineString(merge(ro_x, ro_y))
        intersect = line_runout.intersection(line_combined)
        try:
            intersect = intersect[0]
        except:
            intersect = intersect    
        ix, iy = intersect.x, intersect.y
        
        # Calculate catch capacity
        line_profile = split(line_combined,line_runout)[0]
        if bund_height > 0:
            line_profile2 = LineString([(0,0), (b_x[2], b_y[2]), (bt_x, bt_y), (ix, iy)])
        else:
            line_profile2 = LineString([(0,0), (bt_x, bt_y), (ix, iy)])
        catch_capacity = Polygon(linemerge([line_profile, line_profile2]))
        cc_x, cc_y = polygon_to_patch(catch_capacity)
        fig.add_trace(go.Scatter(x=cc_x, y=cc_y, name = "Catch capacity = {0:.1f} m³/m".format(catch_capacity.area), mode='lines', line=dict(color='blue'), opacity=0.2, marker_size=0, fillcolor='blue', fill='toself', hoverinfo='skip'))
    except:
        print('Catch capacity error')
    
    # plot extents
    #fig.update_yaxes(range=[min(sp_y), max(sp_y)], fixedrange=True)
    #fig.update_xaxes(range=[min(b_x), max(sp_x)])
    
    fig.update_xaxes(scaleanchor = "y", scaleratio = 1)
    #fig.update_yaxes(scaleanchor = "x", scaleratio = 1)

    return fig


# App HTML layout
styledict = {'display':'inline-block','vertical-align':'left', 'margin-top':'10px','margin-left':'20px','font-size':10,'font-family':'Verdana','textAlign':'center'}

# Dropdown and input fields, saved as variables
standoff = dcc.Input(id='standoff-state', type='number', value=18, min=5, max=50, step=1, style={'width': '60px', 'display':'inline-block', 'margin-left':'5px','vertical-align':'middle'})

swellfactor = dcc.Input(id='swellfactor-state', type='number', value=1.3, min=0.8, max=2, step=0.05, style={'width': '150px', 'display':'inline-block', 'margin-left':'5px','vertical-align':'left', 'textAlign' : 'center'})

bundheight = dcc.Input(id='bundheight-state', type='number', value=2, min=0, max=5, step=0.1, style={'width': '80px', 'display':'inline-block', 'margin-left':'5px','vertical-align':'middle'})

runoutangle = dcc.Input(id='runoutangle-state', type='number', value=37, min=1, max=89, style={'width': '60px', 'display':'inline-block', 'margin-left':'5px','vertical-align':'left', 'textAlign':'center',})

spx = dcc.Input(id='spx-state', type='text', value="0,3.5,6.4,7.1,9,12.4,16.5,22.1,28.8", style={'width': '300px', 'display':'inline-block', 'margin-left':'5px','vertical-align':'left', 'textAlign':'center',})

spy = dcc.Input(id='spy-state', type='text', value="0,5.2,11.6,16.5,21.6,27.7,32.3,35.6,36", style={'width': '300px', 'display':'inline-block', 'margin-left':'5px','vertical-align':'left', 'textAlign':'center',})

fsx = dcc.Input(id='fsx-state', type='text', value="6.4,14.3,18.6,22.1", style={'width': '300px', 'display':'inline-block', 'margin-left':'5px','vertical-align':'left', 'textAlign':'center',})

fsy = dcc.Input(id='fsy-state', type='text', value="11.6,17.7,22.9,35.6", style={'width': '300px', 'display':'inline-block', 'margin-left':'5px','vertical-align':'left', 'textAlign':'center',})

directions = ['left', 'right']
direction = dcc.Dropdown(id='direction-state', options=[{'label': i, 'value': i} for i in directions], value='left', style={'width': '60px', 'display':'inline-block', 'margin-left':'5px','vertical-align':'middle'})

projects = ["yes", "no"]
project = dcc.Dropdown(id='project-state', options=[{'label': i, 'value': i} for i in projects], value="yes", style={'width': '60px', 'display':'inline-block', 'margin-left':'5px','vertical-align':'middle'})

app.layout = html.Div([    
    html.Div([html.Img(src='https://raw.githubusercontent.com/j-ahn/misc/main/favicon.png',style={'display':'inline-block', 'width': '1.5%', 'height': '1.5%', 'margin-left': '25px'}),
              html.H1(children='Runout Calculator',
            style={'display':'inline-block','textAlign': 'left','margin-left': '25px', 'font-family':'Verdana', 'font-size': 30,'vertical-align':'middle'})],
             style={'margin-top': '25px'}),

    html.Br(style={'height':'10px'}),
    
    html.Div([html.Label(["Slope profile (x, y):",spx, spy])],
         style=styledict),
    
    html.Div([html.Label(["Failure surface (x, y):",fsx, fsy])],
         style=styledict),
    
    html.Div(html.P([html.Br()])),
    
    
    html.Div([html.Label(["Standoff (m):",standoff])],
         style=styledict),
    
    html.Div([html.Label(["Swell factor:",swellfactor])],
         style=styledict),
    
    html.Div([html.Label(["Bund height (m):",bundheight])],
         style=styledict),
        
    html.Div([html.Label(["Runout Angle (°):",runoutangle])],
         style=styledict),
    
    html.Div([html.Label(["Slope direction:",direction])],
         style=styledict),
    
    html.Div([html.Label(["Project to backscarp:",project])],
         style=styledict),
        
    
    html.Div([html.Button('Update', id='update_button', n_clicks=0)], style=styledict),
    
    dcc.Graph('dashboard',style={'height': '70vh'},config={'displayModeBar': True, 
                      'scrollZoom':False,
                      'displaylogo':False,
                      'toImageButtonOptions': {'format': 'svg','filename': 'runout_calculator'},
                      'modeBarButtonsToRemove':['hoverClosestPie']}),
    
        html.Div(dcc.Markdown('''Enter slope profile and failure surface co-ordinates from bottom to top (1 decimal place) as comma delimited strings. Start and finish points of failure surface must co-incide with points on the slope profile - app will snap to nearest node. Created by : Jiwoo Ahn
    '''), style = {'font-size':10,'font-family':'Verdana','textAlign':'center'})
])

@app.callback(
    Output('dashboard', 'figure'),
    Input('update_button', 'n_clicks'),
    State('standoff-state', 'value'),
    State('swellfactor-state', 'value'),
    State('bundheight-state', 'value'),
    State('runoutangle-state', 'value'),
    State('spx-state', 'value'),
    State('spy-state', 'value'),
    State('fsx-state', 'value'),
    State('fsy-state', 'value'),
    State('direction-state','value'),
    State('project-state','value')
)

def update_graph(n_clicks, standoff, swellfactor, bundheight, runoutangle, spx, spy, fsx, fsy, direction, project):
    if n_clicks >= 0:
        fig = plot_runout(standoff, swellfactor, bundheight, runoutangle, spx, spy, fsx, fsy, direction, project)
    return fig

if __name__ == '__main__':
    app.run_server()
    
