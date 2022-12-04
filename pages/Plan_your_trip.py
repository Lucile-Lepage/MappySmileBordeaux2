# -*- coding: utf-8 -*-
"""
Created on Mon Nov 28 16:13:06 2022

@author: Lucile Lepage
"""

import time
import pandas as pd 
import numpy as np
import requests
import folium
from folium  import plugins
import streamlit as st
from streamlit_folium import st_folium
from sqlalchemy import create_engine
from streamlit_option_menu import option_menu

st.title("MappySmileBord'eau")
st.write('What transport is available around my position?')

menu_selected = option_menu(None, ["MappySmileBord'eau","Home", "Plan your trip"], 
    icons=['house', 'cloud-upload', "list-task", 'gear'], 
    menu_icon="cast", default_index=2, orientation="horizontal")
 
with st.sidebar:  
    
    st.title(":sun_with_face::heart_eyes::sleeping:")
    st.title("")
    
    link_street_names="https://opendata.bordeaux-metropole.fr/explore/dataset/bor_refvoiesquartiers/download/?format=csv&timezone=Europe/Berlin&lang=fr&use_labels_for_header=true&csv_separator=%3B"
    df_street_names=pd.read_csv(link_street_names,sep=';',usecols=['libellevoie','codepostal'])
    df_street_names.drop_duplicates(subset='libellevoie',inplace=True)
    df_street_names['link_api']="https://api-adresse.data.gouv.fr/search/?q="+df_street_names['libellevoie'].str.replace(" ","+")+"&postcode="+df_street_names['codepostal'].astype(str)+"&limit=1"
    
    list_streets=df_street_names['libellevoie'].tolist()
    
   
    street_choice = st.selectbox(
        'Select your street name',
        list_streets)
    st.title("")
          
    #### Recuperer les coordonnees de le rue choisie afin de faire un zoom sur la carte sur ces coodronnees
    #link_API_coordinates(rue):
    
    def get_lat_lon():
        """à partir du nom de la rue, appelle la fonction link_API_coordinates pour se connecter à l'API et renvoi la latitude et longitude"""
        requete=requests.get(df_street_names['link_api'][df_street_names['libellevoie']==street_choice].values[0])
        lat_user=requete.json()['features'][0]['geometry']['coordinates'][1]
        lon_user=requete.json()['features'][0]['geometry']['coordinates'][0]
        return(lat_user,lon_user)
      

   

    start_time = st.slider("Select your time", 0, 24, (0, 24))   
    st.title("")
    
    day = st.radio(
    "Select your day",
    ('Monday', 'Tuesday', 'Wednesday','Thursday','Friday','Saturday','Sunday'))
 
# /**************************************     1- import all my datasets and disply them           ********************************************/
# 1.1 create connection to my sql db
 # dialect+driver://username:password@host:port/database


# 1.2 import from db


# /*****************************************     2- analysing the datasets           ***********************************************/

# 2.1.1 merge the vcub dataset throught the station_id and add days / hours columns

def tidying_vcub_data_func(station_status,vcub_status):
    vcub_merged_data = pd.merge(station_status,vcub_status, how='inner', on='station_id')
    vcub_merged_data['station_id'] = vcub_merged_data['station_id'].astype(np.int64)
    vcub_merged_data['post_code'] = vcub_merged_data['post_code'].astype(np.int64)
    vcub_merged_data['last_reported'] = pd.to_datetime(vcub_merged_data['last_reported'])
    vcub_merged_data['date'] = vcub_merged_data['last_reported'].dt.date
    vcub_merged_data['day'] = vcub_merged_data['last_reported'].dt.day_name()
    vcub_merged_data['hour'] = vcub_merged_data['last_reported'].dt.hour
    return vcub_merged_data



# In[74]:
# 2.2.1 create a function to get the geo_shape data from link:
def get_geo_shape_func(data_link):
    data = requests.get(data_link).json()
    normalized_data= pd.json_normalize(data, record_path=['fields', 'geo_shape','coordinates'], meta=[['fields','gid']],errors='ignore')
    return normalized_data


