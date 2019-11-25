import sys
import time
import backend_mongo as mo


users, tradeables, logs, webapp_current_ranking = mo.login()


def user_generator(umid_list):
    for umid in umid_list:
        yield mo.User(umid)


def get_rankings():
    print(f'{time.strftime("%M:%S", time.gmtime())} ranking')
    """ future feature: to get one class' ranking - change umid_list to match for ID list instead of finding all """
    ledger = []
    umid_list = [x['UMID'] for x in users.find({}, {"_id": 0, "UMID": 1})]

    # generate the ledger from list of UMIDs
    for user in user_generator(umid_list):
        ledger.append(dict(UMID=user.umid, name=user.name, balance=user.balance))

    # sort the ledger by balance
    ledger = sorted(ledger, key=lambda k: float(k['balance'].replace(',', '')))[::-1]

    # add rank to each
    for k, i in enumerate(ledger):
        ledger[k]['rank'] = k + 1

    # purge rankings and insert new data
    print(f'{time.strftime("%M:%S", time.gmtime())} db update')
    webapp_current_ranking.delete_many({"UMID": {"$nin": [umid_list]}})  # delete those no longer in the ledger
    webapp_current_ranking.insert_many(ledger)
    print(f'{time.strftime("%M:%S", time.gmtime())} complete')
    return True


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
        get_rankings()
        update_log('Rankings Complete')
    except Exception as err:
        print(err)
        update_log(err, '')
    finally:
        sys.exit()
