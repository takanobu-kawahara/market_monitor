# %%
import yfinance as yf
import plotly as py
import os
import pandas as pd
import plotly.graph_objects as go
import base64
from xhtml2pdf import pisa
# from IPython.display import display, HTML
import datetime
import pytz
from dateutil.relativedelta import relativedelta
DEVELOP = False

# %%

# jst = pytz.timezone('Asia/Tokyo')
kyo = datetime.datetime.today().date()
kinou = kyo - relativedelta(days=1)
senshu = kyo - relativedelta(weeks=1)
kyo,senshu = kyo.strftime("%Y-%m-%d"),senshu.strftime("%Y-%m-%d")
kinou = kinou.strftime("%Y-%m-%d")

# %%

"""
functions 
"""


def convert_html_to_pdf(source_html, output_filename):
    # open output file for writing (truncated binary)
    result_file = open(output_filename, "w+b")

    # convert HTML to PDF
    pisa_status = pisa.CreatePDF(
        source_html,                # the HTML to convert
        dest=result_file)           # file handle to recieve result

    # close output file
    result_file.close()                 # close output file

    # return True on success and False on errors
    return pisa_status.err


# %%
tickers = ['^GSPC', '^FTSE', '^HSI', '^N225',
           '^VIX',
           '^FVX', '^TNX', '^TYX',
           'BTC-USD', 'ETH-USD']

# %%
if DEVELOP and os.path.exists("./dled_data.csv"):
    data = pd.read_csv("./dled_data.csv", header=[0, 1],
                       skipinitialspace=True, index_col=0,
                       parse_dates=[0])
else:
    data = yf.download(
        tickers=' '.join(tickers),
        period='5d',
        # start = senshu, end = kyo,
        interval='15m',
        group_by='ticker',
        auto_adjust=True,
    )
    data.to_csv("./dled_data.csv")

fetchd_tickers = data.columns.get_level_values(0).drop_duplicates()
data.iloc[:5, :5]

# %%

figures = []
for ft in tickers:
    df = data[[ft]].droplevel(0, axis=1)
    df = df[['Open', 'High', 'Low', 'Close']].dropna()\
        .sort_index()
    df['hiduke'] = df.index.date
    # df = df.loc[df.index.strftime("%Y-%m-%d") <= kinou , :]
    uq_dates = df.hiduke.unique()
    if len(uq_dates) >=3 :
        uq_dates = uq_dates[-3:]
    # uq_dates = uq_dates.to_list()
    df = df.query(f" hiduke in {tuple(uq_dates)}")
    xlabels = df.reset_index().groupby('hiduke')\
            .min()['Datetime']

    """
    gapとなっている時間を抽出し、リスト名timegapとして取得する
    """
    # gapの期間中を時間単位で補間したDataFrameを取得。max()は便宜上入れています。
    df.index = pd.to_datetime(df.index)
    df_resample = df.resample('15min').max()
    # 元々のindexとまとめてgapの時間以外を重複要素としてやる
    merged_index = df.index.append(df_resample.index)
    timegap = merged_index[~merged_index.duplicated(
        keep=False)]  # 重複要素を除去することでgapとなっている時間を抽出する
    fig = go.Figure(data=[go.Candlestick(x=df.index,
                                         open=df['Open'],
                                         high=df['High'],
                                         low=df['Low'],
                                         close=df['Close'])]
                    )
    fig.update_layout(
        title=ft,
        font=dict(
            family="Courier New, monospace",
            size=12,
            color="RebeccaPurple"
        ),
        xaxis_rangeslider_visible=False,
        margin=dict(l=80, r=80, t=100, b=80)
    )
    fig.update_xaxes(
        rangebreaks=[dict(values=timegap, dvalue=3600000/4)],
        tickmode='array',
        tickvals=xlabels
    )
    figures.append(fig)

# fig.show()

# %%

width = 600
height = 300

template = (''
            '<img style="width: {width}; height: {height}"'
            ' src="data:image/png;base64,{image}">'
            # Optional caption to include below the graph
            # '{caption}'
            # '<br>'
            '<hr>'
            '')

# A collection of Plotly graphs
# figures

# Generate their images using `py.image.get`
images = [base64.b64encode(
    py.io.to_image(figure, width=width, height=height)
).decode('utf-8') for figure in figures]

report_html = ''
for image in images:
    _ = template
    _ = _.format(image=image,  width=width, height=height)
    report_html += _

# %%
rtns = []
for ft in tickers:
    df = data[[ft]].droplevel(0, axis=1)\
        .sort_index()
    df = df[['Open', 'High', 'Low', 'Close']].dropna()
    df = df.assign(date=df.index.strftime("%Y%m%d"))\
        .drop_duplicates(subset=['date'],keep="last")

    rtns.append(
        pd.DataFrame(dict(index=ft,
                rtn1d=100.*(df.Close[-1]/df.Close[-2]-1)
            )
            ,index = [0]
        )
    )


report_html += pd.concat(rtns).to_html()
# %%


# display(HTML(report_html))
# display(HTML(pd.concat(rtns).to_html()))
convert_html_to_pdf(report_html, 'monitor.pdf')

# %%