# In[75]:
# 2.2.2 merge the trafic_status with the street captors geo_shape and add day and hour columns
# create function to tidy the trafic json, changing type and adding columns day /  hour
def tidying_trafic_data_func(trafic_staus, geo_shape_data):
    trafic_merged_df = pd.merge(trafic_staus, geo_shape_data, on='fields.gid', how='inner')
    trafic_merged_df.drop(columns=['fields.cdate','fields.mdate'], inplace=True )
    trafic_merged_df.rename(columns= {
                                    'record_timestamp' : 'date',
                                    'fields.typevoie' : 'road',
                                    'fields.etat': 'status'	,
                                    'fields.code_commune' :'postal_code',
                                    'fields.commune' : 'city',
                                    'fields.gid' : 'gid',
                                    'lat' : 'lat',
                                    'lon' :'lon',
                                    1 : 'lat_for_road',
                                    0 : 'lon_for_road',
                                },inplace=True)
    
    # 2.2.2 change type & add day and hour columns 
    trafic_merged_df['status'] = trafic_merged_df['status'].astype('category')
    trafic_merged_df['postal_code'] = trafic_merged_df['postal_code'].astype(np.int64)
    trafic_merged_df['gid'] = trafic_merged_df['gid'].astype(np.int64)
    trafic_merged_df['date'] = pd.to_datetime(trafic_merged_df['date'])

    trafic_merged_df['day'] = trafic_merged_df['date'].dt.day_name()
    trafic_merged_df['date_day'] = trafic_merged_df['date'].dt.date
    trafic_merged_df['hour'] = trafic_merged_df['date'].dt.hour
    return trafic_merged_df


# In[76]:
# 2.3.1 create function to tidy the transport json, changing type and adding columns day /  hour / symbole (train, bus, ship)
def tidying_transport_data_func(transport_status):
    transport_status.drop(columns=['fields.cdate','fields.mdate','fields.statut','fields.rs_sv_ligne_a','fields.arret','index'], inplace=True)

    # 2.3.2 rename columns and change the type
    transport_status.rename(columns={
                            'record_timestamp' :'date',
                            'fields.etat' : 'status',
                            'fields.vehicule' : 'vehicule',
                            'fields.gid' : 'gid',
                            'fields.retard' : 'late_status',
                            'fields.terminus' : 'terminus',
                            'fields.sens' :'direction',
                            'lat' : 'lat',
                            'lon' :'lon'
                        }, inplace=True)



    transport_status['status'] = transport_status['status'].astype('category') 
    transport_status['vehicule'] = transport_status['vehicule'].astype('category') 
    transport_status['late_status'] = transport_status['late_status'].astype('category') 
    transport_status['date'] = pd.to_datetime(transport_status['date'])
    transport_status['day'] = transport_status['date'].dt.day_name()
    transport_status['hour'] = transport_status['date'].dt.hour
    transport_status['date_day'] = transport_status['date'].dt.date
    transport_status['symbole'] = transport_status['vehicule'].apply(lambda x: 'bus' if (x =='BUS') else 'train' if (x=='TRAM_LONG' or x =='TRAM_COURT') else 'ship')
    return transport_status

# In[77]:
# 2.1.2 group the data throught station_id
def vcub_grouping_func(asked_vcub_data):
    grouped_vcub_df= asked_vcub_data.groupby(['station_id'], as_index=False).agg(
                                              quartier = ('name','first'),
                                              day = ('day','first'),
                                              moyenne_utilsation_per =('taux_utilisation_%', 'mean'),
                                              moyenne_remplissage_per = ('taux_remplissage_%', 'mean'),
                                              moyenne_bikes_available =('num_bikes_available', 'mean'),
                                              moyenne_docks_available = ('num_docks_available', 'mean'),
                                              lat = ('lat','first'),
                                              lon = ('lon','first')
                                            ).sort_values(by='station_id', ascending=True)

    return grouped_vcub_df
  
  
  # 2.2.3 grouping trafic data throught gid
