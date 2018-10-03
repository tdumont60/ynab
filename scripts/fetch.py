import datetime
import json
import os
import sys
import time

import requests


URL = 'https://api.youneedabudget.com/v1'
MONTHS_BACK = 6


def main():
    token = os.environ.get('YNAB_TOKEN', None)
    if not token:
        raise RuntimeError('YNAB_TOKEN not set')

    ynab = YnabClient(URL, token)

    month_result = ynab.get('/budgets/last-used/months')
    month_list = month_result['data']['months']

    def month_from_row(row):
        return datetime.date(*time.strptime(row['month'], '%Y-%m-%d')[:3])

    found_months = sorted(filter(not_in_future,
                                 map(month_from_row, month_list)),
                          reverse=True)[:MONTHS_BACK]

    out_months = []
    for month in found_months:
        results = ynab.get('/budgets/last-used/months/%s' % month.strftime('%Y-%m-%d'))
        out_months.append(results['data']['month'])

    categories = ynab.get('/budgets/last-used/categories')

    output = {'categories': categories,
              'months': out_months}

    print json.dumps(output)


def not_in_future(dt):
    return dt <= datetime.date.today()


class YnabClient(object):
    def __init__(self, url, token):
        self.url = url
        self.token = token
        self.session = requests.session()

    def get(self, path):
        resp = self.session.get(self.url + path, headers={'Authorization': 'Bearer %s' % self.token})
        if resp.status_code != 200:
            raise RuntimeError(resp)

        return resp.json()


if __name__ == '__main__':
    sys.exit(main())
