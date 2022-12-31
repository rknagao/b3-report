import altair as alt
import numpy as np
import pandas as pd
import streamlit as st


def pivot_table(df, x, y, value):
    
    # Ajuste para o formato de data no Streamlit.
    if np.issubdtype(df[x].dtype, np.datetime64):
        df[x] = pd.to_datetime(df[x]).dt.date

    pv = pd.pivot_table(df,
                        values=[value],
                        columns=[x],
                        index=[y],
                        aggfunc='sum',
                        margins=True,
                        margins_name='Total',
                        observed=True
                        ).astype(float)\
                         .fillna(0)\
                         .round(2)\
                         .iloc[:, :-1]
     
    list_col = [i[1] for i in pv.columns]
    pv.columns = [f"{i.strftime('%B')}/{i.year}" for i in list_col]
    pv.reset_index(drop=False, inplace=True)
    data_col=pv.columns[1:].tolist()
    st.dataframe(pv.style.format(subset=data_col, formatter="{:.2f}"))

    

#def lineplot(df, title: str, col_date: str, col_value: str, col_label: str ):
def lineplot(df, x, y, label, title):

    alt.themes.enable("streamlit")
    df['x_lag'] = df[x].shift(-1)
    
    hover = alt.selection_single(
        fields=[x],
        nearest=True,
        on="mouseover",
        empty="none",
    )

    lines = (
        alt.Chart(df, height=500)
        .mark_line()
        .encode(
            x=alt.X(x, title="Data"),
            y=alt.Y(y, title="Valor total (R$)"),
            color=alt.Color(label, title='Legenda')
        )
    )

    # Draw points on the line, and highlight based on selection
    points = lines.transform_filter(hover).mark_circle(size=90)

    # Draw a rule at the location of the selection
    tooltips = (
        alt.Chart(df)
        .mark_rule()
        .encode(
            x=f"yearmonthdate({x})",
            y=y,
            opacity=alt.condition(hover, alt.value(0.3), alt.value(0)),
            tooltip=[
                alt.Tooltip("yearmonthdate(x_lag)", title="Data"),
                alt.Tooltip(label, title="Legenda"),
                alt.Tooltip(y, title="Valor (R$)"),
            ],
        )
        .add_selection(hover)
    )

    chart = (lines + points + tooltips).interactive()
    st.altair_chart(chart.interactive(), use_container_width=True)
    