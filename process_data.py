import csv
import json
from collections import defaultdict

def process_csv(filepath, event_name):
    """Read CSV and return rows with event_name added."""
    rows = []
    with open(filepath, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            # Normalize path: lowercase, strip trailing slash, collapse specific IDs
            raw_path = row.get('path', '').strip()
            path = raw_path.lower().rstrip('/')
            if not path:
                path = '(unknown)'
            rows.append({
                'total_events': int(row['Total Events']),
                'date': row['Date'],
                'visitor': row['Visitor'],
                'account': row['Account'],
                'country': row['Country'],
                'event_name': event_name,
                'path': path,
            })
    return rows

def main():
    # Process both files
    off_rows = process_csv('newui_onload_off.csv', 'newui_load_off')
    on_rows = process_csv('newui_onload_on.csv', 'newui_load_on')

    all_rows = off_rows + on_rows

    # Aggregate by Visitor and Event Name
    visitor_event = defaultdict(lambda: defaultdict(int))
    for row in all_rows:
        visitor_event[row['visitor']][row['event_name']] += row['total_events']

    # Aggregate by Account and Event Name
    account_event = defaultdict(lambda: defaultdict(int))
    for row in all_rows:
        account_event[row['account']][row['event_name']] += row['total_events']

    # Aggregate by Date and Event Name
    date_event = defaultdict(lambda: defaultdict(int))
    for row in all_rows:
        date_event[row['date']][row['event_name']] += row['total_events']

    # Compute adoption metrics
    # Build visitor -> account mapping
    visitor_accounts = defaultdict(set)
    for row in all_rows:
        visitor_accounts[row['visitor']].add(row['account'])

    # Per visitor: adoption = on / (on + off)
    visitor_adoption = []
    for visitor, events in visitor_event.items():
        on = events.get('newui_load_on', 0)
        off = events.get('newui_load_off', 0)
        total = on + off
        adoption_rate = round((on / total) * 100, 1) if total > 0 else 0
        visitor_adoption.append({
            'visitor': visitor,
            'newui_load_on': on,
            'newui_load_off': off,
            'total': total,
            'adoption_rate': adoption_rate,
            'account': list(visitor_accounts[visitor])[0] if len(visitor_accounts[visitor]) == 1 else list(visitor_accounts[visitor])
        })
    visitor_adoption.sort(key=lambda x: x['total'], reverse=True)

    # Per account with per-visitor breakdown
    # First, build visitor-per-account aggregation
    account_visitor_event = defaultdict(lambda: defaultdict(lambda: defaultdict(int)))
    for row in all_rows:
        account_visitor_event[row['account']][row['visitor']][row['event_name']] += row['total_events']

    account_adoption = []
    account_visitors_detail = {}
    for account, events in account_event.items():
        on = events.get('newui_load_on', 0)
        off = events.get('newui_load_off', 0)
        total = on + off
        adoption_rate = round((on / total) * 100, 1) if total > 0 else 0
        unique_visitors = set()
        for row in all_rows:
            if row['account'] == account:
                unique_visitors.add(row['visitor'])
        account_adoption.append({
            'account': account,
            'newui_load_on': on,
            'newui_load_off': off,
            'total': total,
            'adoption_rate': adoption_rate,
            'unique_visitors': len(unique_visitors)
        })
        # Build per-visitor detail for this account
        visitors_list = []
        visitors_on_set = set()
        visitors_off_set = set()
        for visitor, v_events in account_visitor_event[account].items():
            v_on = v_events.get('newui_load_on', 0)
            v_off = v_events.get('newui_load_off', 0)
            v_total = v_on + v_off
            v_rate = round((v_on / v_total) * 100, 1) if v_total > 0 else 0
            if v_on > 0:
                visitors_on_set.add(visitor)
            if v_off > 0:
                visitors_off_set.add(visitor)
            visitors_list.append({
                'visitor': visitor,
                'newui_load_on': v_on,
                'newui_load_off': v_off,
                'total': v_total,
                'adoption_rate': v_rate
            })
        visitors_list.sort(key=lambda x: x['total'], reverse=True)
        account_visitors_detail[account] = {
            'visitors': visitors_list,
            'visitors_only_new': len(visitors_on_set - visitors_off_set),
            'visitors_only_old': len(visitors_off_set - visitors_on_set),
            'visitors_both': len(visitors_on_set & visitors_off_set),
            'visitors_total': len(visitors_on_set | visitors_off_set),
            'visitor_adoption_rate': round((len(visitors_on_set) / len(visitors_on_set | visitors_off_set)) * 100, 1) if len(visitors_on_set | visitors_off_set) > 0 else 0
        }
    account_adoption.sort(key=lambda x: x['total'], reverse=True)

    # Date trend
    date_trend = []
    for date, events in sorted(date_event.items()):
        on = events.get('newui_load_on', 0)
        off = events.get('newui_load_off', 0)
        total = on + off
        adoption_rate = round((on / total) * 100, 1) if total > 0 else 0
        date_trend.append({
            'date': date,
            'newui_load_on': on,
            'newui_load_off': off,
            'total': total,
            'adoption_rate': adoption_rate
        })

    # Summary stats
    total_on = sum(r['total_events'] for r in on_rows)
    total_off = sum(r['total_events'] for r in off_rows)
    total_all = total_on + total_off
    overall_adoption = round((total_on / total_all) * 100, 1) if total_all > 0 else 0

    unique_visitors_on = len(set(r['visitor'] for r in on_rows))
    unique_visitors_off = len(set(r['visitor'] for r in off_rows))
    unique_visitors_total = len(set(r['visitor'] for r in all_rows))
    unique_accounts_on = len(set(r['account'] for r in on_rows))
    unique_accounts_off = len(set(r['account'] for r in off_rows))
    unique_accounts_total = len(set(r['account'] for r in all_rows))

    # Compute adoption rate buckets from the account_adoption table data
    accounts_high = len([a for a in account_adoption if a['adoption_rate'] >= 80])
    accounts_medium = len([a for a in account_adoption if 50 <= a['adoption_rate'] < 80])
    accounts_low = len([a for a in account_adoption if a['adoption_rate'] < 50])

    # Visitor adoption buckets
    visitors_high = len([v for v in visitor_adoption if v['adoption_rate'] >= 80])
    visitors_medium = len([v for v in visitor_adoption if 50 <= v['adoption_rate'] < 80])
    visitors_low = len([v for v in visitor_adoption if v['adoption_rate'] < 50])

    summary = {
        'total_events_on': total_on,
        'total_events_off': total_off,
        'total_events': total_all,
        'overall_adoption_rate': overall_adoption,
        'unique_visitors_on': unique_visitors_on,
        'unique_visitors_off': unique_visitors_off,
        'unique_visitors_total': unique_visitors_total,
        'unique_accounts_on': unique_accounts_on,
        'unique_accounts_off': unique_accounts_off,
        'unique_accounts_total': unique_accounts_total,
        'visitor_adoption_rate': round((unique_visitors_on / unique_visitors_total) * 100, 1) if unique_visitors_total > 0 else 0,
        'account_adoption_rate': round((unique_accounts_on / unique_accounts_total) * 100, 1) if unique_accounts_total > 0 else 0,
        'visitors_only_new': len(set(r['visitor'] for r in on_rows) - set(r['visitor'] for r in off_rows)),
        'visitors_only_old': len(set(r['visitor'] for r in off_rows) - set(r['visitor'] for r in on_rows)),
        'visitors_both': len(set(r['visitor'] for r in on_rows) & set(r['visitor'] for r in off_rows)),
        'accounts_only_new': len(set(r['account'] for r in on_rows) - set(r['account'] for r in off_rows)),
        'accounts_only_old': len(set(r['account'] for r in off_rows) - set(r['account'] for r in on_rows)),
        'accounts_both': len(set(r['account'] for r in on_rows) & set(r['account'] for r in off_rows)),
        'accounts_high_adoption': accounts_high,
        'accounts_medium_adoption': accounts_medium,
        'accounts_low_adoption': accounts_low,
        'visitors_high_adoption': visitors_high,
        'visitors_medium_adoption': visitors_medium,
        'visitors_low_adoption': visitors_low,
    }

    # Accounts only using new UI or only old UI (with details)
    accounts_on_set = set(r['account'] for r in on_rows)
    accounts_off_set = set(r['account'] for r in off_rows)
    accounts_only_new_names = accounts_on_set - accounts_off_set
    accounts_only_old_names = accounts_off_set - accounts_on_set

    accounts_only_new_list = sorted(
        [a for a in account_adoption if a['account'] in accounts_only_new_names],
        key=lambda x: x['total'], reverse=True
    )
    accounts_only_old_list = sorted(
        [a for a in account_adoption if a['account'] in accounts_only_old_names],
        key=lambda x: x['total'], reverse=True
    )

    # Accounts using both UIs
    accounts_both_names = accounts_on_set & accounts_off_set
    accounts_both_list = sorted(
        [a for a in account_adoption if a['account'] in accounts_both_names],
        key=lambda x: x['total'], reverse=True
    )

    # Path insights - aggregate events by path and UI version
    import re
    def normalize_path(p):
        """Collapse numeric IDs and UUIDs to generic placeholders for grouping."""
        p = re.sub(r'/[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}', '/{uuid}', p)
        p = re.sub(r'/\d+', '/{id}', p)
        # Remove URL-encoded segments after tradingpartners
        p = re.sub(r'(/tradingpartners/[^/]+)/.*', r'\1/...', p)
        return p

    path_events = defaultdict(lambda: {'newui_load_on': 0, 'newui_load_off': 0})
    for row in all_rows:
        norm_path = normalize_path(row['path'])
        path_events[norm_path][row['event_name']] += row['total_events']

    path_insights = []
    for path, events in path_events.items():
        on = events['newui_load_on']
        off = events['newui_load_off']
        total = on + off
        rate = round((on / total) * 100, 1) if total > 0 else 0
        path_insights.append({
            'path': path,
            'newui_load_on': on,
            'newui_load_off': off,
            'total': total,
            'adoption_rate': rate,
        })
    path_insights.sort(key=lambda x: x['total'], reverse=True)

    # Per-account top paths (top 5 paths per account)
    account_path_events = defaultdict(lambda: defaultdict(lambda: {'newui_load_on': 0, 'newui_load_off': 0}))
    for row in all_rows:
        norm_path = normalize_path(row['path'])
        account_path_events[row['account']][norm_path][row['event_name']] += row['total_events']

    account_paths = {}
    for account, paths in account_path_events.items():
        acct_paths = []
        for path, events in paths.items():
            on = events['newui_load_on']
            off = events['newui_load_off']
            total = on + off
            rate = round((on / total) * 100, 1) if total > 0 else 0
            acct_paths.append({'path': path, 'on': on, 'off': off, 'total': total, 'rate': rate})
        acct_paths.sort(key=lambda x: x['total'], reverse=True)
        account_paths[account] = acct_paths[:5]

    output = {
        'summary': summary,
        'date_trend': date_trend,
        'account_adoption': account_adoption,  # All accounts
        'account_visitors': {a['account']: account_visitors_detail[a['account']] for a in account_adoption},  # All accounts with visitor details
        'visitor_adoption': visitor_adoption,   # All visitors
        'accounts_only_new_list': accounts_only_new_list,
        'accounts_only_old_list': accounts_only_old_list,
        'accounts_both_list': accounts_both_list,
        'path_insights': path_insights,
        'account_paths': account_paths,
    }

    # Raw data aggregated by date + visitor + account
    raw_agg = defaultdict(lambda: {'newui_load_on': 0, 'newui_load_off': 0})
    country_lookup = {}
    for row in all_rows:
        key = (row['date'], row['visitor'], row['account'])
        raw_agg[key][row['event_name']] += row['total_events']
        country_lookup[key] = row['country']

    raw_data = []
    for (date, visitor, account), events in raw_agg.items():
        on = events['newui_load_on']
        off = events['newui_load_off']
        total = on + off
        rate = round((on / total) * 100, 1) if total > 0 else 0
        raw_data.append({
            'd': date,
            'v': visitor,
            'a': account,
            'c': country_lookup[(date, visitor, account)],
            'on': on,
            'off': off,
            't': total,
            'r': rate
        })
    raw_data.sort(key=lambda x: (x['d'], x['a'], x['v']))

    # Get unique filter values
    countries = sorted(set(r['country'] for r in all_rows))
    dates = sorted(set(r['date'] for r in all_rows))
    accounts_list = sorted(set(r['account'] for r in all_rows))

    output['raw_data'] = raw_data
    output['filters'] = {
        'countries': countries,
        'dates': dates,
        'accounts': accounts_list,
    }

    with open('adoption_data.json', 'w', encoding='utf-8') as f:
        json.dump(output, f)

    print(f"Data processed successfully!")
    print(f"Total events: {total_all:,}")
    print(f"New UI events: {total_on:,} | Old UI events: {total_off:,}")
    print(f"Overall adoption rate: {overall_adoption}%")
    print(f"Unique visitors: {unique_visitors_total:,}")
    print(f"Unique accounts: {unique_accounts_total:,}")

if __name__ == '__main__':
    main()
