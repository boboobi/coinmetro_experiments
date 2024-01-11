import json
import os
import requests
import time

from parse import get_argument_at_index, get_numerical_argument_at_index
from command import Command, match_command

LAG = 60  # seconds to wait before refreshing cache
BOT_TOKEN = os.environ.get('BOT_TOKEN')

COINMETRO_ENDPOINT = os.environ.get('COINMETRO_ENDPOINT')
PRICES_ENDPOINT = "/exchange/prices"
ASSETS_ENDPOINT = "/assets"
NOMINATING_ASSETS = ['USD', 'USDT', 'USDC', 'EUR', 'GBP', 'BTC', 'ETH', 'AUD']
NOMINATING_ASSET_MAP = {} # used as cache

response_cache = {}


def lambda_handler(event, _):
    try:
        body = json.loads(event['body'])
        message_part = body['message'].get('text')
        text_response = generate_text_response(message_part)
        if text_response is not None:
            chat_id = body['message']['chat']['id']
            send_message(BOT_TOKEN, chat_id, text_response)
        return {
            "statusCode": 200
        }
    except Exception as exception:
        print('Something went wrong.')
        print(exception)
        return {
            "statusCode": 200
        }


def send_message(bot_token, 
    chat_id, 
    message, 
    parse_mode='HTML',
    disable_web_page_preview=True):
    preview_off = f"disable_web_page_preview={disable_web_page_preview}"
    parameters = f'parse_mode={parse_mode}&{preview_off}'
    url = f'https://api.telegram.org/bot{bot_token}/sendMessage?{parameters}'
    payload = {
        'chat_id': chat_id,
        'text': message
    }
    _ = requests.post(url, json=payload)


def generate_text_response(message_part):
    response = None
    command = match_command(message_part)
    if command is Command.START:
        return "Hey, I'm an unofficial bot for Coinmetro. Use the /help " \
               "command to see an overview of currently available commands."
    elif command is Command.HELP:
        return "Here's an overview of commands : \n" \
               "/admin : ping admins \n" \
               "/volume : get 24h volume \n" \
               "/topvolume x : get volume for top x pairs, x from 1-20 \n" \
               "/sentiment y : get sentiment data for asset y \n" \
               "/code: get a link to the codebase"
    elif command is Command.VOLUME:
        return get_with_caching(command, get_volume)
    elif command is Command.TOPVOLUME:
        nb = get_numerical_argument_at_index(message_part, index=1)
        if nb is None:
            nb = 10
        if nb > 0 and nb < 21:
            return get_volume(leading_text=False, nb_top=nb)
    elif command is Command.ADMIN:
        return "@xcmonika @xcmusab @herebycm @reddug @XCMkellyXCM " \
               "@JensAtDenmark @medatank @WillDec"
    elif command is Command.CODE:
        return "See https://github.com/radagasus/coinmetro_bot"
    elif command is Command.SENTIMENT:
        asset = get_argument_at_index(message_part, index=1)
        sentiment_data = get_sentiment(asset)
        if sentiment_data is not None:
            sentiment, interest = sentiment_data
            preface = f"Sentiment data for {asset}:\n\n"
            if interest is None:
                return f"{preface}Sentiment: <i>{sentiment:,.2f}</i>"
            return f"{preface}Sentiment: <i>{sentiment:,.2f}</i>\nInterest: <i>{interest:,.2f}</i>"
    return response


def update_cache(command, response):
    response_cache.update({command: (time.time(), response)})


def get_with_caching(command, function):
    if command in response_cache:
        tic, response = response_cache.get(command)
        if time.time() - tic < LAG:
            return response
    response = function()
    update_cache(command, response)
    return response


def get_volume(leading_text=True, nb_top=3):
    response = requests.get(f"{COINMETRO_ENDPOINT}{PRICES_ENDPOINT}")
    if response.status_code == 200:
        response_json = response.json()
        total_volume, volumes = calculate_volumes(response_json)
        top = format_top_volumes(volumes, nb_top)
        if not leading_text:
            return f"Top {nb_top}: {top}"
        return f"The current 24h volume on Coinmetro is " \
                   f"${total_volume:,.2f}\n\n " \
                   f"Top {nb_top}: {top}"
    else:
        print("API call failed.")
    return None


def format_top_volumes(volumes, nb_top=3):
    sorted_volumes = sorted(volumes.items(), key=lambda x: x[1], reverse=True)
    top = '\n\t'.join([format_volume(sorted_volumes[i]) for i in range(nb_top)])
    return f"\n\t{top}"


def format_volume(tuple):
    return f"${tuple[0]}: ${tuple[1]:,.2f}"


def calculate_volumes(price_data):
    total_volume = 0
    volumes = {}
    prices = get_prices(price_data)
    for pair in price_data['24hInfo']:
        identifier = pair['pair']
        if identifier in prices:
            price, nominating_asset = prices[identifier]
            rate = get_rate(nominating_asset, prices)
            if rate is not None and price is not None:
                price_dollar = price * rate
                pair_volume = price_dollar * pair['v']
                total_volume = total_volume + pair_volume
                volumes.update({identifier: pair_volume})
    return total_volume, volumes


def get_prices(price_data):
    prices = {}
    for pair in price_data['latestPrices']:
        identifier = pair['pair']
        nominating_asset = get_nominating_asset(identifier)
        prices.update({identifier: (pair['price'], nominating_asset)})
    return prices


def get_rate(asset, prices):
    usd_tickers = ['USD', 'USDT', 'USDC']
    if asset in usd_tickers:
        return 1.0
    for usd_ticker in usd_tickers:
        pair_id = f"{asset}{usd_ticker}"
        if pair_id in prices:
            return prices[pair_id][0]
        inverted_pair_id = f"{usd_ticker}{asset}"
        if inverted_pair_id in prices:
            return 1 / prices[inverted_pair_id][0]
    if f"BTC{asset}" in prices:
        btc_price = prices['BTCUSD'][0]
        return btc_price / prices[f"BTC{asset}"][0]
    return None


def get_nominating_asset(identifier):
    def get_nominating_asset_internal():
        if identifier in NOMINATING_ASSET_MAP:
            return NOMINATING_ASSET_MAP[identifier]
        nominating_asset = None
        for asset in NOMINATING_ASSETS:
            if identifier.endswith(asset):
                nominating_asset = asset
        NOMINATING_ASSET_MAP.update({identifier: nominating_asset})
        return nominating_asset
    return get_nominating_asset_internal()


def get_assets():
    response = requests.get(f"{COINMETRO_ENDPOINT}{ASSETS_ENDPOINT}")
    if response.status_code == 200:
        return response.json()
    return None


def get_sentiment(identifier):
    assets = get_with_caching(Command.ASSETS, get_assets)
    def matches_name(asset, identifier):
        return 'name' in asset \
            and asset['name'].casefold() == identifier.casefold()
    def matches_symbol(asset, identifier):
        return 'symbol' in asset \
            and asset['symbol'].casefold() == identifier.casefold()
    for asset in assets:
        if matches_name(asset, identifier) or matches_symbol(asset, identifier):
            if 'sentimentData' in asset:
                sentiment_data = asset['sentimentData']
                if 'sentiment' in sentiment_data:
                    if 'interest' in sentiment_data:
                        return sentiment_data['sentiment'], sentiment_data['interest']
                    return sentiment_data['sentiment'], None
            return None
    return None
