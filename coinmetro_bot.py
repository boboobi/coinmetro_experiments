import json
import os
import requests

BOT_TOKEN = os.environ.get('BOT_TOKEN')

COINMETRO_ENDPOINT = os.environ.get('COINMETRO_ENDPOINT')
PRICES_ENDPOINT = "/exchange/prices"


def lambda_handler(event, context):
    print(event)
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
            response = requests.post(url, json=payload)
        return {
            "statusCode": 200
        }
    except:
        return {
            "statusCode": 200
        }
        

def generate_text_response(message_part):
    if message_part == '/volume':
        volume = get_volume()
        return f"The current 24h volume on Coinmetro is ${volume:.2f}."
    elif message_part == '/admin':
        return "@xcmonika @xcmusab @herebycm @reddug @XCMkellyXCM @JensAtDenmark @medatank"
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
    prices = {}
    for pair in price_data['latestPrices']:
        identifier = pair['pair']
        prices.update({identifier: pair['price']})
    for pair in price_data['24hInfo']:
        identifier = pair['pair']
        pair_volume = pair['v']
        price = prices[identifier]
        if identifier.endswith("EUR"):
            price = price * 1.1
        if identifier.endswith("GBP"):
            price = price * 1.3
        volume = volume + price * pair_volume
    return volume
