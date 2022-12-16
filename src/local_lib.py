import json
import numpy as np
import pandas as pd
import os
import streamlit as st
import yfinance as yf

#@st.cache
def etl_tesouro_historic_price():
    url = 'https://www.tesourotransparente.gov.br/ckan/dataset/df56aa42-484a-4a59-8184-7676580c81e3/resource/796d2059-14e9-44e3-80c9-2d9e30b405c1/download/PrecoTaxaTesouroDireto.csv'
    df = pd.read_csv(url, sep=';', decimal=',')
    df['data'] = pd.to_datetime(df['Data Base'], format='%d/%m/%Y')
    df['ticker'] = df['Tipo Titulo'].astype(str) + ' ' + df['Data Vencimento'].str[6:]
    df['preco_hist'] = round(df['PU Base Manha'].astype(float), 2)
    return df


def merge_historic_tesouro(df_historic, df_tesouro):

    # Merge entre preços históricos e investimentos do B3.
    list_ticker = df_tesouro['ticker'].unique()
    dt_min = df_tesouro['data'].min()

    df_historic = df_historic.loc[(df_historic['ticker'].isin(list_ticker)) &
                                  (df_historic['data'] >= dt_min)].sort_values(by=['ticker','data'], ascending=True)
    
    df_tesouro_hist = pd.merge(df_historic, df_tesouro, on=['data','ticker'], how='left').fillna(0)
    
    # Cálculo do valor acumulado para cada ticker.
    for i in list_ticker:
        df_tesouro_hist.loc[df_tesouro_hist['ticker'] == i, 'qt_acum'] = df_tesouro_hist.loc[df_tesouro_hist['ticker'] == i, 'qt'].cumsum(skipna=True)
        df_tesouro_hist = df_tesouro_hist.loc[df_tesouro_hist['qt_acum'] != 0]
        df_tesouro_hist['vl_atualizado'] = (df_tesouro_hist['qt_acum'] * df_tesouro_hist['preco_hist']).round(2)

    return df_tesouro_hist


def create_column_last_day(df_orig):
    # Criando nova coluna identificando o último dia do mês para cada ticker.
    df_left = df_orig
    df_right = df_orig[['data', 'ticker']]
    
    # Identificar o maior dia dentro de um mesmo ano e mês.
    df_right['year'] = pd.to_datetime(df_right['data']).dt.year
    df_right['month'] = pd.to_datetime(df_right['data']).dt.month
    df_right['day'] = pd.to_datetime(df_right['data']).dt.day
    df_right = df_right.groupby(['ticker','year','month']).agg({'day':'max'}).reset_index(drop=False)
    df_right['data'] = pd.to_datetime(df_right[['year', 'month', 'day']])

    df_right.drop(columns=['year', 'month', 'day'], inplace=True)
    df_right['dummy_ultimo_dia'] = 1
    df_merge = pd.merge(df_left, df_right, on=['ticker', 'data'], how='left').fillna(0)
    df_merge['dt_competencia'] = [i.replace(day=1) for i in df_merge['data']]

    return df_merge



def custom_pivot_table(df, col_value):
    # Criando a tabela dinâmica (tab1).

    assert [i in df.columns.tolist() for i in ['ticker','data_competencia']]
    
    # Ajuste para o formato de data no Streamlit.
    df['dt_competencia'] = pd.to_datetime(df['dt_competencia']).dt.date

    tab = pd.pivot_table(df,
                         values=[col_value],
                         columns=['dt_competencia'],
                         index=['ticker'],
                         aggfunc='sum',
                         margins=True,
                         margins_name='Total',
                         observed=True
                         ).astype(float)\
                         .fillna(0)\
                         .round(2)
     
    list_col = [i[1] for i in tab.columns]
    tab.columns = list_col
    tab.reset_index(drop=False, inplace=True)
    data_cols=tab.columns[1:].tolist()

    return tab, data_cols


#@st.cache    
def etl_benchmark_historic_price():
    # CDI
    df_cdi = pd.read_json('http://api.bcb.gov.br/dados/serie/bcdata.sgs.12/dados?formato=json')
    df_cdi['data'] = pd.to_datetime(df_cdi['data'], format='%d/%m/%Y')
    df_cdi.columns = ['data','cdi']

    # IPCA
    df_ipca = pd.read_json('http://api.bcb.gov.br/dados/serie/bcdata.sgs.433/dados?formato=json')
    df_ipca['data'] = pd.to_datetime(df_ipca['data'], format='%d/%m/%Y')
    df_ipca.columns = ['data','ipca']
    df_ipca['ipca'] = round((1 + df_ipca['ipca']) ** (1/22) - 1, 6)

    # IBOV
    df_ibov = yf.download('^BVSP', interval='1d')['Adj Close'].reset_index(drop=False)
    df_ibov.columns = ['data','ibov']
    df_ibov['ibov'] = ((df_ibov['ibov'] / df_ibov['ibov'].shift(1) - 1) * 100).fillna(0).round(6)
        
    # S&P500
    df_sp500 = yf.download('^GSPC', interval='1d')['Adj Close'].reset_index(drop=False)
    df_sp500.columns = ['data','sp500']
    df_sp500['sp500'] = ((df_sp500['sp500'] / df_sp500['sp500'].shift(1) - 1) * 100).fillna(5).round(6)

    df_final = pd.merge(df_ibov, df_sp500, on='data', how='inner')
    df_final = pd.merge(df_final, df_cdi, on='data', how='inner')
    df_final = pd.merge(df_final, df_ipca, on='data', how='left')
    df_final['ipca'] = df_final['ipca'].fillna(method='ffill')
    df_final['data'] = pd.to_datetime(df_final['data'])

    return df_final


