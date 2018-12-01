import argparse
import datetime
import json
import sys
import time

from prettytable import PrettyTable

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--pretend-today', dest='pretend_today')
    args = parser.parse_args()
    if args.pretend_today:
        try:
            today = datetime.date(*time.strptime(args.pretend_today, '%Y-%m-%d')[:3])
        except ValueError:
            print 'Invalid date "%s" for pretend-today (expected YYYY-MM-DD)' % args.pretend_today
            sys.exit(1)
    else:
        today = datetime.date.today()

    data = json.loads(sys.stdin.read())

    # filter out future months and sort
    data['months'] = filter(lambda m: m['month'] <= today.strftime('%Y-%m-%d'), data['months'])
    data['months'].sort(key=lambda m: m['month'], reverse=True)

    this_month_all = data['months'][0]
    last_month_all = data['months'][1]
    this_month_goal_total = 0
    last_month_budgeted_total = 0
    this_month_budgeted_total = 0

    for category_this in sorted(this_month_all['categories'], key=lambda c: c['name']):
        category_name = category_this['name']

        if category_this['hidden']:
            continue

        if category_this['goal_type'] != 'MF':
            continue

        for c in last_month_all['categories']:
            if c['name'] == category_name:
                category_last = c
                break

        name = category_this['name']
        goal = float(category_this['goal_target']) / 1000
        this_month_name = this_month_all['month'][:7]
        last_month_name = last_month_all['month'][:7]
        last_month_start = float(category_last['balance'] - category_last['activity'] - category_last['budgeted']) / 1000
        last_month_budgeted = float(category_last['budgeted']) / 1000
        last_month_months_at_start = last_month_start / goal
        last_month_spent = abs(float(category_last['activity']) / 1000)
        this_month_start = float(category_last['balance']) / 1000
        this_month_budgeted = float(category_this['budgeted']) / 1000
        this_month_current = float(category_this['balance']) / 1000
        this_month_spent = abs(float(category_this['activity']) / 1000)
        if today.day > 10:
            this_month_projected_spent = (this_month_spent * 30 / today.day)
        else:
            this_month_projected_spent = max([last_month_spent, this_month_spent])
        this_month_projected_end = this_month_start + this_month_budgeted - this_month_projected_spent
        this_month_months_now = this_month_current / goal
        this_month_months_at_start = this_month_start / goal
        this_month_months_at_end = this_month_projected_end / goal

        last_month_budgeted_total += last_month_budgeted
        this_month_budgeted_total += this_month_budgeted
        this_month_goal_total += goal

        print '* %s: $%.2f/month' % (name, goal)
        print '%s balance: $%.2f (%.1f months)' % (last_month_name, last_month_start, last_month_months_at_start)
        print '%s spent $%.2f' % (last_month_name, last_month_spent)
        print '%s start balance: $%.2f (%.1f months)' % (this_month_name, this_month_start, this_month_months_at_start)
        print '%s budgeted $%.2f, spent $%.2f so far' % (this_month_name, this_month_budgeted, this_month_spent)
        table = PrettyTable(field_names=['Date', 'Payee', 'Amount'])
        for trans in data['transactions']:
            if trans['date'][:7] in (this_month_name, last_month_name):
                if trans['category_name'] == name:
                    table.add_row(transaction_row(trans['date'], trans['payee_name'], trans['memo'], trans['amount']))
                if trans['subtransactions']:
                    for subtrans in trans['subtransactions']:
                        if category_this['id'] == subtrans['category_id']:
                            table.add_row(transaction_row(trans['date'], trans['payee_name'], subtrans['memo'], subtrans['amount']))
        print table

        print '%s balance now: $%.2f (%.1f months if no more spent this month)' % (this_month_name, this_month_current, this_month_months_now)
        print '%s projected $%.2f (%.1f months at end of month)' % (this_month_name, this_month_projected_spent, this_month_months_at_end)

        print

    this_month_total_income = float(this_month_all['income']) / 1000
    print '*** LAST MONTH TOTAL: $%.2f income, $%.2f ***' % (float(last_month_all['income']) / 1000, last_month_budgeted_total)
    print '*** THIS MONTH TOTAL: $%.2f income, $%.2f budgeted, $%.2f surplus ***' % (this_month_total_income, this_month_budgeted_total, this_month_total_income - this_month_budgeted_total)
    print 'GOAL RUN RATE: $%.2f/month ($%.2f/year)' % (this_month_goal_total, this_month_goal_total * 12)

def transaction_row(date, payee, memo, amount):
    desc = payee
    if memo:
        desc += ' (%s)' % memo
    return (date, desc, '$%.2f' % (-float(amount)/1000.0))

if __name__ == '__main__':
    sys.exit(main())
