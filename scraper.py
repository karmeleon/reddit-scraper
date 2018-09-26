import argparse
import datetime
import json
import shutil
import os
import os.path

import praw
import requests as r

FIELDS_TO_UPDATE = [
    'locked',
    'num_comments',
    'num_crossposts',
    'over_18',
    'pinned',
    'score',
    'selftext',
    'spoiler',
    'stickied',
    'subreddit_subscribers',
]

class DateAction(argparse.Action):
    def __call__(self, parser, namespace, values, option_string):
        try:
            setattr(namespace, self.dest, datetime.datetime.strptime(values, '%Y-%m-%d'))
        except ValueError:
            raise ValueError(f'{values} is not a valid YYYY-MM-DD date')

def main():
    parser = argparse.ArgumentParser(description='Chronologically scrape reddit')
    parser.add_argument('sub', help='Subreddit to scrape (e.g. "me_irl")')
    parser.add_argument('start_date', help='Start date in YYYY-MM-DD format (starts at 00:00 UTC)', action=DateAction)
    parser.add_argument('end_date', help='End date in YYYY-MM-DD format ends at (23:59:59 UTC)', action=DateAction)
    parser.add_argument('--overwrite', help='If included, overwrite the output file if it exists', action='store_true')

    args = parser.parse_args()

    path = os.path.abspath(f'{args.sub}-{args.start_date.strftime("%Y-%m-%d")}-{args.end_date.strftime("%Y-%m-%d")}.json')

    if os.path.isfile(path):
        if not args.overwrite:
            print('The output file already exists, exiting')
            exit(1)
        os.remove(path)

    if not os.path.isfile('praw.ini'):
        print("Couldn't find praw.ini in this directory! Try making one if this breaks: https://praw.readthedocs.io/en/latest/getting_started/configuration/prawini.html")

    reddit = praw.Reddit('DEFAULT', user_agent='python:reddit-scraper:v0.0.1 (by /u/notverycreative1)')

    print('Logged in!')

    start_epoch = int(args.start_date.timestamp())
    # add 23 hours, 59 minutes, 59 seconds to include the posts made on end_date
    end_epoch = int((args.end_date + datetime.timedelta(days=1) - datetime.timedelta(seconds=1)).timestamp())
    current_epoch = start_epoch

    output = []

    while True:
        payload = {
            'subreddit': args.sub,
            'sort': 'asc',
            'size': 500,
            'after': current_epoch,
            'before': end_epoch,
            'sort_type': 'created_utc',
        }
        posts = query_pushshift(payload)
        ids = [f't3_{post["id"]}' for post in posts]
        if len(posts) == 0:
            break
        for json_post, submission in zip(posts, reddit.info(ids)):
            for field in FIELDS_TO_UPDATE:
                json_post[field] = getattr(submission, field)
            current_epoch = int(submission.created_utc)
            output.append(json_post)
            if len(output) % 500 == 0:
                print(f'Downloaded {len(output)} posts so far')
    
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(output, f, ensure_ascii=False)

    print(f'All done! Downloaded {len(output)} posts.')


def query_pushshift(payload):
    """
    Query the pushshift API.
    :param payload: Payload of params to query with
    :returns: list of post objects
    """
    response = r.get('https://api.pushshift.io/reddit/search/submission', params=payload)
    return [post for post in response.json()['data']]

def get_post_range(sub, start_date, end_date):
    """
    Get the submission epochs of the first and last submissions in the range
    :param sub: subreddit to retrieve from
    :param date: datetime of date to retrieve from
    :returns: tuple of (start_id, end_id)
    """
    payload = {
        'subreddit': sub,
        'sort': 'desc',
        'size': 1,
        'after': int(start_date.timestamp()),
        # add 23 hours, 59 minutes, 59 seconds to include the posts made on end_date
        'before': int((end_date + datetime.timedelta(days=1) - datetime.timedelta(seconds=1)).timestamp()),
        'sort_type': 'created_utc',
        'fields': 'id',
    }

    start_payload = payload.copy()
    start_payload['sort'] = 'asc'

    end_payload = payload.copy()
    end_payload['sort'] = 'desc'

    start_id = query_pushshift(start_payload)[0]['id']
    end_id = query_pushshift(end_payload)[0]['id']

    return start_id, end_id

if __name__ == '__main__':
    main()