def trafic_grouping_func(asked_trafic_data):
    trafic_grouped_df = asked_trafic_data.groupby(['gid'], as_index=False).agg(
                                                            lat_for_road_first = ('lat_for_road', 'first'),
                                                            lon_for_road_first = ('lon_for_road', 'first'),
                                                            lat_for_road_last = ('lat_for_road', 'last'),
                                                            lon_for_road_last = ('lon_for_road', 'last'),
                                                            lat =('lat','first'),
                                                            lon = ('lon','first'),
                                                            road = ('road', 'first'),
                                                            city = ('city','first'),
                                                            postal_code = ('postal_code','first'),
                                                            status = ('status',lambda x: x.mode()[0])
                                                         )

   # array(['INCONNU', 'FLUIDE', 'DENSE', 'EMBOUTEILLE'], dtype=object)
    return trafic_grouped_df

# 2.3.3 grouping the transport_df throught gid
def transport_grouping_func(asked_transport_ata):
    transport_grouped_df = asked_transport_ata.groupby(['gid'], as_index=False).agg(
                                                          day = ('day','first'),
                                                          lat = ('lat','first'),
                                                          lon = ('lon','first'),
                                                          status = ('status', lambda x : x.mode()[0]),
                                                          terminus = ('terminus', 'first'),
                                                          symbole = ('symbole','first'),
                                                          vehicule = ('vehicule', 'first'),
                                                        )
    return transport_grouped_df


# In[78]:


# 3 - trying to get df by filtering

def filtering_func(all_data, asked_day = None, asked_hour = None):
    hour = asked_hour
    day = asked_day
    all_days = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday','Sunday']
    
    if hour is None:
        hour = 0,24
    if day is None:
        day =  '|'.join(all_days)
        
    # get only the data for the day and time filters
    asked_df = all_data.loc[all_data['day'].str.contains(day) & (all_data['hour'].between(hour[0],hour[1], inclusive='left')) ]
    
    return asked_df


station_status = pd.read_csv('csv/df_stations_info.csv')
vcub_status = pd.read_csv('csv/df_stations_status_29_11_2022.csv')
trafic_status = pd.read_csv('csv/table_trafic_avec_wknd.csv')
transport_status = pd.read_csv('csv/table_transport_avec_wknd.csv')



# In[79]:
# /****************************************************  4- group all my func in one cell, to simplify the calling       *********************************************************/

# In[80]:

# 1.3 assigning my data
   
    
    # In[81]:
    # 2 - tidying function for all my newly dfs
    # vcub
tidyed_vcub_df = tidying_vcub_data_func(station_status,vcub_status)

# trafic
data_link = 'https://opendata.bordeaux-metropole.fr/explore/dataset/ci_trafi_l/download/?format=json&timezone=Europe/Berlin&lang=fr'
geo_shape_data = get_geo_shape_func(data_link)
geo_shape_data['fields.gid'] =  geo_shape_data['fields.gid'].astype(np.int64)
tidyed_trafic_df =tidying_trafic_data_func(trafic_status, geo_shape_data)

# transport
tidyed_transport_df = tidying_transport_data_func(transport_status)


# In[82]:
# 3- call the filtering function depending on the asked argument:

