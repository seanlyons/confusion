import datetime
from flask import Flask
import inspect
import pdb
from flask import render_template
from flask import request
from flask import send_from_directory
from hashlib import sha512
import random
import simplejson
import sqlite3
import sys
import time

app = Flask(__name__)
namespace = 'foon'

def context(*msg):
    if msg is None:
        print("{0}".format(whoami()))
    for m in msg:
        print("{0}: {1}".format(whoami(), m))

def whoami(): 
    frame = inspect.currentframe()
    #pdb.set_trace()
    context = inspect.getouterframes(frame)[2]
    return "{0}({1})".format(context.function, context.lineno)

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
    db_file = "confusion.db"

    try:
        return sqlite3.connect(db_file)
    except Exception as e:
        context('sqliteConnect ERROR: ' + str(e) + ' for db_file: ' + colorize(db_file, 1))
        sys.exit()

def sqliteStatement(conn, statement, variables):
    try:
        c = conn.cursor()
        c.execute(statement, variables)

        return c.fetchall()
    except Exception as e:
        context('sqliteStatement ERROR: ' + str(e) + " for statement: \n\n" + colorize(statement, 1))
        sys.exit()

def showCombo(tag1, tag2):
    conn = sqliteConnect()
    context(tag1, tag2)
    if tag1 is None:
        tag1id,tag1 = getRandomTag(conn)
    else:
        context(tag1)
        submitTag(tag1)
    if tag2 is None:
        tag2id,tag2 = getRandomTag(conn)
    else:
        context(tag2)
        submitTag(tag2)

    tag1id,tag1name = verifyTag(tag1, conn)
    context([tag1, tag1id, tag1name])
    tag2id,tag2name = verifyTag(tag2, conn)
    context([tag2, tag2id, tag2name])

    if tag1id is None or tag2id is None:
        context('DB not initialized? tag1 or tag2 is null.', tag1, tag2, tag1id, tag2id)
        sys.exit()

    #Order the two tags alphabetically
    if tag1id < tag2id:
       first = tag1id
       second = tag2id
    else:
       first = tag2id
       second = tag1id

    statement = "select * from combos where tag1id='{0}' and tag2id='{0}'".format(first, second)
    combos = sqliteStatement(conn, statement, ())
    
    comboList = []
    for combo in combos:
        comboList.append(combo[0])

    data = {'tag1': tag1name, 'tag2': tag2name, 'combos': comboList}
    context(data)
    return data

def submitTag(tag):
    conn = sqliteConnect()

    tag = tag.lower()
    #if this tag already exists, reject it
    tag_id,tag_name = verifyTag(tag, conn)
    context(['checking on:', tag,tag_id,tag_name])
    if tag_id is not None and tag_name is not None:
        context('returning False')
        return False

    #This tag doesn't exist, so let's add it
    added_by = 0
    tag = addTag(conn, tag, namespace, added_by)
    context(['successfully added', tag])
    return True

def getMaxId(conn):
    try:
        statement = "select MAX(id) from tags"
        maxId = sqliteStatement(conn, statement, ())
        maxId = maxId[0][0]
    except Exception as e:
        context('Tags table appears to be empty.')
        sys.exit()

    if maxId < 0:
        context("There are no tags present in the database. You might want to seed the database? /seed")
        sys.exit()
    return maxId

def getRandomTag(conn):
    maxId = getMaxId(conn)
    #Tags are None when they want a random value.
    if maxId > 1:
        randId = random.randrange(1,maxId)
    else:
        randId = 1
    statement = "select id,name from tags where id='{0}' and disabled=0".format(randId)
    tag = sqliteStatement(conn, statement, ())
    if not tag:
        return None,None
    return tag[0][0], tag[0][1]

def verifyTag(tag_name, conn):
    context(tag_name)
    statement = "select id,name from tags where name='{0}' and disabled=0".format(tag_name)
    tag = sqliteStatement(conn, statement, ())
    if not tag:
        return None,None
    context(tag_name, '&', tag)
    return tag[0][0], tag[0][1]

