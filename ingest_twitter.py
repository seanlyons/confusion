import base64
from collections import OrderedDict
import datetime
import pdb
import pprint
import requests
import simplejson
import sqlite3
import sys
import time
from urllib.parse import urlencode
import yaml

#to see your tweets: 
# > python ingest_twitter.py  | jq '.[].text'

with open("secrets.yaml", 'r') as stream:
    try:
        secrets = yaml.load(stream)
    except yaml.YAMLError as exc:
        print(exc)
        sys.exit()

pp = pprint.PrettyPrinter(indent=4)

toEncode = secrets['consumerKey'] + ':' + secrets['consumerSecret']

base64Encoded = (base64.standard_b64encode(toEncode.encode("utf-8"))).decode("utf-8")
#print(toEncode + ' -> ' + base64Encoded)

'''
from: https://dev.twitter.com/oauth/application-only

POST /oauth2/token HTTP/1.1
Host: api.twitter.com
User-Agent: My Twitter App v1.0.23
Authorization: Basic eHZ6MWV2RlM0d0VFUFRHRUZQSEJvZzpMOHFxOVBaeVJn
                     NmllS0dFS2hab2xHQzB2SldMdzhpRUo4OERSZHlPZw==
Content-Type: application/x-www-form-urlencoded;charset=UTF-8
Content-Length: 29
Accept-Encoding: gzip

grant_type=client_credentials
'''
def obtainBearerToken(base64Encoded):
    s = requests.Session()
    url = 'https://api.twitter.com/oauth2/token'
    data = {
        'grant_type': 'client_credentials'
    }
    headers = {
        'User-Agent': 'conical v0.0.1',
        'Authorization': 'Basic ' + str(base64Encoded),
        'Content-Type': 'application/x-www-form-urlencoded;charset=UTF-8',
        'Accept-Encoding': 'gzip'
    }

    req = requests.Request('POST', 'https://api.twitter.com/oauth2/token', data=data, headers=headers)
    prepped = req.prepare()

    resp = s.send(prepped)

    if resp.status_code != requests.codes.ok:
        print('Error: ['+ str(resp.status_code) +'] '+ str(resp.content))
        sys.exit()

    json = simplejson.loads(resp.content)
    return json['access_token']

def call(bearerToken, userName, params={}):
    '''
    GET /1.1/statuses/user_timeline.json?count=100&screen_name=twitterapi HTTP/1.1
    Host: api.twitter.com
    User-Agent: My Twitter App v1.0.23
    Authorization: Bearer AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA%2FAAAAAAAAAAAA
                        AAAAAAAA%3DAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA
    Accept-Encoding: gzip
    '''
    s = requests.Session()

    baseUrl = 'https://api.twitter.com/1.1/favorites/list.json'

    queryParams = {
        'count': 200,
        'screen_name': userName,
        'tweet_mode': 'extended',
    }
    if params:
        for k,v in params.items():
            queryParams[k] = v


    url = baseUrl + '?' + urlencode(queryParams)
    headers = {
        'User-Agent': 'conical v0.0.1',
        'Authorization': 'Bearer ' + bearerToken,
        'Content-Type': 'application/x-www-form-urlencoded;charset=UTF-8',
        'Accept-Encoding': 'gzip'
    }

    req = requests.Request('GET', url, headers=headers)
    prepped = req.prepare()

    resp = s.send(prepped)

    return simplejson.loads(resp.content)

def colorize(string, n):
    attr = []
    if n % 2 == 0:
        # green
        attr.append('32')
    else:
        # red
        attr.append('31')
    return '\x1b[%sm%s\x1b[0m' % (';'.join(attr), string)

def sqliteConnect():
    db_file = "twitter.db"

    try:
        return sqlite3.connect(db_file)
    except Exception as e:
        print('sqliteConnect ERROR: ' + str(e) + ' for db_file: ' + colorize(db_file, 1))
        sys.exit()

def sqliteStatement(conn, statement, variables):
    try:
        c = conn.cursor()
        c.execute(statement, variables)

        return c.fetchall()
    except Exception as e:
        print('sqliteStatement ERROR: ' + str(e) + " for statement: \n\n" + colorize(statement, 1))
        sys.exit()

