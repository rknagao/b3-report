from datetime import datetime
import json
import numpy as np
import pandas as pd
from PIL import Image
import os
import streamlit as st
#import local_lib as ll


############
## FRONT  ##
############

st.header('B3 Report - Personal Investment')

if 'import_state' not in st.session_state:
    st.session_state['import_state'] = 'empty'

def change_import_state():
    st.session_state['import_state'] = 'processing'
    st.success('Carregamento concluído.')
    
uploaded_files = st.file_uploader("Carregue o(s) relatório(s)",
                                  accept_multiple_files=True,
                                  on_change=change_import_state)

st.markdown("#### Como extrair os relatórios da B3?")
st.markdown("Acesse o [site](https://www.investidor.b3.com.br/) da B3 e faça o login na área de investidor.")

st.image(Image.open('src/fig/pag1.PNG'), caption='Passo 1: após o login, acesse o Menu no lado esquerdo superior.', width=800)
st.write('')
st.image(Image.open('src/fig/pag2.PNG'), caption='Passo 2: acesse os Extratos.', width=800)
st.write('')
st.image(Image.open('src/fig/pag3.PNG'), caption='Passo 3: clique em Movimentação e depois no botão amarelo Filtrar .', width=800)
st.write('')
st.image(Image.open('src/fig/pag4.PNG'), caption='Passo 4: selecione o filtro desejado (dica: use o ano civil, ou seja, 01/jan até 31/dez).', width=800)
st.write('')
st.image(Image.open('src/fig/pag5.PNG'), caption='Passo 5: clique em Extrair no formato excel.', width=800)
st.write('')
st.image(Image.open('src/fig/pag6.PNG'), caption='Certifique-se que os arquivos tenham o formato acima.', width=800)

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
        df = pd.read_excel(i)

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
                  'preco_mov': float,
                  'vl_total_abs': float}

    df_all.columns = list(dict_dtype.keys())
    df_all['preco_mov'].replace('-', 0, inplace=True)
    df_all['vl_total_abs'].replace('-', 0, inplace=True)
    df_all = df_all.astype(dict_dtype)
    df_all['data'] = pd.to_datetime(df_all['data'], format='%d/%m/%Y')
    
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

    # (f) Unificar múltiplas compras/vendas em diferentes corretoras.
    # Essa etapa necessariamente é a última, pois aplicaremos cálculo sobre quantidade e preço.
    # Ao final, teremos o preço médio de compras/venda 
    # tp_movimento foi removido pois podem haver compras e vendas o mesmo dia (caso de daytrade)
    df_all = df_all.groupby(['tp_ativo','ticker','data']).agg({'qt':'sum', 'vl_total':'sum'}).reset_index(drop=False)
    df_all['preco_mov'] = np.where(df_all['qt'] != 0, round(df_all['vl_total'] / df_all['qt'], 2), 0)
    return df_all


def only_tesouro(df):
    df = df.loc[df['tp_ativo'] == 'Tipo 1: tesouro'].sort_values(by=['ticker','data'], ascending=True)
    return df[['data', 'ticker', 'qt', 'preco_mov', 'vl_total']]


if st.session_state['import_state'] == 'processing':
    df_all = etl(uploaded_files)
    st.session_state['tesouro'] = only_tesouro(df_all)
    st.session_state['import_state'] = 'ready'
