# reddit-scraper
A small Python script to scrape Reddit posts by date.

## Installation

Requires Python >= 3.6. A virtualenv is recommended, but not required. Before continuing, place a [`praw.ini`](https://praw.readthedocs.io/en/latest/getting_started/configuration/prawini.html) file in the root of the directory, with the `[DEFAULT]` section filled out with your client ID and secret.

    pip3 install -r requirements.txt
    python3 scraper.py -h

When complete, it'll dump a `json` file in the cwd with your data.

## Limitations

* Only post data is scraped; comments are not.
* There is no save/resume feature, so don't ctrl+C it before you're done!
  * It's pretty fast, though, so it shouldn't take too long to complete.
* The data is saved in memory before being dumped to a file at the very end, so scraping a popular subreddit for a long timespan may cause issues with RAM usage.
  * 100,000 posts use about 450MB of RAM and dump to 180MB on disk, for reference.
  * If you find yourself running out of RAM and swap, you can always scrape a smaller timespan and splice them together manually. PRs are also accepted! 😉
