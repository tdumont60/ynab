from collections import defaultdict
import datetime
import hashlib
import json
import os
import sys
import time

import requests


DAYS_IN_MONTH = 30
URL = 'https://api.youneedabudget.com/v1'


TEMPLATE = """
<html>
  <body style="font-size: 30px">
  {% for cat in cats %}
  <div style="display: block; color: {{ cat.color }}; font-size: 40px; font-weight: bold">{{ cat.name }}</div>
  <div>Spent {{ cat.per_day_so_far }} per day so far</div>
  <div>Able to spend {{ cat.per_day_remaining }} per day for the rest of the month</div>
  {% if cat.days_until_balance > 0 %}
  <div>Or, don't spend for {{ cat.days_until_balance }} days in order to restore balance</div>
  {% else %}
  <div>Can spend up to {{ cat.burst_amount }} today and still be on track.</div>
  {% endif %}
  <div style="display: block; position: absolute; width: {{ cat.green_left }}px; height:30px; background-color:#F88">&nbsp;</div>
  <div style="display: block; position: absolute; left: {{ cat.green_left }}px; width: {{ cat.green_width }}px; height:30px; background-color:#8F8">&nbsp;</div>
  <div style="display: block; position: absolute; left: {{ cat.bar_left }}px; width: 4px; height:30px; background-color:0">&nbsp;</div>
  <div style="margin-top: 40px"><hr></div>
  {% endfor %}
  </body>
</html>
"""

NUMBER_TEMPLATE = """
<body style="font-size: 40px">
<table border="0" cellpadding="3" cellspacing="0" style="font-size: 40px">
{% for i, (w, d, n1, n2) in enumerate(data) %}
{% if i == 0 %}
<tr style="font-weight:bold">
{% else %}
<tr>
{% endif %}
<td>{{ w }}</td>
<td>{{ d }}</td>
<td>{{ n1 }}</td>
<td>{{ n2 }}</td>
</tr>
{% endfor %}
</table>
{% for k in totals %}
<div>{{ k }}: {{ totals[k] }}
{% endfor %}
</body>
"""


from flask import Flask, render_template_string
app = Flask(__name__)


def h(d, s):
    possibilities = 4
    cycles = 2
    days_in_group = possibilities * cycles
    d_ord = d.toordinal()
    d_cycle_index = d_ord % days_in_group
    group_start_ord = d_ord - d_cycle_index
    days_in_group = [datetime.date.fromordinal(group_start_ord + i) for i in range(days_in_group)]
    days_in_group.sort(key=lambda x: hashlib.md5(str(x.toordinal()) + s).hexdigest())
    assert d in days_in_group
    return (days_in_group.index(d) % possibilities) + 1


@app.route('/number')
def number():
    data = []
    totals = defaultdict(lambda: defaultdict(int))
    for i in range(30):
        d = datetime.date.today() - datetime.timedelta(days=i)
        date_str = d.strftime('%Y-%m-%d')
        weekday = d.strftime('%A')[0]
        seed1 = 'abcd'
        seed2 = 'ghjkinj'
        num1 = h(d, seed1)
        num2 = h(d, seed2)
        data.append((weekday, date_str, num1, num2))
        totals[0][num1] += 1
        totals[1][num2] += 1

    table = []

    return render_template_string(NUMBER_TEMPLATE, data=data, totals=totals, enumerate=enumerate)

@app.route('/')
def hello_world():
    token = os.environ.get('YNAB_TOKEN', None)
    if not token:
        raise RuntimeError('YNAB_TOKEN not set')

    ynab = YnabClient(URL, token)

    categories = ynab.get('/budgets/last-used/categories')
    params = {}
    for cg in categories['data']['category_groups']:
        if cg['deleted'] or cg['hidden']:
            continue
        if cg['name'] != 'Monthly Variable':
            continue
        cats = []
        max_budgeted = max([c['budgeted'] for c in cg['categories']])
        for category in cg['categories']:
            info = {}
            activity = -category['activity']
            budgeted = category['budgeted']
            spent_percent = activity * 1.0 / budgeted
            total_width = 900 * (float(budgeted) / max_budgeted)
            day_of_month = max(datetime.date.today().day - 2, 1)
            funds_left = budgeted - activity
            remaining_days = DAYS_IN_MONTH - day_of_month
            info['name'] = category['name']
            info['green_width'] = total_width * (1 - spent_percent)
            info['green_left'] = total_width * spent_percent
            info['bar_left'] = day_of_month * 1.0 * total_width / DAYS_IN_MONTH
            info['per_day_par'] = budgeted * 1.0 / DAYS_IN_MONTH
            info['burst_amount'] = '$%.2f' % ((budgeted - (info['per_day_par'] * remaining_days) - activity) / 1000)
            info['per_day_so_far'] = '$%.2f' % (activity / 1000.0 / day_of_month)
            info['per_day_remaining'] = '$%.2f' % (funds_left / 1000.0 / remaining_days)
            info['total_remaining'] = '$%.2f' % (funds_left / 1000.0)
            effective_day_of_month = int(spent_percent * DAYS_IN_MONTH)
            info['days_until_balance'] = effective_day_of_month - day_of_month
            if info['days_until_balance'] <= 0:
                info['color'] = '#080'
            elif (info['days_until_balance'] * 1.0 / remaining_days) < .2:
                info['color'] = '#BB0'
            else:
                info['color'] = '#800'
            print spent_percent
            cats.append(info)
        params['cats'] = cats
        return render_template_string(TEMPLATE, **params)


def main():
    app.run('0.0.0.0', debug=True, port=5400)


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
