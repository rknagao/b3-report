import json
import pandas as pd
import os

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