import logging
import numpy as np
import pandas as pd
from PIL import Image
import streamlit as st


def data_ingestion(uploaded_files):
    df = pd.DataFrame()
    for i in uploaded_files:
        df_temp = pd.read_excel(i, engine='openpyxl')
        df = pd.concat([df, df_temp], axis=0, ignore_index=True)
    df.drop_duplicates(keep='last', inplace=True)        
    return df


def data_treatment(df):
    # Datatype
    dict_dtype = {'credito_ou_debito': str,
                  'data': str,
                  'tp_movimento': str,
                  'ativo': str,
                  'instituicao': str,
                  'qt_abs': float,
                  'preco_mov': float,
                  'vl_total_abs': float}
    
    df.columns = list(dict_dtype.keys())
    df['preco_mov'].replace('-', 0, inplace=True)
    df['vl_total_abs'].replace('-', 0, inplace=True)
    df = df.astype(dict_dtype)
    df['data'] = pd.to_datetime(df['data'], format='%d/%m/%Y')

    # (geral) Nova variável: classificação do ativo.
    df['tp_ativo'] = np.select(
        [
            (df['ativo'].str.upper()).str.contains('TESOURO'),
            df['ativo'].str.split(' - ', 0).str[0].str.len() == 5,
            df['ativo'].str.split(' - ', 0).str[0].str.len() == 6,
            df['ativo'].str.contains('DEB'),
            df['ativo'].str.contains('|'.join(['CDB', 'RDB', 'LCA', 'LCI']))
        ],
        [
            'Tipo 1: tesouro',
            'Tipo 2: ações',
            'Tipo 3: BDR',
            'Tipo 4: debêntures',
            'Tipo 5: renda fixa privada'
        ],'?'
    )

    # (geral) Nova variável: ticker.
    df['ticker'] = np.select(
        [
            df['tp_ativo'] == 'Tipo 4: debêntures',
            df['tp_ativo'] == 'Tipo 5: renda fixa privada'
        ],
        [   
            df['ativo'].str[5:12],
            df['ativo'].str[5:17]
        ], df['ativo'].str.split(' - ').str[0]
    )

    # (bolsa) Ajuste específico de ações: zerar a quantidade de compra/venda em caso de dividendos e juros sobre capital próprio.
    condition = df['tp_movimento'].isin(['Transferência - Liquidação', 'Bonificação em Ativos', 'Desdobro'])
    df['qt_abs'] = np.where(condition, 0, df['qt_abs'])

    # (geral) Nova variável: variação na quantidade de ativos.
    df['qt'] = df['qt_abs'] * np.where(df['credito_ou_debito'] == 'Credito', 1, -1)

    # (geral) Nova variável: variação na quantidade no valor total.
    df['vl_total'] = df['vl_total_abs'] * np.where(df['credito_ou_debito'] == 'Credito', 1, -1)

    # (bolsa) Nova variável: flag se a negociação é um provento (dividendo, juros sobre capital próprio ou leilão)
    df['evento'] = np.select(
        [
            df['tp_movimento'].isin(['Dividendo', 'Juros Sobre Capital Próprio', 'Fração em Ativos', 'Leilão de Fração']),
            df['tp_movimento'].isin(['Bonificação em Ativos']),
            df['tp_movimento'].isin(['Desdobro', 'Grupamento', ]),
            df['tp_movimento'].isin(['Transferência - Liquidação', 'Compra', 'Venda', 'COMPRA / VENDA', 'COMPRA/VENDA DEFINITIVA/CESSAO']),
            df['tp_movimento'].isin(['Cobrança de Taxa Semestral', 'Atualização'])
        ],
        [
            'dividendo_ou_jcp',
            'bonificacao',
            'split',
            'compra_ou_venda',
            'outros'
        ],
        '?')
    return df


