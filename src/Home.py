from datetime import datetime
import json
import numpy as np
import pandas as pd
import os
import streamlit as st
#import local_lib as ll


############
## FRONT  ##
############

st.header('B3 Report - Personal Investment 🤑')

############
## IMPORT ##
############

if 'import_state' not in st.session_state:
    st.session_state['import_state'] = 'empty'
    

def change_import_state():
    st.session_state['import_state'] = 'processing'
    st.success('Carregamento concluído.')
    
uploaded_files = st.file_uploader("Choose a file",
                                  accept_multiple_files=True,
                                  on_change=change_import_state)


def etl(uploaded_files):
    '''
    Objetivo: centralizar e tratar múltiplos arquivos carregados.
    Input:
        - uploaded_files (BytesIO ?): relatórios de movimentação extraídos da B3.
    Output:
        - df_all (dataframe): arquivos convertidos em um único dataframe. 
    '''
    # Extração.
    for i in uploaded_files:
        df = pd.read_excel(i, engine='openpyxl')

        # No primeiro caso criaremos um dataframe que consolidará todas as movimentações.
        if i == uploaded_files[0]:
            df_all = df
        else:
            df_all = pd.concat([df_all, df], axis=0, ignore_index=True)

    # Tratamentos:
    # (a) Nome e dtype.
    dict_dtype = {'credito_ou_debito': str,
                  'data': str,
                  'tp_movimento': str,
                  'ativo': str,
                  'instituicao': str,
                  'qt_abs': float,
                  'preco': float,
                  'vl_total_abs': float}

    df_all.columns = list(dict_dtype.keys())
    df_all['preco'].replace('-', 0, inplace=True)
    df_all['vl_total_abs'].replace('-', 0, inplace=True)
    df_all = df_all.astype(dict_dtype)
    df_all['data'] = pd.to_datetime(df_all['data'], format='%d/%m/%Y').dt.date
    
    # (b) Nova variável: classificação do ativo.
    df_all['tp_ativo'] = np.select(
        [
            (df_all['ativo'].str.upper()).str.contains('TESOURO'),
            df_all['ativo'].str.split(' - ', 0).str[0].str.len() == 5,
            df_all['ativo'].str.split(' - ', 0).str[0].str.len() == 6,
            df_all['ativo'].str.contains('DEB'),
            df_all['ativo'].str.contains('|'.join(['CDB', 'RDB', 'LCA', 'LCI']))
        ],
        [
            'Tipo 1: tesouro',
            'Tipo 2: ações',
            'Tipo 3: BDR',
            'Tipo 4: debêntures',
            'Tipo 5: renda fixa privada'
        ],'?'
    )

    # (c) Nova variável: ticker.
    df_all['ticker'] = np.select(
        [
            df_all['tp_ativo'] == 'Tipo 4: debêntures',
            df_all['tp_ativo'] == 'Tipo 5: renda fixa privada'
        ],
        [   
            df_all['ativo'].str[5:12],
            df_all['ativo'].str[5:17]
        ], df_all['ativo'].str.split(' - ').str[0]
    )

    # (d) Nova variável: variação na quantidade de ativos.
    df_all['qt'] = df_all['qt_abs'] * np.where(df_all['credito_ou_debito'] == 'Credito', 1, -1)

    # (e) Nova variável: variação na quantidade no valor total.
    df_all['vl_total'] = df_all['vl_total_abs'] * np.where(df_all['credito_ou_debito'] == 'Credito', 1, -1)

    # (f) Nova variável: data de competência.
    #df_all['data_ult_dia_mes'] = [i.replace(day=1) for i in df_all['data']]
    #df_all['data_ult_dia_mes'] = df['date'] + pd.tseries.offsets.MonthEnd(0)
    
    #### INCLUIR UM GROUPBY QUE SOME AS QUANTIDADES E CALCULE UM PREÇO MÉDIO
    st.write('PRECISA ARRUMAR AQUIIIIIIIIIIIIIIIIIIIIIIIIIIIII')
    return df_all


def only_tesouro(df):
    df = df.loc[df['tp_ativo'] == 'Tipo 1: tesouro'].sort_values(by=['ticker','data'], ascending=True)
    return df[['data','tp_movimento','ticker', 'qt', 'vl_total']]


if st.session_state['import_state'] == 'processing':
    df_all = etl(uploaded_files)
    st.session_state['tesouro'] = only_tesouro(df_all)
    st.session_state['import_state'] = 'ready'
    

