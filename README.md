redditdownloader
================

Simple python/praw based reddit image downloader.

Simply call the script with a username or subreddit and it will process all submissions and download them to a folder (nominally `downloads/<query_type>/<query>` e.g. `downloads/subreddit/casualuk`.  This script requires a few libraries like PRAW.

```bash
    pip install -r requirements.txt
```

As per Reddit API rules this uses a custom user-agent, you can change this if you want. You should [create your own OAuth application](https://praw.readthedocs.io/en/stable/getting_started/authentication.html#oauth) and add the credentials to a `.env` file, like:

```bash
# Contents of .env
client_secret=<your key>
client_id=<your id>
```

The script searches for either imgur and reddit galleries, or i.imgur/i.redd.it links which are directly downloaded.  Duplicate files (e.g. x-posting) are detected via sha265 hashes.

Usage
=====

Run:

```bash
python reddit_downloader.py
```

Options:

```bash
    reddit_downloader.py [-h] [--subreddit SUBREDDIT | --username USERNAME]

        options:
        -h, --help            show this help message and exit
        --subreddit SUBREDDIT
                                Subreddit to scrape
        --username USERNAME   User to scrape
```