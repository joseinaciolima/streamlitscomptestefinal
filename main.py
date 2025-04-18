import streamlit as st
import pandas as pd

st.set_page_config(
    page_title="SCOMP",  # Define o título da aba
    page_icon="imagens/logo.png"  # Caminho para o seu ícone
)

@st.cache_data
def carregar_dados():
    tabela = pd.read_excel("Base.xlsx")
    return tabela

base = carregar_dados()

    
pg = st.navigation(
    {
    "Home": [st.Page("homepage.py", title="SCOMP")],
    "Distrib_Agrupacomprador": [st.Page("sort_agrup_comp.py", title="Distribuidor AgrupaSCOMP2")],
    "Distrib_AgrupaSCOMP1": [st.Page("sort_agrup_comp1.py", title="Distribuidor AgrupaSCOMP1")],
    "Distrib_AgrupaGCOMP": [st.Page("sort_agrup_gcomp.py", title="Distribuidor AgrupaGCOMP")]
    }
)


pg.run()