def seedDatabase():
    conn = sqliteConnect()
    defaultTags = ['alpha', 'beta', 'delta', 'omega', 'first', 'zero', 'final']
    namespace = 'foon'
    added_by = 0
    for name in defaultTags:
        addTag(conn, name, namespace, added_by)

'''
CREATE TABLE IF NOT EXISTS combos (
    id integer PRIMARY KEY,
    tag1id BIG INT not null,
    tag2id BIG INT not null,
    namespace text not null,
    username text not null,
    description text not null,
    added_ts BIG INT,
    changed_ts big int,
    disabled SMALL INT DEFAULT 0
);


'''
def combine(tag1, tag2, description):
    conn = sqliteConnect()
    
    if tag1 is None:
        tag1 = getRandomTag(conn)
    tag1id,tag1name = verifyTag(tag1, conn)
    tag2id,tag2name = verifyTag(tag2, conn)

    namespace = 'foon'
    added_by = '0'

    statement = "INSERT OR IGNORE INTO combos (tag1id, tag2id, namespace, username, description, added_ts, disabled) VALUES ('{0}', '{1}', {2}, '{3}', {4}, {5}, {6})".format(tag1id, tag2id, namespace, added_by, description, datetime.datetime.now().strftime("%s"), 0)
    sqliteStatement(conn, statement, ())

def addTag(conn, name, namespace, added_by):
    name = name.lower()
    #name is a unique key, nothing else. `id` is primary key, autoincremented.
    statement = "INSERT OR IGNORE INTO tags (name, namespace, added_by, added_ts, disabled) VALUES ('{0}', '{1}', {2}, '{3}', {4})".format(name, namespace, added_by, datetime.datetime.now().strftime("%s"), 0)
    tag = sqliteStatement(conn, statement, ())
    context(['tag', tag, 'for statement', statement])
    return tag

############################# FLASK ROUTING #############################

def verify_post_auth():
    #@TODO: nonce, user, namespace, auth, etc.
    return True

def renderCombosOrNone(data):
    context('data:', data)
    return render_template('show.html', data=data)

@app.route('/favicon.ico')
def favicon():
    return ''

@app.route('/<string:tag1>/<string:tag2>/<string:etc>')
def two_tags_etc(tag1, tag2, etc):
    context('@route')
    return two_tags(tag1, tag2)

@app.route('/<string:tag1>/<string:tag2>')
def two_tags(tag1, tag2):
    data = showCombo(tag1, tag2)
    data['this_these'] = 'these'
    context('@route', data)
    return renderCombosOrNone(data)

@app.route('/<string:tag1>')
def one_tag(tag1):
    context('@route')
    data = showCombo(tag1, None)
    data['this_these'] = 'this'
    return renderCombosOrNone(data)

@app.route('/seed')
def seed_db():
    context('@route')
    seedDatabase()
    return 'seeded!'

@app.route('/addtag/<string:tag>', methods=['POST'])
def post_submit_tag():
    context('@route')
    if not verify_post_auth():
        return 'Invalid request!'
    if not request.form['tag']:
        return 'Invalid tag!'

    if submitTag(tag):
        return one_tag(tag)

    return 'Tag already exists!'

@app.route('/combine/<string:tag1>/<string:tag2>', methods=['POST'])
def post_submit_combine():
    context()
    if not verify_post_auth():
        return 'Invalid request!' 
    if not request.form['combination']:
        return 'Invalid combination!'

    combine(tag1, tag2, request.form['combination'])

    #that's presumably persisted correctly and shouldn't have any race conditions, right?! now display it back to them.
    return two_tags(tag1, tag2)

@app.route('/')
def no_tags():
    context()
    data = showCombo(None, None)
    data['this_these'] = 'those'
    return renderCombosOrNone(data)
