from flask import Flask, request, jsonify
import hashlib
import hmac
import time
import requests
import urllib.parse

BASE_URL = 'https://api.bybit.com'

app = Flask(__name__)


def get_account_balance(api_key, secret_key):
    endpoint = '/v2/private/wallet/balance'
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

    return response.json()


def create_order(api_key, secret_key, coin_pair, position, buy_leverage, percentage, trade_type='derivatives'):
    # Získání informací o zůstatku na účtu
    account_balance_response = get_account_balance(api_key, secret_key)

    # Kontrola, zda byla odpověď úspěšná
    if 'result' not in account_balance_response or not account_balance_response['result']:
        return jsonify({"error": "Nepodařilo se získat informace o zůstatku účtu"}), 500

    # Získání hodnoty zůstatku v USDT (USD Tether)
    account_balance = account_balance_response['result']['USDT']['equity']

    # Vypočítání množství kryptoměny na základě zadaného procenta zůstatku
    trade_amount = float(account_balance) * (float(percentage) / 100)

    if trade_type == 'derivatives':
        endpoint = '/v2/private/order/create'
    elif trade_type == 'spot':
        endpoint = '/v2/private/spot/order/create'
    else:
        return jsonify({"error": "Neplatný typ obchodu, použijte 'derivatives' nebo 'spot'"}), 400

    timestamp = int(time.time() * 1000)

    # Příprava dat pro požadavek
    data = {
        'symbol': coin_pair,
        'side': position,
        'leverage': int(buy_leverage),
        'order_type': 'Market',
        'qty': trade_amount,  # Použití vypočteného množství kryptoměny pro obchod
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

    return response.json(), response.status_code


@app.route('/', methods=['POST'])
def webhook():
    try:
        data = request.get_json()

        # Získání hodnot z TradingView alert message
        api_key = data['api_key']
        secret_key = data['secret_key']
        coin_pair = data['coin_pair']
        position = data['position']
        buy_leverage = data['buy_leverage']
        percentage = data['percentage']
        trade_type = data.get('trade_type', 'derivatives')  # Defaultně bude obchodováno na derivatives

        # Kontrola, zda jsou API klíče a ostatní hodnoty vyplněny
        if not api_key or not secret_key or not coin_pair or not position or not buy_leverage or not percentage:
            return jsonify({"error": "Chybějící informace v alert message"}), 400

         # Odeslání požadavku na platformu Bybit
        headers = {'Content-Type': 'application/json'}
        response = requests.post(BASE_URL + endpoint, json=data, headers=headers)
    
        # Zde upravujeme zpracování odpovědi
        if response.headers['content-type'] == 'application/json':
            response_json = response.json()
            return response_json, response.status_code
        else:
            return response.content, response.status_code

    except Exception as e:
        print("Došlo k chybě:")
        print(str(e))
        return jsonify({"error": "Došlo k chybě při provádění požadavku"}), 500


if __name__ == '__main__':
    # Spuštění aplikace s Gunicorn serverem na veřejné adrese a portu
    app.run(host='0.0.0.0', port=80)
