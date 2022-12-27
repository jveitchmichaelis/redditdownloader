import os
import re
import sys
import urllib.error
import urllib.request
from urllib.parse import urlparse
import argparse
import hashlib
import shutil
import zipfile

import praw
from imgurpython import ImgurClient
import logging
import dotenv
import tempfile
from tqdm.auto import tqdm

from clint.textui import progress

dotenv.load_dotenv()
logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

class DownloadProgressBar(tqdm):
    def update_to(self, b=1, bsize=1, tsize=None):
        if tsize is not None:
            self.total = tsize
        self.update(b * bsize - self.n)

def hash_file(filename : str):
    """Get file hash

    Parameters
    ----------
    filename : str
        File path

    Returns
    -------
        sha256 hash
    """
    h  = hashlib.sha256()
    b  = bytearray(128*1024)
    mv = memoryview(b)
    with open(filename, 'rb', buffering=0) as f:
        while n := f.readinto(mv):
            h.update(mv[:n])
    return h.hexdigest()


class RedditImageDownloader:
    """Convenience class to download most gallery types from Reddit. Currently
    limited to redd.it single and gallery posts, and Imgur galleries which
    covers the vast majority of submissions.
    """

    def __init__(self):

        assert os.path.exists(".env"), "Your credentials should be stored in a .env file"

        client_id = os.getenv("client_id", None)
        client_secret = os.getenv("client_secret", None)
        username = os.getenv("reddit_username", None)
        password = os.getenv("reddit_password", None)

        assert client_id is not None
        assert client_secret is not None
        assert username is not None
        assert password is not None

        # Make sure we've got a unique user agent to use the Reddit API.
        self.reddit = praw.Reddit(user_agent="Image Downloader /u/your-reddit-name",
                        client_id=client_id,
                        client_secret=client_secret,
                    )

        #self.imgur = ImgurClient(client_id, client_secret)

        assert self.reddit.read_only
    
    def download_imgur(self, gallery : str, prefix : str = ""):
        """Download from an Imgur Gallery.

        This function will download from an imgur gallery via the "zip"
        functionality on the platform. So it'll pull the gallery in 
        zip format and then extract to the current base folder.

        Parameters
        ----------
        gallery
            Gallery URL
        """

        if gallery[-1] == "/":
            gallery = gallery[:-2]

        gallery += "/zip"

        # Download zip:
        with tempfile.TemporaryDirectory() as tempdir:

            temp_zip = os.path.join(tempdir, "temp.zip")

            self.download_url(gallery, temp_zip)

            if not os.path.exists(temp_zip):
                return
            
            try:
                zip = zipfile.ZipFile(temp_zip)
                zip.extractall(tempdir)

                for file in zip.namelist():
                    temp_image = os.path.join(tempdir, file)
                    assert os.path.exists(temp_image)

                    hash = hash_file(temp_image)

                    if hash not in self.image_hashes:
                        shutil.copy(temp_image, os.path.join(self.basefolder, f"{prefix}_{file}"))
                        self.image_hashes[hash] = True
                    else:
                        logger.debug("Skipping previously downloaded file")
            except Exception as e:
                logger.error(f"{e}, failed to download: {gallery}")

    def download_url(self, url : str, output_path : str):
        """Download a URL with hash de-duplication. This function
        will download to a temporary location, check the downloaded
        file hash against a lookup and will only copy it if it's
        a new file. This gets rid of a lot of cross-posts if downloading
        from a users' submissions.

        Parameters
        ----------
        url
            URL
        output_path
            Path to download to
        """

        with tempfile.NamedTemporaryFile(delete=True) as tmp:
            with DownloadProgressBar(unit='B', unit_scale=True,
                                    miniters=1, desc=url.split('/')[-1], disable = logger.level < logging.INFO) as t:

                try:
                    urllib.request.urlretrieve(url, filename=tmp.name, reporthook=t.update_to)
                except urllib.error.HTTPError:
                    logger.error(f"Failed to download {url}")
                    return

                hash = hash_file(tmp.name)

                if hash not in self.image_hashes:
                    shutil.copy(tmp.name, output_path)
                    self.image_hashes[hash] = True
                else:
                    logger.debug("Skipping previously downloaded file")


    def download_submission(self, post : praw.models.Submission):
        """Download images from a submission/post

        Parameters
        ----------
        post
            PRAW post
        """
        url = post.url
        prefix = str(post)
        
        logger.debug(post.title)

        meta = vars(post)

        import json
        with open(os.path.join(self.basefolder, f"{prefix}_meta.json"), 'w') as fp:
            json.dump(meta, fp, indent=1, default=lambda o: str(o))

        if url[-4:] == ".jpg" or url[-4:] == ".png":

            fname = urlparse(url).path
            if fname[0] == '/':
                fname = fname[1:]

            if not os.path.isfile(fname):
                self.download_url(url, os.path.join(self.basefolder, f"{prefix}_{fname}"))

        elif "imgur" in url and "i.imgur" not in url:
            logger.info(f"Imgur gallery: {url}")
            self.download_imgur(url, prefix=prefix)

        elif 'i.imgur' in url or 'i.redd.it' in url:
            
            logger.debug("Direct image link")

            fname = urlparse(url).path
            if fname[0] == '/':
                fname = fname[1:]

            if not os.path.isfile(fname):
                self.download_url(url, os.path.join(self.basefolder, f"{prefix}_{fname}"))

        else:
            if hasattr(post, "gallery_data"):
                
                logger.debug("Reddit gallery")

                for img in sorted(post.gallery_data['items'], key=lambda x: x['id']):

                    media_id = img['media_id']
                    meta = post.media_metadata[media_id]

                    if meta['e'] == 'Image':
                        source = meta['s']
                        image_url = source['u']

                        fname = urlparse(image_url).path
                        if fname[0] == '/':
                            fname = fname[1:]

                        if not os.path.isfile(fname):
                            logger.debug(f"{image_url} > {fname}")
                            self.download_url(image_url, os.path.join(self.basefolder, f"{prefix}_{fname}"))
                        
    def _download_query(self, query, type="username"):

        if type == "username":
            redditor = self.reddit.redditor(query)
            posts = redditor.submissions.new(limit=None)
            self.basefolder = os.path.join("downloads", "username", query)
        elif type == "subreddit":
            sub = self.reddit.subreddit(query)
            posts = sub.new(limit=None)
            self.basefolder = os.path.join("downloads", "subreddit", query)
        
        os.makedirs(self.basefolder, exist_ok=True)

        # Collect image hashes, might take a while
        self.image_hashes = {}

        for f in os.listdir(self.basefolder):
            self.image_hashes[hash_file(os.path.join(self.basefolder, f))] = True

        for post in posts:
            self.download_submission(post)

    def download_username(self, query):
        self._download_query(query, type="username")

    def download_subreddit(self, query):
        self._download_query(query, type="subreddit")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--subreddit", help='Subreddit to scrape', type=str)
    group.add_argument("--username", help='User to scrape', type=str)

    args = parser.parse_args()

    client = RedditImageDownloader()
    if args.username:
        client.download_username(args.username)
    elif args.subreddit:
        client.download_subreddit(args.subreddit)
