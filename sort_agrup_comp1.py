import streamlit as st
import pandas as pd
import numpy as np
from collections import defaultdict
import unicodedata
import io

st.title("Distribuição de Agrupamentos")

# Função para normalizar textos (remover acentos, espaços extremos e converter para maiúsculas)
def normalize_text(text):
    text = str(text).strip().upper()
    return ''.join(c for c in unicodedata.normalize('NFD', text)
                   if unicodedata.category(c) != 'Mn')

# ----------------------------
# 1. Carregar e Processar Compradores
# ----------------------------
uploaded_compradores = st.file_uploader("Selecione o arquivo exportacao_painel_compradores_s1", type=['xlsx'], key="compradores")
if uploaded_compradores is not None:
    compradores_df = pd.read_excel(uploaded_compradores)
    compradores_df.columns = compradores_df.columns.str.strip().str.upper()
    compradores_df = compradores_df.dropna(subset=["COMPRADOR"])
    # Normaliza os nomes dos compradores
    compradores_df["COMPRADOR"] = compradores_df["COMPRADOR"].apply(normalize_text)
    
    obrigatorias = ["COMPRADOR", "PRODUÇÃO QTD. ITENS TOTAL", "QTD. RC_ITEM", "TMC GMP", "QTD. GMP EM ANDAMENTO"]
    for col in obrigatorias:
        if col not in compradores_df.columns:
            st.error(f"A coluna '{col}' não foi encontrada.")
            st.stop()
    
    compradores_df["PDT"] = compradores_df["PRODUÇÃO QTD. ITENS TOTAL"].fillna(0)
    compradores_df["QIC"] = compradores_df["QTD. RC_ITEM"].fillna(0)
    compradores_df["TMC"] = compradores_df["TMC GMP"].fillna(0)
    compradores_df["GMP"] = compradores_df["QTD. GMP EM ANDAMENTO"].fillna(0)
    compradores_df["TOTAL_BASE"] = compradores_df["PDT"] + compradores_df["QIC"]
else:
    st.info("Carregue o arquivo exportacao_painel_compradores_s1.")
    st.stop()

# ----------------------------
# 2. Carregar e Processar Agrupamentos (XRA)
# ----------------------------
uploaded_xra = st.file_uploader("Selecione o arquivo XRA/XQH", type=['xlsx'], key="xra")
if uploaded_xra is not None:
    xra_df = pd.read_excel(uploaded_xra)
    xra_df.columns = xra_df.columns.str.strip().str.upper()
    
    # Identifica a coluna que contenha "ACOMPANHAMENTO" e renomeia para "NUM_ACOMPANHAMENTO"
    coluna_acomp = None
    for col in xra_df.columns:
        if "ACOMPANHAMENTO" in col:
            coluna_acomp = col
            break
    if coluna_acomp is None:
        st.error("Coluna referente ao 'Nº ACOMPANHAMENTO' não encontrada.")
        st.stop()
    else:
        xra_df = xra_df.rename(columns={coluna_acomp: "NUM_ACOMPANHAMENTO"})
    
    xra_df = xra_df.dropna(subset=["NUM_ACOMPANHAMENTO"])
    xra_df["NUM_ACOMPANHAMENTO"] = xra_df["NUM_ACOMPANHAMENTO"].apply(normalize_text)
    
    # Define a função para prioridade: agrupamentos com "EA" > "PID" > demais
    def get_weight(valor):
        texto = str(valor).upper()
        if "EA" in texto:
            return 3
        elif "PID" in texto:
            return 2
        else:
            return 1
    xra_df["PESO"] = xra_df["NUM_ACOMPANHAMENTO"].apply(get_weight)
    xra_df["TIPO"] = xra_df["NUM_ACOMPANHAMENTO"].apply(lambda x: "PREG" if "PREG" in str(x).upper() else "OUTRO")
    
    # Obter códigos únicos e contagem de ocorrências
    groupings_unique = xra_df["NUM_ACOMPANHAMENTO"].unique().tolist()
    grouping_count = xra_df.groupby("NUM_ACOMPANHAMENTO").size().to_dict()
else:
    st.info("Carregue o arquivo XRA/XQH.")
    st.stop()
    