def calling_filtering_func(show_all=True , vcub_all_data=False , trafic_all_data=False, transport_all_data=False, asked_day=None, asked_hour=None):
    tab_to_display_in_map = {}
    global tidyed_vcub_df
    global tidyed_trafic_df
    global tidyed_transport_df
    
    
    # filter vcub data then grouping it throught station_id
    if vcub_all_data or show_all:
        filtered_vcub= filtering_func(tidyed_vcub_df,asked_day, asked_hour)
        ready_to_map_vcub = vcub_grouping_func(filtered_vcub)
        if 'moyenne_bikes_available' in ready_to_map_vcub.columns:
            ready_to_map_vcub['available_color'] = ready_to_map_vcub['moyenne_bikes_available'].apply(lambda x: 'red' if (x <= 3) else 'orange' if (x>3 and x<8) else 'green')
        else:
            print('there a bug, no moyenne_bikes_available column in vcub df, after grouping')
    
        tab_to_display_in_map['vcub'] = ready_to_map_vcub
    
    
    # filter trafic data then grouping it throught Gid
    if trafic_all_data or show_all:
        filtered_trafic= filtering_func(tidyed_trafic_df,asked_day, asked_hour)
        ready_to_map_trafic = trafic_grouping_func(filtered_trafic)
        tab_to_display_in_map['trafic'] = ready_to_map_trafic
        
        
    # filter transport data then grouping it throught Gid
    if transport_all_data or show_all:
        filtered_transport= filtering_func(tidyed_transport_df,asked_day, asked_hour)
        ready_to_map_transport = transport_grouping_func(filtered_transport)
        if 'status' in ready_to_map_transport.columns:
            ready_to_map_transport['status_color'] = ready_to_map_transport['status'].apply(lambda x: 'red' if (x== 'RETARD') else 'cadetblue' if (x =='HEURE') else 'green')
        else:
            print('there a bug, no status column in transport df, after grouping')
            
        tab_to_display_in_map['transport'] = ready_to_map_transport
    
    
    # return the tab for filling the map
    return tab_to_display_in_map  
     


# /******************************************* 5-  drawing my map for all vehicles: transport , vcub and trafic ********************************************************/

# 4- creating 3 function for each df

def vcub_maping_func(vcub_df):
      #  1- create à vcub cluster 
    vcub_cluster = plugins.MarkerCluster(name='vcub marker',
                                         overlay=True,
                                        control=False,
                                        icon_create_function=None)
    
    # looping throught lat and lon columns, for marker
    for index, value in vcub_df['vcub'].iterrows():
        marker_color = value['available_color']
        station_id = vcub_df['vcub'].iloc[index]['station_id']
        lat = vcub_df['vcub'].iloc[index]['lat']
        lon = vcub_df['vcub'].iloc[index]['lon']
        tooltip = '<center><b> Vcub station :</b></center>'+ str(round(value['moyenne_bikes_available'])) +' bikes left'
        
        
        marker = folium.Marker(location=[lat, lon],
                            tooltip=tooltip,
                            icon= folium.Icon(
                                    color='white',
                                    icon="bicycle", prefix='fa',
                                    icon_color=marker_color,
                                    
                                    ),
                            )
        marker.add_to(vcub_cluster)
    
    return vcub_cluster


def trafic_maping_func(trafic_df):
    thick_staus = ''
    jam_status = ''
    
    #  2 - dispatch throught status 
    for index, value in trafic_df['trafic'].iterrows():
        if value['status'] == 'EMBOUTEILLE': 
            trafic_info ='<center><b> Trafic Info :</b></center>'+ 'embouteillage'
            jam_status =folium.Marker(location=[value['lat'],value['lon']],
                            tooltip=trafic_info,
                                icon=folium.Icon(
                                    color='red',
                                    icon_color='white',
                                    icon='car',
                                    prefix='fa'
                                )
                            )
            
        if value['status'] == 'DENSE': 
            trafic_info ='<center><b> Trafic Info :</b></center>'+ 'dense'
            thick_staus = folium.Marker(location=[value['lat'],value['lon']],
                            tooltip=trafic_info,
                                icon=folium.Icon(
                                    color='orange',
                                    icon_color='white',
                                    icon='car',
                                    prefix='fa'
                                )
                            )
            
    return [jam_status, thick_staus]


