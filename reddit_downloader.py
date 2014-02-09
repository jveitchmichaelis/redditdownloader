import urllib2, sys, re, os, praw

def downloadimage(url, file_name):
    """
    Credit to: https://stackoverflow.com/users/394/pablog for the status bar.
    """
    try:
        u = urllib2.urlopen(url)
        f = open(file_name, 'wb')
        meta = u.info()
        file_size = int(meta.getheaders("Content-Length")[0])
        print "Downloading: %s Bytes: %s" % (file_name, file_size)

        file_size_dl = 0
        block_sz = 8192
        while True:
            buffer = u.read(block_sz)
            if not buffer:
                break

            file_size_dl += len(buffer)
            f.write(buffer)
            status = r"%10d  [%3.2f%%]" % (file_size_dl, file_size_dl * 100. / file_size)
            status = status + chr(8)*(len(status)+1)
            print status,

        f.close()
    except:
        print "Download failed."


if __name__ == "__main__":
    
    # Make sure we've got a unique user agent to use the Reddit API.
    r = praw.Reddit(user_agent='Image Downloader /u/your-reddit-name')
    
    # Get the Redditor.
    if len(sys.argv) > 1:
        username = sys.argv[1]
    else:
        username = raw_input("Enter a username: ")
        
    # Basefolder in the current directory, but will probably add a command line flag for this.
    
    basefolder = "./"+username+"/"
    
    if not os.path.exists(basefolder):
        os.makedirs(basefolder)
    
    # API call to get the submissions from this user. Save as a set to
    # ignore duplicates.  We only allow imgur links!
    
    urls = []
    
    for submission in r.get_redditor(username).get_submitted(limit=None):
        url = submission.url
        if "imgur" in url and "i.imgur" not in url:
            urls.append(str(submission.url))
        if "i.imgur" in url:
            fname = re.findall(r'.com/([^\'" >]+\.(jpg|png|gif|apng|tiff|bmp|pdf|xcf))', url)[0][0]
            if not os.path.isfile(fname):
                downloadimage(url, basefolder+fname)
    
    urls = set(urls)
    
    
        
    # Feedback to the user:
    url = "http://www.reddit.com/user/"+username+"/submitted/"
    
    print "Downloading from: " + url
    print "Saving to: " + basefolder
    
    imagelist = set()
    
    print "Found "+str(len(urls))+" imgur links"
    
    # For each image gallery:
    
    for gallery in urls:
        print "Getting images from:", gallery
        
        # Attempt to open the image gallery
        try:
            request = urllib2.urlopen(gallery)
            
            data = ' '.join(request.readlines())
        
            # Regex to strip out all the image names
        
            images = re.findall(r'href=[\'"]?(//i\.imgur.com/[^\'" >]+)', data)
            images = ["http://"+image[2:] for image in images]
        
            imagelist.update(images)
        except urllib2.HTTPError:
            print "404, page not found!"
            
    print "Found "+str(len(imagelist))+" images."
    # For each image, download it if it doesn't already exist.
    for image in imagelist:
        fname = re.findall(r'.com/([^\'" >]+\.(jpg|png|gif|apng|tiff|bmp|pdf|xcf))', image)[0][0]
        if not os.path.isfile(fname):
            downloadimage(image, basefolder+fname)