# ----------------------------
# 3. Carregar e Processar Controle Processos Publicação SCOMP2 (Opcional)
# ----------------------------
uploaded_controle = st.file_uploader("Selecione o arquivo Controle Processos Publicação SCOMP1 (opcional)", type=['xlsx'], key="controle")
controle_dict = {}
if uploaded_controle is not None:
    # Lê o Excel considerando que a linha 2 contém os títulos (header=1)
    controle_df = pd.read_excel(uploaded_controle)
    # Normaliza os nomes das colunas
    controle_df.columns = [normalize_text(col) for col in controle_df.columns]
    # Se necessário, remova espaços extras e garanta que os cabeçalhos estejam em maiúsculas
    controle_df.columns = controle_df.columns.str.strip().str.upper()
    
    # Verifica se existe a coluna "CONTRATADOR" e, se não, tenta usar "COMPRADOR"
    if "CONTRATADOR" in controle_df.columns:
        group_col = "CONTRATADOR"
    elif "COMPRADOR" in controle_df.columns:
        group_col = "COMPRADOR"
    else:
        st.error("Nem a coluna 'CONTRATADOR' nem 'COMPRADOR' foram encontradas no arquivo de controle.")
        st.stop()
    
    # Processa a coluna escolhida: normaliza e remove os 6 últimos caracteres (para manter somente o nome do comprador)
    controle_df[group_col] = controle_df[group_col].apply(lambda x: normalize_text(x)[:-6])
    
    # Filtrar linhas: manter somente as linhas onde a coluna "GMP" esteja vazia (se existir)
    if "GMP" in controle_df.columns:
        controle_df = controle_df[controle_df["GMP"].isna() | (controle_df["GMP"] == "")]
    else:
        st.warning("A coluna 'GMP' não foi encontrada no arquivo de controle. Pulando o filtro de GMP.")
    
    # Excluir linhas com "CANCELADOS" na coluna "EDITAL E GMC"
    if "EDITAL E GMC" in controle_df.columns:
        controle_df = controle_df[~controle_df["EDITAL E GMC"].str.contains("CANCELADO", na=False)]
    else:
        st.warning("A coluna 'EDITAL E GMC' não foi encontrada no arquivo de controle. Pulando este filtro.")
    
    # Converter "QUANTIDADE DE LINHAS" para numérico, preenchendo valores ausentes com 0
    if "QUANTIDADE DE LINHAS" in controle_df.columns:
        controle_df["QUANTIDADE DE LINHAS"] = pd.to_numeric(controle_df["QUANTIDADE DE LINHAS"], errors='coerce').fillna(0)
    else:
        st.warning("A coluna 'QUANTIDADE DE LINHAS' não foi encontrada no arquivo de controle.")
    
    # Agrupar por comprador (usando a coluna group_col) e somar as quantidades para formar QEP
    controle_dict = controle_df.groupby(group_col)["QUANTIDADE DE LINHAS"].sum().to_dict()
else:
    controle_dict = {}






# ----------------------------
# 4. Preparar Dados para Distribuição Heurística
# ----------------------------
# Lista única de compradores (já normalizados)
unique_compradores = sorted(set(compradores_df["COMPRADOR"]))

# Para agrupamentos do tipo PREG, apenas compradores autorizados podem receber
# Retirada aqui a condição de compradores de PREGÃO

# Para cada comprador, calcular parâmetros: target_qp, shortfall, etc.
buyers_info = {}
for idx, row in compradores_df.iterrows():
    buyer = row["COMPRADOR"]
    QIC = row["QIC"]
    PDT = row["PDT"]
    TMC = row["TMC"]
    GMP = row["GMP"]
    QEP = controle_dict.get(buyer, 0)
    elegivel = (TMC <= 160) or (GMP <= 16)  # ou outro critério se desejado
    target_qp = 15
    if (PDT + QIC + QEP) >= 120:
        target_qp = min(target_qp, 2)
    # Limitar target_qp a no máximo 15
    target_qp = min(target_qp, 15)
    shortfall = max(0, 120 - (PDT + QIC + QEP))
    buyers_info[buyer] = {
        "PDT": PDT,
        "QIC": QIC,
        "TMC": TMC,
        "GMP": GMP,
        "QEP": QEP,
        "target_qp": target_qp,
        "shortfall": shortfall,
        "elegivel": elegivel,
        "allocated": 0  # itens alocados (QP) inicial
    }