def distributeTweet(conn, tweet):
    #desired fields:
    '''
        created_at
        id_str
        text
        user.id_str
        user.description
        user.name
        user.profile_image_url
        user.screen_name
        quoted_status.text
        quoted_status.id
        quoted_status.user.id_str
        quoted_status.user.description
        quoted_status.user.name
        quoted_status.user.profile_image_url
        quoted_status.user.screen_name
        quoted_status.created_at
        entities.urls[].expanded_url
        extended_entities.media[].media_url
        extended_entities.media[].url
        extended_entities.media[].sizes.large.[w,h]
    '''

    if not isinstance(tweet, dict) or not tweet.get('created_at'):
        print('Tweet missing created_at element: ' + str(tweet))
        sys.exit()

    unixTime = datetime.datetime.strptime(tweet['created_at'], '%a %b %d %H:%M:%S +0000 %Y').strftime('%s')
    unixTime = int(unixTime)
    addTweetStatement = "INSERT OR IGNORE INTO tw_tweets (tw_created_at, tw_id, tw_full_text, tw_user, tw_api_content) VALUES (?, ?, ?, ?, ?)"
    
    #pdb.set_trace()
    jsonTweet = simplejson.dumps(tweet)
    
    addTweetVariables = (unixTime, tweet['id'], tweet['full_text'], tweet['user']['id'], jsonTweet)
    sqliteStatement(conn, addTweetStatement, addTweetVariables)
    
    addUserStatement = "INSERT OR IGNORE INTO tw_users (added_by, tw_id, tw_screen_name, tw_description, tw_name, tw_profile_image_url) VALUES (?, ?, ?, ?, ?, ?)"
    addUserVariables = (1, tweet['user']['id'], tweet['user']['screen_name'], tweet['user']['description'], tweet['user']['name'], tweet['user']['profile_image_url'])
    sqliteStatement(conn, addUserStatement, addUserVariables)

    addFavoritesStatement = "INSERT OR IGNORE INTO favorites (owner, added, contextual_id, favorite_type) VALUES (?, ?, ?, ?)"
    addFavoritesVariables = (1, int(time.time()), tweet['id'], 1)
    sqliteStatement(conn, addFavoritesStatement, addFavoritesVariables)

    if tweet.get('extended_entities') and tweet['extended_entities'].get('media'):
        print(simplejson.dumps(tweet))
        for media in tweet['extended_entities']['media']:
            dims_ratio = (media['sizes']['large']['w'] / media['sizes']['large']['h'])
            if media['type'] == 'video' or media['type'] == 'animated_gif':
                addMediaStatement = "INSERT OR IGNORE INTO tw_entities (tweet_id, media_type, media_url, media_preview, dims_ratio) VALUES (?, ?, ?, ?, ?)"
                addMediaVariables = (tweet['id'], media['type'], media['video_info']['variants'][0]['url'], media['media_url'], dims_ratio)            
            elif media['type'] == 'photo':
                addMediaStatement = "INSERT OR IGNORE INTO tw_entities (tweet_id, media_type, media_url, dims_ratio) VALUES (?, ?, ?, ?)"
                addMediaVariables = (tweet['id'], media['type'], media['media_url'], dims_ratio)
            sqliteStatement(conn, addMediaStatement, addMediaVariables)


def callLoop(conn, bearerToken, offset, i):
    params = {}
    if offset != 0:
        params['max_id'] = offset

    tweets = call(bearerToken, secrets['userName'], params)

    if not isinstance(tweets, list) and tweets.get('errors'):
        print(colorize('ERROR: '+ tweets['errors'][0]['message'], 1))
        sys.exit()

    if not tweets:
        print(str(i) + ' tweet ingested. after >> ' + str(params))
        sys.exit()

    for tweet in tweets:
        i += 1
        distributeTweet(conn, tweet)
        lastTweet = tweet['id_str']

    conn.commit()

    return lastTweet, i

conn = sqliteConnect()
bearerToken = obtainBearerToken(base64Encoded)
offset = 0
i = 0
for n in range(1, 20):
    offset, i = callLoop(conn, bearerToken, offset, i)
