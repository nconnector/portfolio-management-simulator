import time
import pymongo
import configparser
from mongoengine import connect


def login():
    """ service function that connects to the dedicated mongo server """
    config = configparser.ConfigParser()
    config.read('config.ini')

    unm = config['MONGO']['UNM']
    pwd = config['MONGO']['PWD']
    host = config['MONGO']['IP']
    db = config['MONGO']['DB']
    mongo = connect(db, alias='portfolio_owner', host=host, port=27017)
    try:
        mongo[db].authenticate(unm, pwd, source=db)
        print('connected using handshake @ {}:27017/{}'.format(host, db))

        webapp_users = mongo[db].webapp_users  # collection
        webapp_tradeables = mongo[db].tradeables  # collection
        webapp_current_ranking = mongo[db].webapp_current_ranking  # collection

        return webapp_users, webapp_tradeables, webapp_current_ranking
    except pymongo.errors.OperationFailure:
        print('    WARNING! connection using handshake has failed')


users, tradeables, current_rankings = login()


def get_rank(umid):
    count = current_rankings.count()
    rank = current_rankings.find_one({"UMID": umid}, {"_id": 0, "rank": 1})['rank']
    return rank, count


class User:
    def __init__(self, umid):
        user = users.find_one({'UMID': umid}, {'_id': 0})
        self.umid = umid
        self.name = user['name']
        self.history = user['history']
        self.balance = 0
        self.account = []
        order = dict(currencies=0, commodities=1, forwards=2, futures=3, options=4, stocks=5)
        for item in user.keys():
            if item not in ['UMID', 'name', 'history']:
                tradeable = tradeables.find_one({'_id': item})
                ledger = user[item]
                price = tradeable["priceBase"]
                if type(price) != dict:  # in Currencies and Commodities ledger==amount and price is float
                    total = ledger * price
                    price = f"$ {price:,.4f}"
                elif tradeable['group'] == 'forwards':  # in Forwards ledger is dict and price is dict
                    total = 0
                    for position in ledger['ledger']:
                        price_at_purchase = position['price']
                        price_now = price[position['month']]['price_now']
                        total += position['amount'] * (price_now - price_at_purchase)
                    ledger = ledger['total_amount']
                    price = ""
                else:  # todo: add Futures, Options and Stocks
                    total = 0
                    ledger = 0
                    price = ""

                row = dict(name=tradeable['name'].capitalize(),
                           group=tradeable['group'].upper(),
                           group_order=order[tradeable['group']],
                           amount=f"{ledger:,.2f}",
                           price=price,
                           total=f"$ {total:,.2f}",
                           )
                self.balance += total
                self.rank, self.rankCount = get_rank(self.umid)
                self.account.append(row)
        self.balance = f"{self.balance:,.2f}"


def update_tradeable(instruction):
    """ service function that changes parameters of tradeables (current price, initial amount, etc..) """
    try:
        tradeables.update_one(
            {"_id": instruction["_id"]},
            {"$set": instruction},
            upsert=True
        )
    except TypeError:
        print("Error: instruction is not a dict")
    except KeyError:
        print("Error: no valid tradeable name in instruction")


def new_user_portfolio(umid, name=''):
    # todo: edit user init to suit new model
    """
    this function boots up a new user into the database and assigns them starting amounts of tradeables
    takes in student ID and name
    """
    instruction = {'UMID': int(umid), 'name': name, 'history': []}
    for item in tradeables.find():
        instruction[item['_id']] = item['startingCount']

    try:
        users.update_one(
            {"UMID": instruction["UMID"]},
            {"$set": instruction},
            upsert=True
        )
    except TypeError:
        print("Error: instruction is not a dict")
    except KeyError:
        print("Error: no valid ID in instruction")


def user_portfolio_trade(delta_instruction, action='trading'):
    """this function updates user portfolio with given pre-set instructions"""
    # TODO: refactor into one pooled update command instead of two
    umid = delta_instruction["UMID"]
    id1 = delta_instruction['_id1']
    delta1 = delta_instruction['val1']
    id2 = delta_instruction['_id2']
    delta2 = delta_instruction['val2']
    price = base2this(tradeables.find_one({'_id': id1}, {'priceBase': 1})['priceBase'], id2.split('_')[-1])

    # TODO: refactor for new data model
    try:
        users.update_one(
            {"UMID": umid},
            {"$inc": {id1: delta1, id2: delta2}},
            upsert=False
        )
        users.update_one(
            {"UMID": umid},
            {"$push": {'history': f'{action:<7} {abs(delta1):>10.2f} {id1:<15} for {abs(delta2):>10.2f} {id2[-3:]:<3} at {price:>12.4f} per unit on {time.strftime("%c")}'}},
            upsert=False
        )

    except TypeError:
        print("Error: instruction is not a dict")
    except KeyError:
        print("Error: no valid ID in instruction")


def base2this(base_amount, this_currency, debug=False):
    """ exchange an amount of base currency into this currency """
    this_amount = base_amount * tradeables.find_one({'name': this_currency}, {'_id': 0, 'base2this': 1})['base2this']
    if debug:
        print("*base2this* {:.2f} {} converts to {:.2f} {}".format(base_amount, 'USD', this_amount, this_currency))
    return this_amount


def this2base(this_amount, this_currency, debug=False):
    """ exchange an amount of this currency into base currency """
    base_amount = this_amount * tradeables.find_one({'name': this_currency}, {'_id': 0, 'this2base': 1})['this2base']
    if debug:
        print("*this2base* {:.2f} {} converts to {:.2f} {}".format(this_amount, this_currency, base_amount, 'USD'))
    return base_amount