# Filtrar compradores elegíveis
eligible_buyers = {buyer: info for buyer, info in buyers_info.items() if info["elegivel"]}

# Ordenar agrupamentos por prioridade: primeiro pelo peso e depois pelo maior número de ocorrências
sorted_groupings = sorted(groupings_unique, key=lambda g: (get_weight(g), grouping_count[g]), reverse=True)

# ----------------------------
# 5. Algoritmo de Distribuição Greedy (sem distinção PREG)
# ----------------------------
allocation_result = defaultdict(list)

for g in sorted_groupings:
    candidates = []
    for buyer, info in eligible_buyers.items():
        # Verifica se o comprador ainda pode receber mais agrupamentos
        if info["allocated"] < min(info["target_qp"], 15):
            candidates.append(buyer)

    if not candidates:
        continue

    # Seleciona o candidato com maior shortfall (deficit para atingir a meta)
    selected = max(candidates, key=lambda b: eligible_buyers[b]["shortfall"])
    allocation_result[selected].append(g)
    eligible_buyers[selected]["allocated"] += grouping_count[g]
    eligible_buyers[selected]["shortfall"] = max(
        0,
        120 - (
            eligible_buyers[selected]["PDT"]
            + eligible_buyers[selected]["QIC"]
            + eligible_buyers[selected]["allocated"]
        )
    )

# ----------------------------
# 6. Consolidação dos Resultados
# ----------------------------
results = []
for buyer in unique_compradores:
    row = compradores_df[compradores_df["COMPRADOR"] == buyer].iloc[0]
    # qp_allocated: total de itens atribuídos (somando as ocorrências dos agrupamentos)
    qp_allocated = eligible_buyers[buyer]["allocated"] if buyer in eligible_buyers else 0
    # QEP: valor do Controle Processos Publicação SCOMP2, se existir; caso contrário 0.
    QEP = controle_dict.get(buyer, 0)
    TGI = row["PDT"] + row["QIC"] + qp_allocated + QEP
    results.append({
        "Comprador": buyer,
        "Agrupamentos": ", ".join(allocation_result.get(buyer, [])),
        "QP (Itens Atribuídos)": qp_allocated,
        "QIC Base": row["QIC"],
        
        "GMP Base": row["GMP"],
        "Total GMP": row["GMP"] + len(allocation_result.get(buyer, [])),  # cada agrupamento vale 1 GMP
        "TMC": row["TMC"],
        "Total QIC": row["QIC"] + qp_allocated,
        "PDT": row["PDT"],
        "QEP": QEP,
        "TGI (QIC+PDT+QEP)": TGI,
        "Desvio": TGI - 120
    })

results_df = pd.DataFrame(results)
# 1) Identifica automaticamente todas as colunas numéricas, exceto 'TMC'
numeric_cols = results_df.select_dtypes(include='number').columns.tolist()
numeric_cols.remove('TMC')

# 2) Monta o dicionário de formatos:
fmt = {col: '{:.0f}' for col in numeric_cols}  # zero decimais
fmt['TMC'] = '{:.1f}'                          # uma casa decimal

# 3) Exibe com o Styler:
st.dataframe(
    results_df.style.format(fmt)
)

st.title("Resultados da Distribuição")
st.write("A coluna 'Agrupamentos' exibe os códigos distribuídos a cada comprador. A coluna 'QEP' vem do Controle Processos Publicação SCOMP2 (se fornecido).")

total_faltante = sum(-row["Desvio"] for idx, row in results_df.iterrows() if row["Desvio"] < 0)
if total_faltante > 0:
    st.markdown(f"**Faltam {total_faltante} itens para que todos atinjam a meta de 120 itens.**")
else:
    st.markdown("**Todos os compradores atingiram a meta mínima de 120 itens.**")

results_df = pd.DataFrame(results)  # "results" pode ser o nome da lista de resultados consolidados

def convert_df_to_excel(df):
    output = io.BytesIO()  # Cria um buffer em memória
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name='Resultados')
    processed_data = output.getvalue()
    return processed_data

excel_data = convert_df_to_excel(results_df)

st.download_button(
    label="Baixar Resultados em Excel",
    data=excel_data,
    file_name='resultados_distribuicao.xlsx',
    mime='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
)