def merge_historic_benchmark(df_filtered, df_bench):
    # Unificar a carteira com os ticker existentes.
    df_unify = df_filtered.groupby(['data']).agg({'vl_total':'sum', 'vl_atualizado':'sum'}).reset_index(drop=False)

    # Merge com df_bench.
    df_merge = pd.merge(df_bench, df_unify, on='data', how='left') 
    df_merge = df_merge.loc[df_merge['vl_atualizado'].notnull()].reset_index(drop=True)

    return df_merge


def calculate_cumsum(array_value, array_yield):
    
    assert len(array_value) == len(array_yield)

    list_new_value = []
    list_new_value.append(array_value[0])

    for i in range(1, len(array_value)):
        last_value = list_new_value[i - 1] * (1 + array_yield[i]/100)
        new_value = round(last_value + array_value[i], 2)
        list_new_value.append(new_value)
    
    return np.array(list_new_value)


def custom_data_lineplot(df, list_bench):
    # Transformar os dados na tab2 para alimentar o gráfico de linhas.
    # Simular o valor acumulado para cada benchmark.
    for i in list_bench:
        array = calculate_cumsum(array_value=df['vl_total'], array_yield=df[i])
        df[f'vl_cumsum_{i}'] = array

    # Transformar colunas em linhas.
    df_plot = pd.melt(df,
                      id_vars='data',
                      value_vars=['vl_atualizado'] + [f'vl_cumsum_{i}' for i in list_bench],
                       )#.reset_index(drop=False)
    df_plot['data'] = pd.to_datetime(df_plot['data']).dt.date
    df_plot['data_lag'] = df_plot['data'].shift(-1)

    return df_plot



"""
class investimento:

    def __init__(self, name, config_path):
        with open(config_path, 'r') as f:
            config = json.load(f)

        self.name = name
        self.path = f"{os.getcwd()}/{config['data']['path']['clean'][name]}"
        self.dtype = config['data']['dtype'][name]
        self.config_json = config


    def hello(self):
        print(f'\nHello!\nName: {self.name}\nPath: {self.path}\nDtype: {self.dtype}\n')


    def load_data(self):
        try:    
            df = pd.read_csv(self.path, dtype=self.dtype, parse_dates=['dt_competencia', 'dt_vencimento'], dayfirst=True)
            df['dt_vencimento'] = pd.to_datetime(df['dt_vencimento']).dt.date
        except:
            df = pd.read_csv(self.path, dtype=self.dtype, parse_dates=['dt_competencia'], dayfirst=True)

        df['dt_competencia'] = pd.to_datetime(df['dt_competencia']).dt.date
        return df


    def preprocessing(self, df):
        '''
        Objetivo: centralizar os preprocessamentos necessários aos dados.
        Input:
            - df: dataframe original.
        Output:
            - df: dataframe com dados unificados.
        '''
        lista_colunas_manter = [key for (key, value) in self.config_json['data']['dtype'][self.name].items() if value == 'str']
        dict_colunas_aggfunc = {'quantidade':'sum',
                                'valor_investido':'sum',
                                'valor_atualizado':'sum'}

        #df = df.loc[df['quantidade'] > 0]
        df = df.groupby(lista_colunas_manter)\
                .agg(dict_colunas_aggfunc)\
                .reset_index(drop=False)\
                .sort_values(['ticker','dt_competencia'], ascending=True)

        return df


    def load_benchmark(self):
        try:    
            df = pd.read_csv(self.path, dtype=self.dtype, parse_dates=['dt_competencia', 'dt_vencimento'], dayfirst=True)
            df['dt_vencimento'] = pd.to_datetime(df['dt_vencimento']).dt.date
        except:
            df = pd.read_csv(self.path, dtype=self.dtype, parse_dates=['dt_competencia'], dayfirst=True)

        df['dt_competencia'] = pd.to_datetime(df['dt_competencia']).dt.date
        #df['dt_competencia'] = pd.to_datetime(df['dt_competencia']).dt.strftime("%Y-%m-%d")
        return df

    
class compare:
    def calculate_return(array_vl_invested, array_pct_var):
        '''
        Objetivo: calcular o valor presente de um fluxo de investimento.
        Input:
            - array_vl_invested: fluxo de valor investido, positivo para entrada e negativo para saída.
            - array_pct_var: variação em cada intervalo (1% = 1)
        Output:
            - ls_return: retorno.
        '''
        # Checks de sanidade.
        try:
            assert all([isinstance(i, float) for i in array_vl_invested])
            assert all([isinstance(i, float) for i in array_pct_var]) 
        except:
            print('Erro: dtype não é float.')

        try:
            assert len(array_vl_invested) == len(array_pct_var) 
        except:
            print('Erro: os arrays não tem o mesmo comprimento.')

        # Início do cálculo.
        ls_return = []
        for i in range(len(array_vl_invested)):
            print(i)
            if (i == 0):
                vl_return = array_vl_invested[i] * (1 + array_pct_var[i]/100)
            else:
                vl_return = (ls_return[-1] + array_vl_invested[i]) * (1 + array_pct_var[i]/100)

            ls_return.append(vl_return.round(2))

        return ls_return
"""