def transport_maping_func(transport_df):
    # 3- add a bus cluster for more visibility 
    bus_cluster = plugins.MarkerCluster(name='bus_marker',
                                            overlay=True,
                                            control=False,
                                            icon_create_function=None)
    
    # looping throught lat and lon columns, for marker
    for index, value in transport_df['transport'].iterrows():
        lat = value['lat']
        lon = value['lon']
        terminus = '<center><b>'+ value['vehicule']+'</b></center>'+'<em>terminus: '+value['terminus'] +'</em>'
        marker_color = value['status_color']
        icon_sign = value['symbole']
        
        bus_marker = folium.Marker(location=[lat,lon],
                    tooltip=terminus,
                    icon= folium.Icon(color='white',
                                        icon=icon_sign,
                                        prefix='fa',
                                        icon_color=marker_color
                                        )
                    )
        bus_marker.add_to(bus_cluster)
            
    return bus_cluster
            

def maping_func(dataframe):
    response=''
    if len(dataframe) > 0:
        for key in dataframe.keys():
            if dataframe[key].empty == True:
                response = f'sorry, no data at the choosen time for {key}'
                continue
            else:
                first_not_empty_key = key
                lat_mean = dataframe[first_not_empty_key]['lat'].mean()
                lon_mean = dataframe[first_not_empty_key]['lon'].mean()
                break
    else:
        return 'sorry, but your dictionnary contains no data, please check the filter section'
        
      
    # creeating my map
    if 'lat_mean' not in locals() or 'lon_mean' not in locals():
        response = 'sorry, no data at the choosen time'
        return response
    else:
        final_map = folium.Map(location = [get_lat_lon()[0],get_lat_lon()[1]],
                        width=750, 
                        height=500,
                        zoom_start=15)
    
    #  1- create à vcub cluster 
    # check first if the category is in the dict
    if ('vcub' in dataframe.keys()) and (dataframe['vcub'].empty == False):
        
        vcub_cluster = vcub_maping_func(dataframe) 
        vcub_cluster.add_to(final_map)
  
    
    #  2 - dispatch throught status 
    # check first if the category is  in the dict
    if ('trafic' in dataframe.keys()) and dataframe['trafic'].empty == False:
        trafic_status = trafic_maping_func(dataframe)
        
        if trafic_status == object:
            for trf_sts in trafic_status:
                trf_sts.add_to(final_map)
        else:
            pass

    # 3- add a bus cluster for more visibility 
    # check first if the category is  in the dict
    if ('transport' in dataframe.keys()) and dataframe['transport'].empty == False:
        bus_cluster = transport_maping_func(dataframe)
        bus_cluster.add_to(final_map)
    
   
    #add user position
    folium.Marker(
        location=[get_lat_lon()[0],get_lat_lon()[1]],
        popup = folium.Popup ('vous êtes ici', max_width=300, show= True),
        icon=folium.Icon(icon='info-sign')).add_to(final_map)
    
    
    
    folium.Circle(radius = 500, location = ([get_lat_lon()[0],get_lat_lon()[1]]), fill_color = 'red').add_to(final_map)

    
    return final_map


# In[88]:
col1,col2,col3 = st.columns(3)

with col1:
    bike = st.checkbox(':bike:')
with col2:
    car = st.checkbox(':car:')
with col3:
    public_transport = st.checkbox(':tram:')

if bike:
    tab_to_display_in_map = calling_filtering_func(False,True,False,False,day,start_time)
    final_map = maping_func(tab_to_display_in_map)
    st_data = st_folium(final_map, width=725)

elif car:
    tab_to_display_in_map = calling_filtering_func(False,False,True,False,day,start_time)
    final_map = maping_func(tab_to_display_in_map)
    st_data = st_folium(final_map, width=725)

elif public_transport:
    tab_to_display_in_map = calling_filtering_func(False,False,False,True,day,start_time)
    final_map = maping_func(tab_to_display_in_map)
    st_data = st_folium(final_map, width=725)

else:
    tab_to_display_in_map = calling_filtering_func(True,False,False,False,day,start_time)   
    final_map = maping_func(tab_to_display_in_map)
    st_data = st_folium(final_map, width=725)
   