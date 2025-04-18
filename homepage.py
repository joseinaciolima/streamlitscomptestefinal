import streamlit as st


# containers
# columns

secao_usuario = st.session_state
nome_usuario = None
if "username" in secao_usuario:
    nome_usuario = secao_usuario.name

coluna_esquerda, coluna_direita = st.columns([1, 1])

coluna_esquerda.title("Time SCOMP")
if nome_usuario:
    coluna_esquerda.write(f"#### Bem vindo, {nome_usuario}") # markdown
botao_sorteador = coluna_esquerda.button("Distribuir GCOMP")
botao_sort_agrupamentos = coluna_esquerda.button("Distribuir SCOMP-1")
botao_sort_agrup_comp = coluna_esquerda.button("Distribuir SCOMP-2")



if botao_sorteador:
    st.switch_page("sort_agrup_gcomp.py")
if botao_sort_agrupamentos:
    st.switch_page("sort_agrup_comp1.py")
if botao_sort_agrup_comp:
    st.switch_page("sort_agrup_comp.py")


container = coluna_direita.container(border=False)
container.image("imagens/croupier.webp")
