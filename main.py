from flask import Flask, request, jsonify
import hashlib
import hmac
import time
import requests
import urllib.parse
import logging
import traceback


BASE_URL = 'https://api.bybit.com'

app = Flask(__name__)

# Konfigurace logování
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Získání loggeru pro knihovnu 'requests'
requests_logger = logging.getLogger('requests')
requests_logger.setLevel(logging.DEBUG)
requests_logger.propagate = True


def get_account_balance(api_key, secret_key):
    endpoint = '/v5/account/wallet-balance'
    timestamp = int(time.time() * 1000)

    data = {
        'coin': 'USDT',
        'timestamp': timestamp,
    }

    data_string = '&'.join([f"{key}={urllib.parse.quote(str(value))}" for key, value in data.items()])
    sign = hmac.new(secret_key.encode(), data_string.encode(), hashlib.sha256).hexdigest()

    data['sign'] = sign
    data['api_key'] = api_key

    headers = {'Content-Type': 'application/json'}
    response = requests.get(BASE_URL + endpoint, params=data, headers=headers)

    # Check if the request was successful (status code 200) and return the JSON data
    if response.status_code == 200:
        return response
    else:
        # If the request failed, you can handle the error here, e.g., print the error message
        print("Error: Failed to get account balance.")
        return None



def create_order(api_key, secret_key, coin_pair, position, buy_leverage, trade_type='derivatives'):
    # Fixed trade amount of 10 USDT
    trade_amount = 1.0

    if trade_type == 'derivatives':
        endpoint = '/v2/private/order/create'
    elif trade_type == 'spot':
        return jsonify({"error": "Není podporováno obchodování na spot (mimoderivátech)"}), 400
    else:
        return jsonify({"error": "Neplatný typ obchodu, použijte 'derivatives' nebo 'spot'"}), 400

    timestamp = int(time.time() * 1000)

    # Příprava dat pro požadavek
    data = {
        'symbol': coin_pair,
        'side': position,
        'order_type': 'Market',
        'qty': trade_amount,  # Fixed trade amount of 10 USDT
        'time_in_force': 'GoodTillCancel',
        'timestamp': timestamp,
    }

    data_string = '&'.join([f"{key}={urllib.parse.quote(str(value))}" for key, value in data.items()])
    sign = hmac.new(secret_key.encode(), data_string.encode(), hashlib.sha256).hexdigest()

    # Přidání podpisu a API klíče do datového objektu
    data['sign'] = sign
    data['api_key'] = api_key

    # Odeslání požadavku na platformu Bybit
    headers = {'Content-Type': 'application/json'}
    response = requests.post(BASE_URL + endpoint, json=data, headers=headers)

    # Zde získáme JSON odpověď z API a převedeme ji na slovník
    response_data = response.json()

    # Vypište obsah odpovědi z API, abychom zjistili, co nám vrací
    print("Odpověď z Bybit API:")
    print(response_data)

    # Kontrola, zda byla objednávka úspěšně vytvořena
    if 'result' not in response_data or not response_data['result']:
        # If the order creation was not successful, print an error message
        print("Error: Failed to create order.")
        return None
    else:
        # If the order was successfully created, return the response data
        return response_data


@app.route('/', methods=['POST'])
def webhook():
    try:
        data = request.get_json()

        # Získání hodnot z TradingView alert message
        api_key = data['api_key']
        secret_key = data['secret_key']
        coin_pair = data['coin_pair']
        action = data['action']  # Možnosti: 'open_long', 'close_long', 'open_short', 'close_short'
        percentage = data['percentage']

        # Kontrola, zda jsou API klíče a ostatní hodnoty vyplněny
        if not api_key or not secret_key or not coin_pair or not action or not percentage:
            return jsonify({"error": "Chybějící informace v alert message"}), 400

        # Rozlišení pozice (long nebo short) a akce (otevření nebo uzavření)
        if action == 'open_long':
            position = 'Buy'
        elif action == 'close_long':
            position = 'Sell'
        elif action == 'open_short':
            position = 'Sell'
        elif action == 'close_short':
            position = 'Buy'
        else:
            return jsonify({"error": "Neplatná akce, použijte 'open_long', 'close_long', 'open_short' nebo 'close_short'"}), 400

        # Odeslání požadavku na platformu Bybit pro provedení obchodu
        response_data, status_code = create_order(api_key, secret_key, coin_pair, position, buy_leverage, percentage)
        logger.debug("Odpověď z Bybit API:")
        logger.debug(response_data)

        # Zde můžeme ověřit, zda je 'response_data' ve formátu JSON, pokud ne, vypíšeme ho jako text
        if isinstance(response_data, dict):
            logger.debug("Odpověď z Bybit API (JSON):")
            logger.debug(response_data)
        else:
            logger.debug("Odpověď z Bybit API (text):")
            logger.debug(response_data)

        # Kontrola, zda se vrátil HTTP kód 200 OK
        if status_code == 200:
            return jsonify({"message": "Obchod byl proveden"}), 200
        else:
            return jsonify({"error": "Došlo k chybě při provádění požadavku"}), 500
            
    except Exception as e:
        traceback.print_exc()  # Print the traceback for detailed error information
        return jsonify({"error": "An unexpected error occurred"}), 500



if __name__ == '__main__':
    # Spuštění aplikace s Gunicorn serverem na veřejné adrese a portu
    app.run(host='0.0.0.0', port=80)
