import sys
import time
from bs4 import BeautifulSoup as Bs
from selenium import webdriver
from os import name as os_name
from datetime import datetime
import backend_mongo as mo
import requests


users, tradeables, logs, webapp_current_ranking = mo.login()


def pull_USD_rates():
    """
    USD as the base currency, this function loads USD rates for any world currency, with its 3-letter abbreviation
    for currency, fields base2this and priceBase are  duplicated to achieve consistency between all tradeables
    base2this field is to be deprecated in future builds
    """
    base = "USD"
    currencies = tradeables.find({"group": "currencies"})
    source = requests.get("https://www.x-rates.com/table/?from=USD&amount=1").text
    soup = Bs(source, 'lxml')
    rates_table = soup.find('table', class_='tablesorter ratesTable')
    rates = rates_table.findAll('td', class_='rtRates')

    for item in currencies:
        cur = item['name']
        if cur == 'USD':
            mo.update_tradeable(
                dict(_id='currencies_' + cur, this2base=1.0, base2this=1.0, baseCurrency=True, priceBase=1.0))
            print('updated base currency')
        else:
            for c in rates:
                a = c.find('a')

                if a.get('href') == "http://www.x-rates.com/graph/?from={}&to={}".format(base, cur):
                    mo.update_tradeable({'_id': 'currencies_' + cur, 'base2this': float(a.text)})
                    print('updated rate Base to {}'.format(cur))

                if a.get('href') == "http://www.x-rates.com/graph/?from={}&to={}".format(cur, base):
                    mo.update_tradeable(
                        {'_id': 'currencies_' + cur, 'this2base': float(a.text), 'priceBase': float(a.text)})
                    print('updated rate {} to base'.format(cur))


"""futures - value != what you paid"""
"""forward - sold at 100 delivery in January. On December 31st value of the forward is 90. Value is -10?"""


def pull_cargill(url="https://www.cargillag.ca/sell-grain/local-bids?locationId=4014"):
    # todo: refactor for new data model
    chrome_options = webdriver.ChromeOptions()
    chrome_options.add_argument('--headless')
    chrome_options.add_argument('--no-sandbox')

    driver = webdriver.Chrome(
        executable_path='/usr/bin/chromedriver' if os_name == 'posix' else 'C:/chromedriver.exe',
        chrome_options=chrome_options,
        service_args=['--verbose'])

    driver.get(url)

    items = {
        'RED SPRING WHEAT': 'wheat',
        'CANOLA': 'canola',
        'WESTERN SOYBEANS': 'soybeans',
        'OATS': 'oats'
    }

    sections = driver.find_elements_by_class_name('bid_section')
    for section in sections:
        # one section - one commodity
        try:
            item_name = items[section.find_element_by_tag_name('h4').text.split(' -- ')[0]]
            table = section.find_element_by_tag_name('tbody')
            rows = table.find_elements_by_tag_name('tr')
            # row one[0]: current Spot Prices
            cols = rows[0].find_elements_by_tag_name('td')  # read one-month row
            date = datetime.strptime(cols[1].text[:10], '%m/%d/%Y')
            Y, M = [date.strftime(i) for i in ['%Y', '%B']]

            spot_price_mt = mo.this2base(float(cols[5].text), 'CAD')
            spot_futures_mt = mo.this2base(float(cols[3].text), 'CAD')
            forward_prices_mt = {M: dict(year=Y, month=M, price_now=spot_price_mt)}
            futures_prices_mt = {M: dict(year=Y, month=M, price_now=spot_futures_mt)}

            for i, row in enumerate(rows[1:]):
                # rows 2+: future dated prices
                cols = row.find_elements_by_tag_name('td')  # read one-month row
                # Todo: choose between MT and BU, then refactor
                date = datetime.strptime(cols[1].text[:10], '%m/%d/%Y')
                Y, M = [date.strftime(i) for i in ['%Y', '%B']]

                forward_mt = mo.this2base(float(cols[5].text), 'CAD')
                forward_bu = mo.this2base(float(cols[8].text), 'CAD')
                futures_mt = mo.this2base(float(cols[3].text), 'CAD')
                futures_bu = mo.this2base(float(cols[6].text), 'CAD')

                forward_prices_mt[M] = dict(year=Y, month=M, price_now=forward_mt)
                futures_prices_mt[M] = dict(year=Y, month=M, price_now=futures_mt)

            mo.update_tradeable({'_id': 'commodities_' + item_name, 'priceBase': spot_price_mt})
            mo.update_tradeable({'_id': 'futures_' + item_name, 'priceBase': futures_prices_mt})
            mo.update_tradeable({'_id': 'forwards_' + item_name, 'priceBase': forward_prices_mt})
            print(f'updated price for {item_name}:  CAD {mo.base2this(spot_price_mt, "CAD")}')

        except KeyError:
            print('KeyError: function pull_commodities_spot_price found an unknown good')

    driver.close()


def update_log(text, comment=''):
    logs.update_one(
        {"service": 'backend_updater'},
        {"$push": {
                'history': {
                    '$each': [f'{time.strftime("%b %d, %Y %H:%M", time.localtime())} :: {text} :: {comment}'],
                    '$position': 0
                            }
                }},
        upsert=True
    )


if __name__ == "__main__":
    try:
        # update_log('Update attempt', 'with __main__')
        pull_cargill()
        pull_USD_rates()
        update_log('Update complete', '-location-ElmCreek')
    except Exception as e:
        update_log(e, '')
    finally:
        sys.exit()
