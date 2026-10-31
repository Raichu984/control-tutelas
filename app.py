import io
import requests
from datetime import datetime, date, timedelta
import pandas as pd
import streamlit as st
import holidays

st.set_page_config(page_title="Control de Tutelas", page_icon="⚖️", layout="wide")
st.title("⚖️ Control de Tutelas y Vencimientos")
st.info("Sistema en línea listo para sincronizar.")
