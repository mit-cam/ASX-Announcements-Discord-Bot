import requests
import json
import sqlite3
from discord import Webhook, RequestsWebhookAdapter, Embed, Colour
from configparser import ConfigParser


config = ConfigParser()
config.read('config.ini')

company_tickers = json.loads(config['Companies']['companies'])

conn = sqlite3.connect('announcements.db')
c = conn.cursor()


def get_xid(company_ticker: str) -> str:
    """Returns the XID of a company according to its ticker."""
    r = requests.get(
        f"https://asx.api.markitdigital.com/asx-research/1.0/search/predictive?searchText={company_ticker}").json()
    return r['data']['items'][0]['xidEntity']


for company in company_tickers:
    c.execute(
        f"CREATE TABLE IF NOT EXISTS {company} (document_key text, date text)")
    print(get_xid(company))
    announcements = requests.get(
        f"https://asx.api.markitdigital.com/asx-research/1.0/markets/announcements?entityXids[]={get_xid(company)}&page=0&itemsPerPage=5").json()
    for announcement in announcements['data']['items']:
        document_key = announcement["documentKey"]
        date = announcement["date"]
        c.execute(
            f"SELECT 1 FROM {company} WHERE document_key=?", (document_key,))
        if c.fetchone() is None:
            print(f"New announcement {document_key}, {date}")
            c.execute(
                f"INSERT INTO {company} VALUES (?, ?)", (document_key, date))
            webhook = Webhook.partial(
                int(config['Discord Settings']['id']), config['Discord Settings']['token'], adapter=RequestsWebhookAdapter())
            if announcement['isPriceSensitive'] is True:
                embed_colour = Colour.red()
            else:
                embed_colour = Colour.orange()
            embed = Embed(
                title=f"{announcement['companyInfo'][0]['symbol']} - {announcement['headline']}", colour=embed_colour)
            embed.add_field(name='Announcement Type',
                            value=announcement['announcementTypes'][0], inline=True)
            embed.add_field(name='Announcement Date',
                            value=announcement['date'], inline=True)
            embed.add_field(name='Price Sensitive',
                            value=str(announcement['isPriceSensitive']), inline=True)
            embed.add_field(name='Document URL',
                            value=f"https://cdn-api.markitdigital.com/apiman-gateway/ASX/asx-research/1.0/file/{announcement['documentKey']}?access_token=83ff96335c2d45a094df02a206a39ff4", inline=True)
            webhook.send(embed=embed)
            conn.commit()
        else:
            print("repeat")

conn.close()
