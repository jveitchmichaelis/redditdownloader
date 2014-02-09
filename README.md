redditdownloader
================

Simple python/praw based reddit image downloader.

Simply call the script with a Redditor and it will locate all their imgur submissions and download them to a folder (currently a folder named _username_ in the script directory).  This script requires PRAW:

    pip install praw

As per Reddit API rules this uses a custom user-agent, you can change this if you want.

The script searches for either imgur galleries, which it will scrape, or i.imgur links which are directly downloaded.  Duplicate files are naively detected to save bandwidth.

Usage
=====

python reddit\_downloader.py _username_


