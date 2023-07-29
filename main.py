from flask import Flask, request, jsonify
import hashlib
import hmac
import time
import requests

BASE_URL = 'https://api.bybit.com'

app = Flask(__name__)


def create_order(api_key, secret_key, coin_pair, position, buy_leverage):
    endpoint = '/v2/private/order/create'
    timestamp = int(time.time() * 1000)

    # Připrava dat pro požadavek
    data = {
        'symbol': coin_pair,
        'side': position,
        'leverage': int(buy_leverage),
        'order_type': 'Market',  # Můžete použít i 'Limit' podle vašich požadavků
        'qty': 1,  # Počet kryptoměn, které chcete nakoupit/prodat
        'time_in_force': 'GoodTillCancel',
        'timestamp': timestamp,
    }

    # Vytvoření podpisu pro autentizaci
    data_string = '&'.join([f"{key}={value}" for key, value in data.items()])
    sign = hmac.new(secret_key.encode(), data_string.encode(), hashlib.sha256).hexdigest()

    # Přidání podpisu a API klíče do datového objektu
    data['sign'] = sign
    data['api_key'] = api_key

    # Odeslání požadavku na platformu Bybit
    headers = {'Content-Type': 'application/json'}
    response = requests.post(BASE_URL + endpoint, json=data, headers=headers)

    return response.json()


@app.route('/', methods=['POST'])
def webhook():
    data = request.get_json()

    # Získání hodnot z TradingView alert message
    api_key = data['api_key']
    secret_key = data['secret_key']
    coin_pair = data['coin_pair']
    position = data['position']
    buy_leverage = data['buy_leverage']

    # Kontrola, zda jsou API klíče a ostatní hodnoty vyplněny
    if not api_key or not secret_key or not coin_pair or not position or not buy_leverage:
        return jsonify({"error": "Chybějící informace v alert message"}), 400

    # Odeslání požadavku na platformu Bybit pro provedení obchodu
    order_response = create_order(api_key, secret_key, coin_pair, position, buy_leverage)
    print("Obchod byl proveden:")
    print(order_response)

    return jsonify({"message": "Obchod byl proveden"}), 200


if __name__ == '__main__':
    # Spuštění aplikace s Gunicorn serverem na veřejné adrese a portu
    app.run(host='0.0.0.0', port=8080)
