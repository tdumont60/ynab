import argparse
import datetime
import json
import sys
import time

from prettytable import PrettyTable

def amount(raw_amount):
    return float(raw_amount) / 1000


def main():
    data = json.loads(sys.stdin.read())

    for cg in data['categories']['data']['category_groups']:
        if cg['deleted'] or cg['hidden']:
            continue
        for c in cg['categories']:
            if c['deleted'] or c['hidden']:
                continue
            if not c['goal_type']:
                continue
            print '\t'.join(map(str, [cg['name'], c['name'], c['goal_type'], c['goal_target'] / 1000]))


if __name__ == '__main__':
    sys.exit(main())
