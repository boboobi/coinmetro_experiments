import json
import os
import requests

BOT_TOKEN = os.environ.get('BOT_TOKEN')

COINMETRO_ENDPOINT = os.environ.get('COINMETRO_ENDPOINT')
PRICES_ENDPOINT = "/exchange/prices"
NOMINATING_ASSETS = ['USD', 'EUR', 'GBP']


def lambda_handler(event, _):
    try:
        body = json.loads(event['body'])
        message_part = body['message'].get('text')
        text_response = generate_text_response(message_part)
        if text_response is not None:
            chat_id = body['message']['chat']['id']
            url = f'https://api.telegram.org/bot{BOT_TOKEN}/sendMessage'
            payload = {
                'chat_id': chat_id,
                'text': text_response
            }
            _ = requests.post(url, json=payload)
        return {
            "statusCode": 200
        }
    except:
        return {
            "statusCode": 200
        }


def generate_text_response(message_part):
    if message_part.startswith('/volume'):
        volume = get_volume()
        return f"The current 24h volume on Coinmetro is ${volume:,.2f}"
    elif message_part.startswith('/admin'):
        return "@xcmonika @xcmusab @herebycm @reddug @XCMkellyXCM @JensAtDenmark @medatank @WillDec"
    elif message_part.startswith('/start'):
        return "Hey, I'm an unofficial bot for Coinmetro. Use the /help " \
               "command to see an overview of currently available commands."
    elif message_part.startswith('/help'):
        return "Here's an overview of commands : \n/admin : ping admins \n/volume : get 24h volume"
    return None


def get_volume():
    response = requests.get(f"{COINMETRO_ENDPOINT}{PRICES_ENDPOINT}")
    if response.status_code == 200:
        response_json = response.json()
        return calculate_volumes(response_json)
    else:
        print("API call failed.")
    return None


def calculate_volumes(price_data):
    volume = 0
    prices, rates = get_prices(price_data)
    for pair in price_data['24hInfo']:
        identifier = pair['pair']
        pair_volume = pair['v']
        nominating_asset = get_nominating_asset(identifier)
        if nominating_asset in rates:
            price = prices[identifier] * rates[nominating_asset]
            volume = volume + price * pair_volume
    return volume


def get_prices(price_data):
    prices = {}
    rates = {'USD': 1}
    for pair in price_data['latestPrices']:
        identifier = pair['pair']
        prices.update({identifier: pair['price']})
        nominating_asset = get_nominating_asset(identifier)
        if nominating_asset is not None and nominating_asset not in rates:
            rates.update({nominating_asset: 1.0})
    for asset in rates:
        rates.update({asset: get_rate(asset, prices)})
    return prices, rates


def get_rate(asset, prices):
    if f"{asset}USD" in prices:
        return prices[f"{asset}USD"]
    elif f"USD{asset}" in prices:
        return 1 / prices[f"{asset}USD"]
    elif f"BTC{asset}" in prices:
        btc_price = prices['BTCUSD']
        return btc_price / prices[f"BTC{asset}"]
    return 1.0


def get_nominating_asset(identifier):
    for asset in NOMINATING_ASSETS:
        if identifier.endswith(asset):
            return asset
    return None
