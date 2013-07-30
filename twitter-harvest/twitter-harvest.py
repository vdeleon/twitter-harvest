##############################################################################
#
# Copyright (c) 2012 ObjectLabs Corporation
#
# Permission is hereby granted, free of charge, to any person obtaining
# a copy of this software and associated documentation files (the
# "Software"), to deal in the Software without restriction, including
# without limitation the rights to use, copy, modify, merge, publish,
# distribute, sublicense, and/or sell copies of the Software, and to
# permit persons to whom the Software is furnished to do so, subject to
# the following conditions:
#
# The above copyright notice and this permission notice shall be
# included in all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
# EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF
# MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND
# NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE
# LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION
# OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION
# WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
################################################################################

#!/usr/bin/env python

__author__ = 'mongolab'


import pymongo
import oauth2 as oauth
import urllib2, json
import sys, argparse, time 


def oauth_header(url, consumer, token):
    params =  {'oauth_version': '1.0',
               'oauth_nonce': oauth.generate_nonce(),
               'oauth_timestamp': int(time.time()),
              }
    req = oauth.Request(method = 'GET',url = url, parameters = params)
    req.sign_request(oauth.SignatureMethod_HMAC_SHA1(),consumer, token)
    head = req.to_header()['Authorization'].encode('utf-8')
    return head


def main():
    
    ### Build arg parser
    parser = argparse.ArgumentParser(description = 'Connects to Twitter User Timeline endpoint, retrieves tweets and inserts into a MongoLab database. Developed on Python 2.7')
    parser.add_argument('-r', '--retweet', help = 'include native retweets in the harvest', action = 'store_true')
    parser.add_argument('-d', '--display', help = 'print harvested tweets in shell.', action = 'store_true')
    parser.add_argument('--numtweets', help = 'set total number of tweets to be harvested. max = 3200', type = int, default = 3200)
    parser.add_argument('--user', help = 'choose user timeline for harvest', default = 'mongolab')
    parser.add_argument('--db', help = 'MongoLab DB URI, example: mongodb://dbuser:dbpassword@dbh85.mongolab.com:port/dbname', required = True)
    parser.add_argument('--consumer-key', help = 'Consumer Key from your Twitter App OAuth settings', required = True)
    parser.add_argument('--consumer-secret', help = 'Consumer Secret from your Twitter App OAuth settings', required = True)
    parser.add_argument('--access-token', help = 'Access Token from your Twitter App OAuth settings', required = True)
    parser.add_argument('--access-secret', help = 'Access Token Secret from your Twitter App Dev Credentials', required = True)

    ### Fields for query
    args = parser.parse_args()
    user = args.user 
    numtweets = args.numtweets
    display = args.display
    retweet = args.retweet

    ### Build Signature
    CONSUMER_KEY = args.consumer_key
    CONSUMER_SECRET = args.consumer_secret
    ACCESS_TOKEN = args.access_token
    ACCESS_SECRET = args.access_secret

    ### Build Endpoint + Set Headers
    base_url = url = "https://api.twitter.com/1.1/statuses/user_timeline.json?include_entities=true&count=200&screen_name=%s&include_rts=%s" % (user, retweet)
    oauth_consumer = oauth.Consumer(key = CONSUMER_KEY, secret = CONSUMER_SECRET)
    oauth_token = oauth.Token(key = ACCESS_TOKEN, secret = ACCESS_SECRET)
 
    ### Setup MongoLab Goodness
    URI = args.db 
    conn = pymongo.MongoClient(URI)
    uri_parts = pymongo.uri_parser.parse_uri(URI)
    db_name = uri_parts['database']
    db = conn[db_name]
    db.TwitterHarvest.ensure_index("id_str", unique = True)
    
    ### Begin Harvesting
    while True:
        auth = oauth_header(url, oauth_consumer, oauth_token)
        headers = {"Authorization": auth}
        request = urllib2.Request(url, headers = headers)
        f = urllib2.urlopen(request)
        tweets = json.load(f)
        if 'errors' in tweets:
            print 'Hit rate limit, code: %s, message: %s' % (tweets['errors']['code'], tweets['errors']['message'])
            sys.exit()
        
	max_id = -1
	for tweet in tweets:
	    max_id = id_str = tweet["id_str"]
	    try:
		if numtweets == 0:
		   print 'Hit numtweets!' 
		   sys.exit()
		if display == True:
		    print tweet["text"]
		db.TwitterHarvest.save(tweet)
		numtweets-=1
	    except pymongo.errors.DuplicateKeyError:
		if len(tweets) == 1:
		    print 'No more tweets to harvest!'
		    sys.exit()    
	url = base_url + "&max_id=" + max_id

if __name__ == '__main__':
    try:
        main()
    except SystemExit as e:
        if e.code == 0:
            pass
