#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Fri Dec 20 00:07:22 2024

@author: group_project
"""

import geopandas as gpd
import matplotlib.pyplot as plt
import networkx as nx
import osmnx as ox
from shapely.geometry import LineString, Point, Polygon
import folium
import dash
from dash import html, dcc, Input, Output
import os
import pandas as pd
import plotly.express as px
from functools import reduce
import operator
import plotly.graph_objects as go
import json
from plotly.io import read_json
import plotly.io as pio
import numpy as np



# These paths need to be updated before running the code
# These paths need to be updated before running the code
geojson_path = "/Users/theispaaske/git-practice/Theispaa.github.io/VISP/output_file.geojson"
csv_file_path = "/Users/theispaaske/git-practice/Theispaa.github.io/VISP/ElectricCarData_Clean.csv"
file_path = ("/Users/theispaaske/git-practice/Theispaa.github.io/VISP")



# Different variables below here

# geojson for heatmap
with open(geojson_path) as f:
    geojson_data = json.load(f)
geojson_lats = [feature["geometry"]["coordinates"][1] for feature in geojson_data["features"]]
geojson_lons = [feature["geometry"]["coordinates"][0] for feature in geojson_data["features"]]
    
# Load vehicle data
vehicle_data = pd.read_csv(csv_file_path, sep=';')
# Normalize data
vehicle_data['FastCharge_KmH'] = pd.to_numeric(vehicle_data['FastCharge_KmH'], errors='coerce')
vehicle_data['Brand_Model'] = vehicle_data['Brand'] + ' ' + vehicle_data['Model']
columns_to_check = ['Range_Km', 'Efficiency_WhKm', 'TopSpeed_KmH', 'FastCharge_KmH']
vehicle_data = vehicle_data.dropna(subset=columns_to_check)
vehicle_data = vehicle_data[(vehicle_data[columns_to_check] != 0).all(axis=1)]
normalized_vehicle_data = vehicle_data.copy()
for col in columns_to_check:
    normalized_vehicle_data[col] = vehicle_data[col] / vehicle_data[col].max()
    


# Average for spyder graph
categories = ['Range_Km', 'Efficiency_WhKm', 'TopSpeed_KmH', 'FastCharge_KmH']

average_data = (
    normalized_vehicle_data.groupby('BodyStyle')[categories]
    .mean()
    .reset_index()
)


average_data['Brand_Model'] = average_data['BodyStyle']

normalized_vehicle_data_with_averages = pd.concat([normalized_vehicle_data, average_data], ignore_index=True)

# Trip times for the map
trip_times = [30, 60]

# Load network map (remember to change path)
G = ox.load_graphml(("/Users/theispaaske/git-practice/Theispaa.github.io/VISP/denmark_driving_network_from_place.graphml"))







# Functions to generate visuals and collect the needed data below

def calculate_co2_emissions_per_km(benzin_forbrug_km_per_liter, diesel_forbrug_km_per_liter, el_forbrug_kwh_per_100km, battery_size_kwh):
    antal_intervaller = 10
    pr_year = 10000
    co2_karosseri = 25
    Realitetsfaktor = 1.14
    
    
    # Elbil
    Elmiks_production = 38.55
    Realitetsfaktor_elbil = 1.19
    Forbrug_KwhPer100km = el_forbrug_kwh_per_100km * Realitetsfaktor_elbil
    samlet_batteriudledning = battery_size_kwh * 106
    el_og_brandstofssproduktion = (Elmiks_production * Forbrug_KwhPer100km) / 100
    samlet_el_prkm = (el_og_brandstofssproduktion + co2_karosseri) / 1000
    
    CO2_elbil = {}
    for i in range(antal_intervaller + 1):  
        km = i * pr_year  
        if i == 0:
            emissions = samlet_batteriudledning
        else:
            emissions = (samlet_el_prkm * km) + samlet_batteriudledning
        CO2_elbil[km] = emissions


    co2_per_liter_benzin = 1422
    co2_udstødning_benzin = 2178
    co2_per_liter_diesel = 2880
    co2_udstødning_diesel = 2420

    Forbrug_liter_benzin_per_100_km_WLTP = 100 / benzin_forbrug_km_per_liter
    Reelt_forbrug_benzin = Forbrug_liter_benzin_per_100_km_WLTP * Realitetsfaktor
    Exhaust_emissons_petrol = (Reelt_forbrug_benzin * co2_udstødning_benzin) / 100
    Fuel_emissions_petrol = (Reelt_forbrug_benzin * co2_per_liter_benzin) / 100
    total_benzin_udledning = (co2_karosseri + Exhaust_emissons_petrol + Fuel_emissions_petrol) / 1000

    CO2_petrol = {}
    for i in range(antal_intervaller + 1):  
        km = i * pr_year  
        if i == 0:
            emissions = 0
        else:
            emissions = (total_benzin_udledning * km)
        CO2_petrol[km] = emissions

    Forbrug_liter_diesel_per_100_km_WLTP = 100 / diesel_forbrug_km_per_liter
    Reelt_forbrug_diesel = Forbrug_liter_diesel_per_100_km_WLTP * Realitetsfaktor
    Exhaust_emissons_diesel = (Reelt_forbrug_diesel * co2_udstødning_diesel) / 100
    Fuel_emissions_diesel = (Reelt_forbrug_diesel * co2_per_liter_diesel) / 100
    total_diesel_udledning = (co2_karosseri + Exhaust_emissons_diesel + Fuel_emissions_diesel) / 1000

    CO2_diesel = {}
    for i in range(antal_intervaller + 1): 
        km = i * pr_year 
        if i == 0:
            emissions = 0
        else:
            emissions = (total_diesel_udledning * km)
        CO2_diesel[km] = emissions

    return {
        "EV": CO2_elbil,
        "Petrolcar": CO2_petrol,
        "Dieselcar": CO2_diesel
    }


def get_v_data(car):
    result = vehicle_data[['Brand', 'Range_Km', 'Combined Cold', 'Combined mild']][vehicle_data['Brand_Model'] == car]
    brand, range_km, range_cold, range_mild = result.iloc[0][['Brand', 'Range_Km', 'Combined Cold', 'Combined mild']]
    range_mixed = (range_cold + range_mild) / 2
    print(brand)
    return range_cold, range_mixed, range_mild


def get_city(name,file_path):
    pd_df = pd.read_csv(("/Users/theispaaske/git-practice/Theispaa.github.io/VISP/Danmarks_Storste_Byer.csv"), sep=",")
    result  = pd_df[['Breddegrad (N)', 'Længdegrad (E)','center_node','x_utm','y_utm']][pd_df['By'] == name]
    x, y, lat, lon, center_node = result.iloc[0][['x_utm', 'y_utm', 'Breddegrad (N)', 'Længdegrad (E)','center_node']]
    return x, y, lat, lon, center_node


def get_poly(G, center_node, trip_times, travel_speed, edge_buff=5000, node_buff=5000, infill=False):
    isochrone_polys = []
    trip_times = [30, 60]
    
    meters_per_minute = travel_speed * 1000 / 60  # km per hour to m per minute
    for _, _, _, data in G.edges(data=True, keys=True):
        data["time"] = data["length"] / meters_per_minute

    for trip_time in sorted(trip_times, reverse=True):
        subgraph = nx.ego_graph(G, center_node, radius=trip_time, distance="time")
        node_points = [Point((data["x"], data["y"])) for node, data in subgraph.nodes(data=True)]
        nodes_gdf = gpd.GeoDataFrame({"id": list(subgraph.nodes)}, geometry=node_points)
        nodes_gdf = nodes_gdf.set_index("id")

        edge_lines = []
        for n_fr, n_to in subgraph.edges():
            f = nodes_gdf.loc[n_fr].geometry
            t = nodes_gdf.loc[n_to].geometry
            edge_lookup = G.get_edge_data(n_fr, n_to)[0].get("geometry", LineString([f, t]))
            edge_lines.append(edge_lookup)

        n = nodes_gdf.buffer(node_buff).geometry
        e = gpd.GeoSeries(edge_lines).buffer(edge_buff).geometry
        all_gs = list(n) + list(e)
        new_iso = gpd.GeoSeries(all_gs).union_all()

        if infill:
            new_iso = Polygon(new_iso.exterior)
        isochrone_polys.append(new_iso)
    
    gdf = gpd.GeoDataFrame(geometry=isochrone_polys)
    gdf = gdf.set_crs(G.graph["crs"]).to_crs(epsg=4326)
    return gdf


def get_color(trip_times):
    custom_colors = ["#90EE90", "#006400"]
    iso_colors = custom_colors[:len(trip_times)]
    print(iso_colors)
    return iso_colors


def get_map(trip_times, travel_speed, G, city_name):
    G = G
    x, y, lat, lon, center_node = get_city(city_name, file_path)
    gdf = get_poly(G, center_node, trip_times, travel_speed)
    iso_colors = get_color(trip_times)
    
    features = []
    for poly, color in zip(gdf.geometry, iso_colors):
        if not poly.is_empty:
            features.append({
                "type": "Feature",
                "properties": {"color": color},
                "geometry": {
                    "type": "Polygon",
                    "coordinates": [list(poly.exterior.coords)]
                }
            })

    geojson_data = {
        "type": "FeatureCollection",
        "features": features
    }
    
    
    city_coords = {"lat": lat, "lon": lon}


    fig = px.choropleth_mapbox(
        geojson=geojson_data,
        locations=iso_colors,  
        featureidkey="properties.color",
        color=["Full range", "Half Range"],
        mapbox_style="carto-positron",
        center={"lat": 56.2038, "lon": 10.7024},
        zoom=6.2,
        opacity=0.4,
        color_discrete_sequence=["#90EE90", "#006400"]
    )
    
    
    
    fig.add_scattermapbox(
        lat=[city_coords["lat"]],
        lon=[city_coords["lon"]],
        mode="markers+text",  
        marker=dict(size=10, color="red"),
        name = city_name,
        showlegend=True,  
        text=city_name,
        textposition="middle left"
    )
    
    
    
    fig.update_layout(
        margin={"r": 0, "t": 0, "l": 0, "b": 0},
        autosize=False,
        width=650,
        height=600,
        legend_title="Explanation",
        legend=dict(
            x=0.8,  
            y=0.95,
            bgcolor="rgba(255,255,255,0.8)", 
            bordercolor="black",
            borderwidth=1
        )
    )

    
    
    return fig


def heat_map(fig, checkbox_enabled = False):
    
    fig = fig 
    checkbox_enabled = checkbox_enabled
    if checkbox_enabled:
        
        density_map = px.density_mapbox(
            lat=geojson_lats,
            lon=geojson_lons,
            radius=2,
            color_continuous_scale=[
                (0.0, "blue"),    
                (1.0, "red")      
            ],
            range_color=(0, 1),  
        )

        fig.add_trace(density_map.data[0])
        fig.update_layout(coloraxis_colorbar=dict(title="Density<br><span style='font-size:10px;'>Charging Stations</span>", tickvals=[0, 1], ticktext=["Low", "High"]))
    else:
        
        fig.data = [trace for i, trace in enumerate(fig.data) if i != 3]
    return fig
    

def check_map(selection_data, dropdown_value, travel_speed=50):
    file_name = f"{selection_data}_{dropdown_value}_{travel_speed}.fig"
    file_path = f"/Users/theispaaske/git-practice/Theispaa.github.io/VISP/{file_name}"

    if os.path.exists(file_path):
        fig = read_json(file_path)
        return fig
    else:
        fig = get_map(trip_times, travel_speed, G, dropdown_value)
        fig.write_json(file_path)
        return fig
    return fig
    
# map to fill visiual
initial_map_fig = get_map(trip_times,30,G,'Odense')

# Sunburst plot
sunburst_fig = px.sunburst(
    vehicle_data,
    path=['BodyStyle', 'Brand', 'Brand_Model'],
    title="Explore vehicles",
    maxdepth=2,
    color='BodyStyle'
)







# Dash-app
app = dash.Dash(__name__)

app.layout = html.Div([
    html.H1(
        "Visual Exploration of Electric vehicles and C02 Emissions",
        style={
            'textAlign': 'center',
            'marginBottom': '10px',
            'color': '#333',
            'fontFamily': 'Arial, sans-serif',
            'fontSize': '24px'
        }
    ),

    dcc.Store(id='sunburst-selection'),

    
    html.Div(
        id='selected-sunburst-element',
        children="You have chosen (sunburst element): None",
        style={
            'textAlign': 'center',
            'margin': '10px',
            'fontSize': '18px',
            'color': '#555',
            'fontFamily': 'Arial, sans-serif'
        }
    ),

    
    html.Div([
        
        html.Div([
            
            html.Div([
                dcc.Graph(
                    id='sunburst-graph',
                    figure=sunburst_fig,
                    style={
                        'height': '550px',
                        'width': '100%',
                        'marginBottom': '10px'
                    }
                )
            ]),

            # spyder Graph
            html.Div([
                html.Label(
                    "Choose a vehicle to compare:",
                    style={'marginRight': '10px', 'fontWeight': 'bold', 'fontFamily': 'Arial, sans-serif'}
                ),
                dcc.Dropdown(
                    id='vehicle-dropdown',
                    options=[
                        {'label': model, 'value': model} for model in normalized_vehicle_data['Brand_Model']
                    ],
                    value='Model A',  
                    placeholder="Choose vehicle",
                    style={'width': '100%', 'marginBottom': '10px'}
                ),
                dcc.Graph(
                    id='radar-graph',
                    style={
                        'height': '590px',
                        'width': '100%',
                        'marginBottom': '10px'
                    }
                )
            ])
        ], style={'width': '40%', 'display': 'inline-block', 'verticalAlign': 'top', 'paddingRight': '10px'}),

        
        html.Div([
            
            html.Div([
                html.H2(
                    "Range Insights",
                    style={
                        'textAlign': 'left',
                        'marginBottom': '5px',
                        'color': '#444',
                        'fontFamily': 'Arial, sans-serif',
                        'fontSize': '20px'
                    }
                ),
                html.P(
                    "Explore the range from your chosen vehicle and show available charging stations.",
                    style={
                        'textAlign': 'left',
                        'marginBottom': '5px',
                        'color': '#666',
                        'fontFamily': 'Arial, sans-serif',
                        'fontSize': '14px'
                    }
                ),
                html.P(
                    "Cold = max 10°C, mild = max 23°C.",
                    style={
                        'textAlign': 'left',
                        'marginBottom': '15px',
                        'color': '#666',
                        'fontFamily': 'Arial, sans-serif',
                        'fontSize': '14px'
                    }
                )
            ], style={'marginBottom': '15px'}),

            # Dropdown, slider & checkbox
            html.Div([            
                html.Label(
                    "City:",
                    style={'marginRight': '10px', 'fontWeight': 'bold', 'fontFamily': 'Arial, sans-serif'}
                ),
                dcc.Dropdown(
                    id='dropdown-selection',
                    options=[
                        {'label': 'Odense', 'value': 'Odense'},
                        {'label': 'Aarhus', 'value': 'Aarhus'},
                        {'label': 'Copenhagen', 'value': 'København'}
                    ],
                    placeholder="Choose a city",
                    style={'width': '180px', 'marginRight': '17px'}
                ),
                html.Label(
                    "Temperature:",
                    style={'marginRight': '10px', 'fontWeight': 'bold', 'fontFamily': 'Arial, sans-serif'}
                ),
                html.Div(
                    dcc.Slider(
                        id='temperature-slider',
                        min=0,
                        max=2,
                        step=1,
                        marks={
                            0: 'Cold',
                            1: 'Mixed',
                            2: 'Mild'
                        },
                        value=1
                        
                    ),
                    style={'width': '200px', 'marginRight': '20px'}
                ),
                dcc.Checklist(
                    id='checkbox-selection',
                    options=[
                        {'label': 'Show Charging Stations', 'value': 'show_data'}
                    ],
                    value=[],
                    style={
                        'fontFamily': 'Arial, sans-serif',
                        'fontSize': '14px',
                        'marginLeft': '20px'
                    },
                    labelStyle={
                        'display': 'flex',
                        'flexDirection': 'column',
                        'alignItems': 'flex-start',
                    },
                    inputStyle={
                        'marginBottom': '5px',  
                        'marginLeft': '0px'  
                    }
                )
            ], style={
                'display': 'flex',
                'alignItems': 'center',
                'marginTop': '10px',
                'marginBottom': '2px'
            }),

            
            dcc.Graph(
                id='map',
                figure=initial_map_fig,
                style={
                    'height': '650px',
                    'width': '100%'
                }
            ),

            
            html.Div([
                html.Label(
                    "Compare C02 emissions",
                    style={'marginRight': '10px', 'fontWeight': 'bold', 'fontFamily': 'Arial, sans-serif'}
                ),
                html.P(
                    "Enter the fuel efficiency of your vehicle to compare their CO2 emissions according to the WLTP range.",
                    style={
                        'fontSize': '14px',
                        'color': '#555',
                        'marginBottom': '10px',
                        'fontFamily': 'Arial, sans-serif'
                    }
                ),
                html.P(
                    "For electric vehicles the CO2 emissions from battery production is included in km 0.",
                    style={
                        'fontSize': '14px',
                        'color': '#555',
                        'marginBottom': '10px',
                        'fontFamily': 'Arial, sans-serif'
                    }
                ),
                html.Div([
                    dcc.Input(
                        id='input1',
                        type='number',
                        placeholder='km/L (petrol)',
                        style={'marginRight': '10px'}
                    ),
                    dcc.Input(
                        id='input2',
                        type='number',
                        placeholder='km/L (diesel)'
                    ),
                ], style={'marginBottom': '10px'}),
                dcc.Graph(
                    id='custom-graph',
                    style={'height': '420px', 'width': '100%'}
                )
            ], style={'marginTop': '20px'})
        ], style={'width': '60%', 'display': 'inline-block', 'verticalAlign': 'top'})
    ], style={'width': '100%', 'display': 'flex', 'justifyContent': 'space-between'})
], style={
    'fontFamily': 'Arial, sans-serif',
    'maxWidth': '1200px',
    'margin': '0 auto',
    'padding': '10px',
    'backgroundColor': '#f9f9f9',
    'border': '1px solid #ddd',
    'borderRadius': '8px',
    'boxShadow': '0px 4px 6px rgba(0, 0, 0, 0.1)'
})

# Callback to save car
@app.callback(
    Output('sunburst-selection', 'data'),
    Input('sunburst-graph', 'clickData')
)
def update_selection(click_data):
    if click_data:
        click_data = click_data
    
        return click_data  

# Callback to show the chosen car
@app.callback(
    Output('selected-sunburst-element', 'children'),
    Input('sunburst-graph', 'clickData')
)
def update_sunburst_selection(click_data):
    if click_data:
        selected_label = click_data['points'][0].get('label', 'None')
        return f"You have chosen: {selected_label}"
    return "Please choose a vehicle to begin"

# Callback to get map
@app.callback(
    Output('map', 'figure'),  # Opdaterer kortet direkte
    [
        Input('sunburst-selection', 'data'),
        Input('dropdown-selection', 'value'),
        Input('checkbox-selection', 'value'),
        Input('temperature-slider', 'value')   
    ]
)
def update_map(selection_data, dropdown_value, checkbox_value, temperature_value):
    try:
       checkbox_enabled = 'show_data' in checkbox_value if checkbox_value else False
       
       fig = initial_map_fig
       dropdown_value = dropdown_value or 'Odense'
       
       if checkbox_enabled:
           fig = heat_map(fig, True)
       if checkbox_enabled == False:
           fig = heat_map(fig)
    
           
       
       if selection_data and dropdown_value:
           print(selection_data['points'][0]['label'])
           print(dropdown_value)
           range_cold, range_mixed, range_mild = get_v_data(selection_data['points'][0]['label'])
           
           print(temperature_value)
           
           if temperature_value == 0:
               travel_speed = range_cold
           elif temperature_value == 1:
               travel_speed = range_mixed
           else:
               travel_speed = range_mild

           if checkbox_enabled:
               print(travel_speed)
               fig = check_map(selection_data['points'][0]['label'], dropdown_value, travel_speed)
               fig = heat_map(fig, True)
           else: 
               print(travel_speed)
               fig = check_map(selection_data['points'][0]['label'], dropdown_value, travel_speed)
               fig = heat_map(fig)
       
       fig.update_layout(
            mapbox=dict(
                center={"lat": 56.2038, "lon": 10.7024},
                zoom=6.2
                
                
            )
        )
       
       
       fig.update_layout(
           width=700,  
           height=600  
           )
        
       return fig
   
    except Exception as e:        
           return initial_map_fig
      
        
# Callback til spyder-graph
@app.callback(
    Output('radar-graph', 'figure'),
    [Input('sunburst-graph', 'clickData'),
     Input('vehicle-dropdown', 'value')]
)
def update_radar(clickData, selected_model):
    
    radar_fig_start = single_radar('Polestar  2')
    radar_fig = single_radar('Polestar  2')
    
    try:
    
        if selected_model:
            radar_fig = double_radar('Polestar  2', selected_model)

    
        if clickData and selected_model:
            radar_fig = double_radar(clickData['points'][0]['label'], selected_model)
        elif clickData:
            radar_fig = ave_radar(clickData['points'][0]['label'])
            
        return radar_fig
    
    except KeyError as e:
        return radar_fig_start
    
    return radar_fig

def single_radar(selected_label):
    result = normalized_vehicle_data[['Range_Km', 'Efficiency_WhKm', 'TopSpeed_KmH', 'FastCharge_KmH']][normalized_vehicle_data['Brand_Model'] == selected_label]
    Range_Km, Efficiency_WhKm, TopSpeed_KmH, FastCharge_KmH = result.iloc[0][['Range_Km', 'Efficiency_WhKm', 'TopSpeed_KmH', 'FastCharge_KmH']]
    
    # Eksempeldata baseret på valg
    categories = ['Range_Km', 'Efficiency_WhKm', 'TopSpeed_KmH', 'FastCharge_KmH']
    values = [Range_Km, Efficiency_WhKm, TopSpeed_KmH, FastCharge_KmH]
    
    values += values[:1]
    categories += categories[:1]
    
    # Opret radar-figuren
    radar_fig = go.Figure(
        data=go.Scatterpolar(
            r=values,
            theta=categories,
            fill='toself',
            name=selected_label
        )
    )
    radar_fig.update_layout(
        polar=dict(
            radialaxis=dict(
                visible=True,
                range=[0, 1],
                showticklabels=False
            )
        ),
        showlegend=True,
        legend=dict(
            orientation="h",  # Horizontal layout
            yanchor="bottom",
            y=-0.3,  # Justér y-værdien for at placere den under grafen
            xanchor="center",
            x=0.5
        ),
        title="Vehicle Specs Comparison"
    )
    return radar_fig
        
def double_radar(selected_label, selected_label_2):


    result = normalized_vehicle_data_with_averages[['Range_Km', 'Efficiency_WhKm', 'TopSpeed_KmH', 'FastCharge_KmH']][normalized_vehicle_data_with_averages['Brand_Model'] == selected_label]
    Range_Km, Efficiency_WhKm, TopSpeed_KmH, FastCharge_KmH = result.iloc[0][['Range_Km', 'Efficiency_WhKm', 'TopSpeed_KmH', 'FastCharge_KmH']]
    
    
    result_2 = normalized_vehicle_data_with_averages[['Range_Km', 'Efficiency_WhKm', 'TopSpeed_KmH', 'FastCharge_KmH']][normalized_vehicle_data_with_averages['Brand_Model'] == selected_label_2]
    Range_Km_2, Efficiency_WhKm_2, TopSpeed_KmH_2, FastCharge_KmH_2 = result_2.iloc[0][['Range_Km', 'Efficiency_WhKm', 'TopSpeed_KmH', 'FastCharge_KmH']]
    
    if result_2.empty:
        print(f" No data for comparison: {selected_label_2}")
        return single_radar(selected_label)

    categories = ['Range_Km', 'Efficiency_WhKm', 'TopSpeed_KmH', 'FastCharge_KmH']
    values = [Range_Km, Efficiency_WhKm, TopSpeed_KmH, FastCharge_KmH]
    values_2 = [Range_Km_2, Efficiency_WhKm_2, TopSpeed_KmH_2, FastCharge_KmH_2]
    
    values += values[:1]
    values_2 += values_2[:1]
    categories += categories[:1]
    

    radar_fig = go.Figure()
    

    radar_fig.add_trace(
        go.Scatterpolar(
            r=values,
            theta=categories,
            fill='toself',
            name=selected_label
        )
    )
    

    radar_fig.add_trace(
        go.Scatterpolar(
            r=values_2,
            theta=categories,
            fill='toself',
            name=selected_label_2
        )
    )
    
    radar_fig.update_layout(
        polar=dict(
            radialaxis=dict(
                visible=True,
                range=[0, 1],
                showticklabels=False
            )
        ),
        showlegend=True,
        legend=dict(
            orientation="h",  
            yanchor="bottom",
            y=-0.3,  
            xanchor="center",
            x=0.5
        ),
        title="Vehicle Specs Comparison"
    )
    
    return radar_fig


def ave_radar(selected_label):
    

    result = normalized_vehicle_data_with_averages[['Range_Km', 'Efficiency_WhKm', 'TopSpeed_KmH', 'FastCharge_KmH','BodyStyle']][normalized_vehicle_data_with_averages['Brand_Model'] == selected_label]
    Range_Km, Efficiency_WhKm, TopSpeed_KmH, FastCharge_KmH, BodyStyle = result.iloc[0][['Range_Km', 'Efficiency_WhKm', 'TopSpeed_KmH', 'FastCharge_KmH','BodyStyle']]
    
    

    result_2 = normalized_vehicle_data_with_averages[['Range_Km', 'Efficiency_WhKm', 'TopSpeed_KmH', 'FastCharge_KmH']][normalized_vehicle_data_with_averages['Brand_Model'] == BodyStyle]
    Range_Km_2, Efficiency_WhKm_2, TopSpeed_KmH_2, FastCharge_KmH_2 = result_2.iloc[0][['Range_Km', 'Efficiency_WhKm', 'TopSpeed_KmH', 'FastCharge_KmH']]
    

    categories = ['Range_Km', 'Efficiency_WhKm', 'TopSpeed_KmH', 'FastCharge_KmH']
    values = [Range_Km, Efficiency_WhKm, TopSpeed_KmH, FastCharge_KmH]
    values_2 = [Range_Km_2, Efficiency_WhKm_2, TopSpeed_KmH_2, FastCharge_KmH_2]
    
    values += values[:1]
    values_2 += values_2[:1]
    categories += categories[:1]
    

    radar_fig = go.Figure()
    

    radar_fig.add_trace(
        go.Scatterpolar(
            r=values,
            theta=categories,
            fill='toself',
            name=selected_label
        )
    )
    

    radar_fig.add_trace(
        go.Scatterpolar(
            r=values_2,
            theta=categories,
            fill='toself',
            name=BodyStyle
        )
    )
    
    radar_fig.update_layout(
        polar=dict(
            radialaxis=dict(
                visible=True,
                range=[0, 1],
                showticklabels=False
            )
        ),
        showlegend=True,
        legend=dict(
            orientation="h",  
            yanchor="bottom",
            y=-0.3,  
            xanchor="center",
            x=0.5
        ),
        title="Vehicle Specs Comparison"
    )
    
    return radar_fig

# Callback to line chart
@app.callback(
    Output('custom-graph', 'figure'),
    [Input('sunburst-graph', 'clickData'), 
     Input('input1', 'value'),
     Input('input2', 'value')]
)
def update_custom_graph(clickData, value1, value2):
    
    selected_label = 'Polestar  2'
    value1 = value1 or 21.8
    value2 = value2 or 26.6
   
    try:
        if clickData:
            selected_label = clickData['points'][0]['label']
    
    except Exception as e:
        selected_label = 'Polestar  2'
    
        
    
    result = vehicle_data[['Range_Km', 'Battery_size']][vehicle_data['Brand_Model'] == selected_label]
   
    if result.empty:
        result = vehicle_data[['Range_Km', 'Battery_size']][vehicle_data['Brand_Model'] == 'Polestar  2']
    
   
    
    
    Range_Km, Battery_size = result.iloc[0][['Range_Km', 'Battery_size']].replace(',', '.', regex=True).astype(float)
    
    
    usage_prkwh = (Battery_size / Range_Km) * 100
    
    
    data = calculate_co2_emissions_per_km(benzin_forbrug_km_per_liter = value1, 
                                          diesel_forbrug_km_per_liter = value2, 
                                          el_forbrug_kwh_per_100km = usage_prkwh, 
                                          battery_size_kwh = Battery_size,
                                          )
   
    
   
        # Create the figure
    fig = line_chart(data, value1, value2,usage_prkwh,selected_label)
    
    return fig
    

def line_chart(data, value1, value2,usage_prkwh,selected_label):
    

    x_values = list(data['EV'].keys())
    
    # Create the figure
    fig = go.Figure()
    

    fig.add_trace(go.Scatter(
        x=x_values,
        y=list(data["Dieselcar"].values()),
        mode='lines',
        name=f'Diesel Emissions at ({value2}) km/L'
    ))
    
    fig.add_trace(go.Scatter(
        x=x_values,
        y=list(data["Petrolcar"].values()),
        mode='lines',
        name=f'Petrol Emissions at ({value1}) km/L'
    ))
    
    fig.add_trace(go.Scatter(
        x=x_values,
        y=list(data["EV"].values()),
        mode='lines',
        name=f'EV Emissions at ({usage_prkwh:.0f}) km/KwH'
    ))
    

    fig.update_layout(
        title=f'CO2 Emissions Over Time for ({selected_label})',
        xaxis_title="Distance (km)",
        yaxis_title="TOTAL CO2 Emissions in KG",
        yaxis=dict(
            title="TOTAL CO2 Emissions in KG",
            range=[0, 20000],  
            tickformat=",.0f", 
            gridcolor="lightgrey",
        ),
        template="plotly_white"
    )
    
    return fig

#%%

# Run the app
if __name__ == '__main__':
    app.run(debug=True)

#%%