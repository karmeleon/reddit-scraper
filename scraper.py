import argparse
import datetime
import json
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
    parser.add_argument('--sub', help='Subreddit to scrape (e.g. "me_irl")')
    parser.add_argument('--sub_list', help='Path to a .txt file with one subreddit name per line to scrape')
    parser.add_argument('--field_list', help='Path to a .txt file with one field per line to keep from posts. If not supplied, keep all fields.')
    parser.add_argument('--start_date', help='Start date in YYYY-MM-DD format (starts at 00:00 UTC)', action=DateAction)
    parser.add_argument('--end_date', help='End date in YYYY-MM-DD format ends at (23:59:59 UTC)', action=DateAction)
    parser.add_argument('--count', type=int, default=1000, help='A maximum amount of posts to download for each provided subreddit')
    parser.add_argument('--update', help='Update the data from the Reddit API after downloading it. Recommended for anything that requires up-to-date karma counts.', action='store_true')

    args = parser.parse_args()

    if not args.sub_list and not args.sub:
        print('You must provide either --sub or --sub_list.')
        exit(1)
    
    """
    Things that are okay:
    - Supplying a start_date, end_date, and count
    - Supplying a start_date and an end_date
    - Supplying a start_date and a count
    - Supplying only a count
    """
    if not ((args.start_date is not None and args.end_date is not None) or (args.start_date is not None and args.count is not None) or (args.count is not None)):
        print('Invalid combination of --start_date, --end_date, and --count. Make sure these arguments make sense.')
        exit(1)

    if args.sub_list:
        subreddits = read_lines_of_file(args.sub_list)
    else:
        subreddits = [args.sub]
    
    if args.field_list:
        fields = read_lines_of_file(args.field_list)
    
    for subreddit in subreddits:
        scrape_subreddit(
            subreddit,
            args.update,
            args.count,
            fields,
            args.start_date if args.start_date else datetime.datetime(2000, 1, 1),
            args.end_date if args.end_date else datetime.datetime.now(),    
        )
    
def read_lines_of_file(path):
    with open(path, 'r') as f:
        return [line.strip() for line in f.readlines()]

def scrape_subreddit(subreddit, update, count, fields, start_date, end_date):
    print(f'Scraping {subreddit}')
    if update:
        reddit = login_to_reddit()

    end_epoch = int(start_date.timestamp())
    # add 23 hours, 59 minutes, 59 seconds to include the posts made on end_date
    start_epoch = int((end_date + datetime.timedelta(days=1) - datetime.timedelta(seconds=1)).timestamp())
    current_epoch = start_epoch

    output = []

    while len(output) < count or count is None:
        payload = {
            'subreddit': subreddit,
            'sort': 'desc',
            'size': 500,
            'before': current_epoch,
            'after': end_epoch,
            'sort_type': 'created_utc',
        }
        posts = query_pushshift(payload)
        ids = [f't3_{post["id"]}' for post in posts]
        if len(posts) == 0:
            break
        
        # Zip with some reddit info if we plan on updating stuff
        if update:
            zipped_posts = zip(posts, reddit.info(ids))
        else:
            zipped_posts = zip(posts, [None] * len(posts))

        for post, submission in zipped_posts:
            # Update the time of the last post we downloaded
            current_epoch = int(post['created_utc'])
            # Lose the fields we don't care about
            if fields:
                post = keep_whitelisted_fields(post, fields)
            # Query reddit for up-to-date info on fields we need to update
            if update:
                for field in FIELDS_TO_UPDATE:
                    if field in post:
                        post[field] = getattr(submission, field)
            # Stick it on the end
            output.append(post)
            if len(output) % 500 == 0:
                print(f'Downloaded {len(output)} posts so far')
    
    output_path = os.path.abspath(f'{subreddit}-{datetime.datetime.fromtimestamp(start_epoch).strftime("%Y-%m-%d")}-{datetime.datetime.fromtimestamp(end_epoch).strftime("%Y-%m-%d")}.json')

    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(output, f, ensure_ascii=False)
    
    print(f'Downloaded {len(output)} posts from {subreddit}.')

def keep_whitelisted_fields(post, whitelist):
    output = {}
    for field in whitelist:
        output[field] = post[field]
    return output

def login_to_reddit():
    if not os.path.isfile('praw.ini'):
        print("Couldn't find praw.ini in this directory! Try making one if this breaks: https://praw.readthedocs.io/en/latest/getting_started/configuration/prawini.html")
        exit(1)

    reddit = praw.Reddit('DEFAULT', user_agent='python:reddit-scraper:v0.2.0 (by /u/notverycreative1)')
    print('Logged in!')
    return reddit

def query_pushshift(payload):
    """
    Query the pushshift API.
    :param payload: Payload of params to query with
    :returns: list of post objects
    """
    response = r.get('https://api.pushshift.io/reddit/search/submission', params=payload)
    return [post for post in response.json()['data']]

if __name__ == '__main__':
    main()
