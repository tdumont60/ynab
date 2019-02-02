import argparse
import datetime
import json
import sys
import time

from prettytable import PrettyTable

def amount(raw_amount):
    return float(raw_amount) / 1000


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
    data['months'].sort(key=lambda m: m['month'])

    goal_total = 0

    for category in sorted(data['months'][-1]['categories'], key=lambda c: c['name']):
        category_id = category['id']
        category_name = category['name']
        if category['hidden']:
            continue

        if category['goal_type'] != 'MF':
            continue
        goal_total += float(category['goal_target']) / 1000

        months = []
        table = PrettyTable(field_names=['Month', 'Start', 'Start Months', 'Budgeted', 'Spent', 'End', 'End Months'])
        for i, month in enumerate(data['months']):
            stats = {}
            budgeted_total = 0

            for c in month['categories']:
                if c['name'] == category_name:
                    category_data = c
                    break

            goal = float(category_data['goal_target']) / 1000
            stats['name'] = month['month'][:7]
            if i > 0:
                stats['start'] = months[i - 1]['end']
            else:
                stats['start'] = 0
            stats['budgeted'] = amount(category_data['budgeted'])
            stats['spent'] = abs(amount(category_data['activity']))
            if stats['name'] == today.strftime('%Y-%m'):
                if today.day > 10:
                    proj_spend = (stats['spent'] * 30 / today.day)
                else:
                    proj_spend = max([months[-1]['spent'], stats['spent']])
                stats['end'] = stats['start'] + stats['budgeted'] - proj_spend
                spend_str = '$%.2f ($%.2f)' % (stats['spent'], proj_spend)
            else:
                stats['end']  = amount(category_data['balance'])
                spend_str = '$%.2f' % stats['spent']


            months.append(stats)
            if i > 0:
                table.add_row((stats['name'],
                               '$%.2f' % stats['start'],
                               '%.2f' % (stats['start'] / goal),
                               '$%.2f' % stats['budgeted'],
                               spend_str,
                               '$%.2f' % stats['end'],
                               '%.2f' % (stats['end'] / goal)))

            # this_month_projected_end = this_month_start + this_month_budgeted - this_month_projected_spent
            # this_month_months_now = this_month_current / goal
            # this_month_months_at_start = this_month_start / goal
            # this_month_months_at_end = this_month_projected_end / goal

            # last_month_budgeted_total += last_month_budgeted
            # this_month_budgeted_total += this_month_budgeted
            # this_month_goal_total += goal
        print '* %s: $%.2f/month' % (category_name, goal)
        print table

        table = PrettyTable(field_names=['Date', 'Payee', 'Amount'])
        for trans in data['transactions']:
            if trans['date'][:7] in (months[-1]['name'], months[-2]['name']):
                if trans['category_name'] == category_name:
                    table.add_row(transaction_row(trans['date'], trans['payee_name'], trans['memo'], trans['amount']))
                if trans['subtransactions']:
                    for subtrans in trans['subtransactions']:
                        if category_id == subtrans['category_id']:
                            table.add_row(transaction_row(trans['date'], trans['payee_name'], subtrans['memo'], subtrans['amount']))
        print table

        #print '%s balance now: $%.2f (%.1f months if no more spent this month)' % (this_month_name, this_month_current, this_month_months_now)
        #print '%s projected $%.2f (%.1f months at end of month)' % (this_month_name, this_month_projected_spent, this_month_months_at_end)

        print

    #this_month_total_income = float(this_month_all['income']) / 1000
    #print '*** LAST MONTH TOTAL: $%.2f income, $%.2f ***' % (float(last_month_all['income']) / 1000, last_month_budgeted_total)
    #print '*** THIS MONTH TOTAL: $%.2f income, $%.2f budgeted, $%.2f surplus ***' % (this_month_total_income, this_month_budgeted_total, this_month_total_income - this_month_budgeted_total)
    print 'GOAL RUN RATE: $%.2f/month ($%.2f/year)' % (goal_total, goal_total * 12)

def transaction_row(date, payee, memo, amount):
    desc = payee
    if memo:
        desc += ' (%s)' % memo
    return (date, desc, '$%.2f' % (-float(amount)/1000.0))

if __name__ == '__main__':
    sys.exit(main())
