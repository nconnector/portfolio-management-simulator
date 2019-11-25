from Webapp_Portfolio import mongo as mo
import time

#    SETTINGS    

users, tradeables, rankings = mo.login()

#    DEFINE TRADEABLE ITEMS


def init_tradeable(name="unknown item", group="", count=0, priceBase=0):
    # todo: rework for DJango and new Classes
    """ this function allows setting up new tradeables without interrupting the trading process """
    params = {
        '_id': "{}_{}".format(group, name),
        'name': name,
        'group': group,
        'startingCount': count,
        'priceBase': priceBase
                }
    print('initialized {} {} as tradeable'.format(group, name))
    return params


def push_tradeables_to_mongo():
    # todo: rework for DJango and new Classes
    # todo: do NOT allow ZERO values
    """
    this function allows a clean reset of tradeables, based on the lists below
    beware, this function does not delete current tradeables, but instead updates them to default values
    """

    currencies = ["USD", "CAD"]
    items = ["wheat", "canola", "soybeans", "oats"]
    starting = dict(wheat=544.31, canola=500, soybeans=680.38, oats=0)  # wheat=20000bu, canola=500MT, soybeans=25000bu
    groups = ["commodities", "forwards", "futures", "options"]
    #  place the table of starting parameters HERE

    for c in currencies:
        mo.update_tradeable({
                            '_id': "currencies_{}".format(c),
                            'name': c,
                            'group': "currencies",
                            'base2this': 0,
                            'this2base': 0,
                            'baseCurrency': False if c != 'USD' else True
                            })
        print('initialized {} as tradeable currency'.format(c))

    for group in groups:
        for item in items:
            if group in ['forwards', 'futures', 'options']:
                count = {'total_amount': 0, 'ledger': []}
                price = {}
            elif group == 'commodities':
                count = starting[item]
                price = 0
            else:
                count = 0
                price = {}
            mo.update_tradeable(init_tradeable(name=item, group=group, count=count, priceBase=price))


#  DEFINE USER AND TRADE PROCESS


def trade(umid, id1, val1, id2, val2, action='trade'):
    # todo: rework for DJango and new Classes
    """
    this function allows to freely trade two commodities between themselves
    amount verification complete
    price verification complete
    """

    user = users.find_one({"UMID": umid})
    if id1 != id2:
        if user[id1]+val1 >= 0 and user[id2]+val2 >= 0:
            if val1*val2 < 0:
                delta_instruction = {
                                    'UMID': umid,
                                    '_id1': id1,
                                    'val1': val1,
                                    '_id2': id2,
                                    'val2': val2
                                    }
                mo.user_portfolio_trade(delta_instruction, action)
#                print("traded {:+.0f} {} for {:+.0f} {}".format(val1, id1, val2, id2))
                print('*trade* trade complete')
            else:
                print("    cannot trade {:+.0f} {} for {:+.0f} {}".format(val1, id1, val2, id2))
                print("    (one account must diminish as the other expands)")
        else:
            print("    cannot trade {:+.0f} {} for {:+.0f} {} (insufficient funds)".format(val1, id1, val2, id2))
    else:
        print("    cannot trade for the same tradeable")

# todo: buy_forwards() as class in mongo.py


# class Forward:
#     # todo: make sure this works and complies with architecture
#     def __init__(self, name):
#         self.id = f'forwards_{name}'
#         self.item = tradeables.find_one({'_id': id})

def buy_forward(umid, name, month, amount, currency='USD'):
    forward = tradeables.find_one({'_id': f'forwards_{name}'})['priceBase'][month]
    yr = forward['year']
    price = forward['price_now']  # price in USD only.

    if amount > 0:
        users.update_one({"UMID": umid}, {'$inc': {f'forwards_{name}.total_amount': amount}})
        users.update_one(
            {'UMID': umid},
            {'$push': {f'forwards_{name}.ledger': dict(year=yr, month=month, price=price, amount=amount)}}
        )
        users.update_one(
            {"UMID": umid},
            {"$push": {
                'history':
                f'{time.strftime("%c")} Bought {amount} {name} {month} forwards at {currency} {price:.2f} per unit'
                      }
             }
        )
    else:
        print('selling not done yet')


def buy_commodity(umid, id1, val1, cur=tradeables.find_one({'baseCurrency': True})['name']):
    # todo: rework for DJango and new Classes
    """
    this function allows to buy val1 amount of id1 for currency (base currency by deafault)
    just like real world, buy -10 equals to sell 10
    when val1 == +10 base currency account will be ammended by  ( -10 * price of id1 )
    """
    currency = tradeables.find_one({'name': cur})['_id']
    valBase = tradeables.find_one({'_id': id1})['priceBase'] * val1 * -1  # todo: remove
    valCur = valBase * tradeables.find_one({'name': cur})['base2this']

    if val1 >= 0:
        action = 'Bought'
    else:
        action = 'Sold'

    trade(umid, id1, val1, currency, valCur, action)
    print()
    print('    {} {:.2f} {} for {}'.format(action, val1, id1.split('_')[1], cur))
    print('    {:<3}  Unit price: {:.2f}   Total: {:.2f}'.format('USD', valBase/-val1, valBase))
    print('    {:<3}  Unit price: {:.2f}   Total: {:.2f} <-- final'.format(cur, valCur/-val1, valCur))

