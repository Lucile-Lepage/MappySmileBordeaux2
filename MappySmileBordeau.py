# -*- coding: utf-8 -*-
"""
Created on Thu Dec  1 11:28:54 2022

@author: Lucile Lepage
"""

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
    menu_icon="cast", default_index=0, orientation="horizontal")
 
  
st.image('bordeaux.gif')
 