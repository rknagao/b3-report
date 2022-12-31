import logging
import pandas as pd
import streamlit as st
import yfinance as yf

#@st.cache
def tesouro():
    url = 'https://www.tesourotransparente.gov.br/ckan/dataset/df56aa42-484a-4a59-8184-7676580c81e3/resource/796d2059-14e9-44e3-80c9-2d9e30b405c1/download/PrecoTaxaTesouroDireto.csv'
    df = pd.read_csv(url, sep=';', decimal=',')
    df['data'] = pd.to_datetime(df['Data Base'], format='%d/%m/%Y')
    df['ticker'] = df['Tipo Titulo'].astype(str) + ' ' + df['Data Vencimento'].str[6:]
    df['preco_hist'] = round(df['PU Base Manha'].astype(float), 2)
    df = df[['data','ticker','preco_hist']]
    return df


#@st.cache
def cdi():
    df = pd.read_json('http://api.bcb.gov.br/dados/serie/bcdata.sgs.12/dados?formato=json')
    df['data'] = pd.to_datetime(df['data'], format='%d/%m/%Y')
    df.columns = ['data','cdi']
    return df


#@st.cache
def ipca():
    df = pd.read_json('http://api.bcb.gov.br/dados/serie/bcdata.sgs.433/dados?formato=json')
    df['data'] = pd.to_datetime(df['data'], format='%d/%m/%Y')
    df.columns = ['data','ipca']
    df['ipca'] = round((1 + df['ipca']) ** (1/22) - 1, 6)
    return df


#@st.cache
def ibovespa():
    df = yf.download('^BVSP', interval='1d')['Adj Close'].reset_index(drop=False)
    df.columns = ['data','ibov']
    df['ibov'] = ((df['ibov'] / df['ibov'].shift(1) - 1) * 100).fillna(0).round(6)
    return df        


#@st.cache
def sp500():
    df = yf.download('^GSPC', interval='1d')['Adj Close'].reset_index(drop=False)
    df.columns = ['data','sp500']
    df['sp500'] = ((df['sp500'] / df['sp500'].shift(1) - 1) * 100).fillna(5).round(6)
    return df        

    """
    df_final = pd.merge(df_ibov, df_sp500, on='data', how='inner')
    df_final = pd.merge(df_final, df_cdi, on='data', how='inner')
    df_final = pd.merge(df_final, df_ipca, on='data', how='left')
    df_final['ipca'] = df_final['ipca'].fillna(method='ffill')
    df_final['data'] = pd.to_datetime(df_final['data'])

    return df_final
    """