
from urllib.request import urlopen, Request
from bs4 import BeautifulSoup
import pandas as pd
import plotly
import plotly.express as px
import json 
import nltk
nltk.downloader.download('vader_lexicon')
from nltk.sentiment.vader import SentimentIntensityAnalyzer
from datetime import datetime

finviz_url = 'https://finviz.com/quote.ashx?t='

def get_news(ticker):
    url = finviz_url + ticker
    req = Request(url=url,headers={'User-Agent': 'Mozilla/5.0 (Windows NT 6.1; WOW64; rv:20.0) Gecko/20100101 Firefox/20.0'}) 
    response = urlopen(req)    
    html = BeautifulSoup(response)
    news_table = html.find(id='news-table')
    return news_table
	
def parse_news(news_table):
    parsed_news = []
    
    for x in news_table.findAll('tr'):
        
        text = x.a.get_text() 
        date_scrape = x.td.get_text().split()
        
        if len(date_scrape) == 1:
            time = date_scrape[0]
            
        else:
            if date_scrape[0].strip()=='Today':
                date = datetime.today().date()
                time = date_scrape[1]
            else:
                date = date_scrape[0]
                time = date_scrape[1]
        
        parsed_news.append([date, time, text])
        
        columns = ['date', 'time', 'headline']

        parsed_news_df = pd.DataFrame(parsed_news, columns=columns)
        
        parsed_news_df['datetime'] = pd.to_datetime(parsed_news_df['date'].astype(str) + ' ' + parsed_news_df['time'])
        
    return parsed_news_df
        
def score_news(parsed_news_df):
    vader = SentimentIntensityAnalyzer()
    scores = parsed_news_df['headline'].apply(vader.polarity_scores).tolist()
    scores_df = pd.DataFrame(scores)
    parsed_and_scored_news = parsed_news_df.join(scores_df, rsuffix='_right')
    # parsed_and_scored_news = parsed_and_scored_news.set_index('datetime')
    parsed_and_scored_news = parsed_and_scored_news.drop(['date', 'time'],axis=1)    
    parsed_and_scored_news = parsed_and_scored_news.rename(columns={"compound": "sentiment_score"})
    parsed_and_scored_news.to_csv("abc.csv")
    return parsed_and_scored_news

def plot_hourly_sentiment(parsed_and_scored_news, ticker):
    # print("!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!")
    # parsed_and_scored_news['datetime'] = pd.to_datetime(parsed_and_scored_news['datetime'])
    # print(type(len(parsed_and_scored_news)))
    total=len(parsed_and_scored_news)
    mean_scores = parsed_and_scored_news.resample('h',on="datetime").sum()
    mean_scores["sentiment_score"]=mean_scores["sentiment_score"]/total
    fig = px.bar(mean_scores, x=mean_scores.index, y='sentiment_score', title = ticker + ' Hourly Sentiment Scores')
    return fig 

def plot_daily_sentiment(parsed_and_scored_news, ticker):
    total=len(parsed_and_scored_news)
    mean_scores = parsed_and_scored_news.resample('D',on="datetime").sum()
    mean_scores["sentiment_score"]=mean_scores["sentiment_score"]/total
    fig = px.bar(mean_scores, x=mean_scores.index, y='sentiment_score', title = ticker + ' Daily Sentiment Scores')
    return fig

def sentiment(tickers):
    tickers_list=[i.upper() for i in tickers.split(' ')]
    # print(tickers_list)
    columns = ['date', 'time', 'headline']
    parse_news_df = pd.DataFrame(columns=columns)

    for tick in tickers_list:
        
        try:
            news_table = get_news(tick)
            p=parse_news(news_table)
            # print(p)
            parse_news_df = pd.concat([parse_news_df, p], axis=0)
        except  Exception as e:
            continue
        
    parsed_and_scored_news = score_news(parse_news_df)
    parsed_and_scored_news['datetime'] = pd.to_datetime(parsed_and_scored_news['datetime'])
    fig_hourly = plot_hourly_sentiment(parsed_and_scored_news, tickers)
    fig_daily = plot_daily_sentiment(parsed_and_scored_news, tickers)

    graphJSON_hourly = json.dumps(fig_hourly, cls=plotly.utils.PlotlyJSONEncoder)
    graphJSON_daily = json.dumps(fig_daily, cls=plotly.utils.PlotlyJSONEncoder)

    header= "Hourly and Daily Sentiment of {} Stock".format(tickers)
    description = """
	The above chart averages the sentiment scores of {} stock hourly and daily.
	The table below gives each of the most recent headlines of the stock and the negative, neutral, positive and an aggregated sentiment score.
    """.format(tickers)
    return graphJSON_hourly,graphJSON_daily ,header,parsed_and_scored_news.to_html(classes='data'),description
