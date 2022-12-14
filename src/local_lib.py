import json
import numpy as np
import pandas as pd
import os
import streamlit as st

def etl_historic_price_tesouro(df_right):
    # To download historic prices of Tesouro Direto (i.e. brazillian T-Bonds). 
    # Extração
    url = 'https://www.tesourotransparente.gov.br/ckan/dataset/df56aa42-484a-4a59-8184-7676580c81e3/resource/796d2059-14e9-44e3-80c9-2d9e30b405c1/download/PrecoTaxaTesouroDireto.csv'
    df_left = pd.read_csv(url, sep=';', decimal=',')

    # Transformação
    df_left['data'] = pd.to_datetime(df_left['Data Base'], dayfirst=True).dt.date
    df_left['ticker'] = df_left['Tipo Titulo'].astype(str) + ' ' + df_left['Data Vencimento'].str[6:]
    df_left = df_left.loc[(df_left['ticker'].isin(df_right['ticker'].unique())) &
                          (df_left['data'] >= df_right['data'].min())].sort_values(by=['ticker','data'], ascending=True)
    df_left.rename(columns={'PU Base Manha':'preco'}, inplace=True)
    df_left['preco'] = round(df_left['preco'].astype(float), 2)

    df_merge = pd.merge(df_left[['data', 'ticker', 'preco']],
                        df_right,
                        on=['data','ticker'],
                        how='left').fillna(0)

    # Cálculo do valor acumulado.
    for i in df_right['ticker'].unique():
        df_merge.loc[df_merge['ticker'] == i, 'qt_acum'] = df_merge.loc[df_merge['ticker'] == i, 'qt'].cumsum(skipna=True)
        df_merge = df_merge.loc[df_merge['qt_acum'] != 0]
        df_merge['vl_atualizado'] = (df_merge['qt_acum'] * df_merge['preco']).round(2)

    return df_merge
    

def create_column_last_day(df_orig, col_index, col_date):
    # Criando nova coluna identificando o último dia do mês para cada ticker.
    
    df_left = df_orig
    
    df_right = df_orig[[col_index, col_date]]
    df_right['year'] = pd.to_datetime(df_right[col_date]).dt.year
    df_right['month'] = pd.to_datetime(df_right[col_date]).dt.month
    df_right['day'] = pd.to_datetime(df_right[col_date]).dt.day
    df_right = df_right.groupby([col_index,'year','month']).agg({'day':'max'}).reset_index(drop=False)
    df_right[col_date] = pd.to_datetime(df_right[['year', 'month', 'day']]).dt.date
    df_right.drop(columns=['year', 'month', 'day'], inplace=True)
    df_right['dummy_ultimo_dia'] = 1

    df_merge = pd.merge(df_left, df_right, on=[col_index, col_date], how='left').fillna(0)
    df_merge['data_competencia'] = [i.replace(day=1) for i in df_merge['data']]

    return df_merge



def custom_pivot_table(df, col_value):

    assert [i in df.columns.tolist() for i in ['ticker','data_competencia']]
    
    tab = pd.pivot_table(df,
                         values=[col_value],
                         columns=['data_competencia'],
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