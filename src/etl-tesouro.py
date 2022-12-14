# %%
import datetime
import json
import os
import pandas as pd
from pandas.tseries.offsets import DateOffset

# %%
# Variábeis globais
with open('src/config.json', 'r') as f:
    config = json.load(f)

DATA_INTERIM = config['data']['path']['interim']['tesouro']
DATA_CLEAN = config['data']['path']['clean']['tesouro']

# %%
df = pd.read_csv(DATA_INTERIM)

# %%
# Tratamento dos dados.
# Dúvida: qual a diferença entre Quantidade e Quantidade Disponível?
dict_colunas = {
    'dt_competencia':'dt_competencia',
    'Produto':'ticker',
    'Vencimento':'dt_vencimento',
    'Indexador':'indice',
    'Quantidade':'quantidade',
    'Valor Aplicado':'valor_investido',
    'Valor Atualizado':'valor_atualizado'
}

df = df[dict_colunas.keys()].rename(columns=dict_colunas)

df.dropna(how='any', inplace=True)
df['dt_competencia'] = pd.to_datetime(df['dt_competencia'])
df['dt_vencimento'] = pd.to_datetime(df['dt_vencimento'], dayfirst=True)
df['quantidade'] = df['quantidade'].astype('float')
df['valor_investido'] = df['valor_investido'].astype('float')
df['valor_atualizado'] = df['valor_atualizado'].astype('float')
df['tipo'] = 'tesouro'
df = df.loc[df['quantidade'] > 0]


# %%
# Incluir quantidade/valor = 0 em t-1 caso o título surgiu em t:
def criar_t_menos_1(df):
    # Objetivo: criar uma data de competência contendo quantidade/valor 0.

    # Identificar os títulos e a primeira aparição.
    df_g = df.groupby(['ticker', 'dt_vencimento', 'indice', 'tipo']).agg({'dt_competencia':'min'}).reset_index(drop=False)
    
    # Criar as colunas a serem inseridas.                                                  
    df_g['dt_competencia'] = df_g['dt_competencia'] - DateOffset(months=1)
    df_g['quantidade'] = 0
    df_g['valor_investido'] = 0
    df_g['valor_atualizado'] = 0

    # Juntar tudo.
    df_final = pd.concat([df, df_g], sort=False, ignore_index=True)

    return df_final 


df = criar_t_menos_1(df)

# %%
df.to_csv(DATA_CLEAN, sep=',', encoding='utf8', index=False)