def only_tesouro(df):
    df = df.groupby(['tp_ativo','ticker','data']).agg({'qt':'sum', 'vl_total':'sum'}).reset_index()
    df['preco_mov'] = np.where(df['qt'] != 0, round(df['vl_total'] / df['qt'], 2), 0)
    df = df.loc[df['tp_ativo'] == 'Tipo 1: tesouro'].sort_values(by=['ticker','data'], ascending=True)
    df = df[['data', 'ticker', 'qt', 'preco_mov', 'vl_total']]
    return df


def only_bolsa(df):
    df = df.loc[(df['tp_ativo'] == 'Tipo 2: ações') | (df['tp_ativo'] == 'Tipo 3: BDR')].sort_values(by=['ticker','data'], ascending=True)
    df = df[['data', 'ticker', 'tp_movimento', 'evento', 'qt', 'preco_mov', 'vl_total']]
    df = df.groupby(['data', 'ticker','evento']).agg({'qt':'sum', 'vl_total':'sum'}).reset_index(drop=False)
    return df
    

def main():    
    # Definindo configuração de logs
    level = logging.DEBUG
    fmt = '[%(levelname)s] %(asctime)s - %(message)s'
    logging.basicConfig(level=level, format=fmt, datefmt='%d-%b-%y %H:%M:%S')
    
    ########
    # HOME #
    ########
    st.header('Reporte Financeiro [B]³ 📈🐕')
    st.write('Olá! Seja bem-vindo ao seu planejador pessoal de investimentos.')
    st.write('Para começar, carregue seus relatórios obtidos na B3. Não se preocupe, pois nenhum dado é gravado.')

    # Acompanhador do status de carregamento dos relatórios da B3.
    if 'import_state' not in st.session_state:
        st.session_state['import_state'] = 'empty'

    def change_import_state():
        st.session_state['import_state'] = 'processing'

    uploaded_files = st.file_uploader("Carregue o(s) relatório(s)",
                                    accept_multiple_files=True,
                                    on_change=change_import_state)
    

    if st.session_state['import_state'] == 'processing':
        try: 
            #st.success('Carregamento concluído.')
            df = data_ingestion(uploaded_files)
            df = data_treatment(df)
        except:
            st.session_state['import_state'] = 'empty'
            st.warning('Sem arquivos com layout válido.')
            logging.debug('Layout do arquivo inesperado.')
        else:
            #st.write(f"")
            st.success(f"Dados carregados.")
            st.session_state['tesouro'] = only_tesouro(df)
            st.session_state['bolsa'] = only_bolsa(df)
            st.session_state['import_state'] = 'ready'


    # Guia passo-a-passo para importar relatórios da B3.
    st.markdown('---')
    st.subheader('Saiba como exportar relatórios da B3')
    st.write('')
    st.markdown("Passo 1: Faça o login na área do investidor clicando no [site](https://www.investidor.b3.com.br/) da B3.")
    st.image(Image.open('src/fig/pag0.PNG'), caption='')
    st.write('')
    st.markdown("Passo 2: Acesse o Menu no lado esquerdo superior.")
    st.image(Image.open('src/fig/pag1.PNG'), caption='')
    st.write('')
    st.markdown("Passo 3: Selecione Extratos.")
    st.image(Image.open('src/fig/pag2.PNG'), caption='')
    st.write('')
    st.markdown("Passo 4: Clique em Movimentação e depois no botão Filtrar em amarelo .")
    st.image(Image.open('src/fig/pag3.PNG'), caption='')
    st.write('')
    st.markdown("Passo 5: Selecione o intervalo desejado (dica: o filtro aceita no máximo 12 meses. A sugestão é filtrar de 01/jan até 31/dez).")
    st.image(Image.open('src/fig/pag4.PNG'), caption='')
    st.write('')
    st.markdown("Passo 6: Clique em Extrair no formato excel.")
    st.image(Image.open('src/fig/pag5.PNG'), caption='')
    st.write('')
    st.markdown("Passo 7: Certifique-se que os arquivos tenham o formato acima.")
    st.image(Image.open('src/fig/pag6.PNG'), caption='')
    

if __name__ == '__main__':
    main()