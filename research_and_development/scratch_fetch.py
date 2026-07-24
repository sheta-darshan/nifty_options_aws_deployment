import os
from dotenv import load_dotenv
from dhanhq import dhanhq
from dhanhq import DhanContext

load_dotenv('.env')
client_id = os.getenv('DHAN_CLIENT_ID')
token = os.getenv('DHAN_API_TOKEN')

context = DhanContext(client_id, token)
dhan = dhanhq(context)

orders = dhan.get_order_list().get('data', [])
if orders:
    try:
        orders.sort(key=lambda x: x.get('updateTime', x.get('createTime', '')))
    except Exception as e:
        pass
    for o in orders[-10:]:
        print(f"ID: {o.get('orderId')} | Symbol: {o.get('tradingSymbol')} | Status: {o.get('orderStatus')} | Type: {o.get('transactionType')} | Time: {o.get('updateTime', o.get('createTime'))}")
else:
    print('No orders found.')
