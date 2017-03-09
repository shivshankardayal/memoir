# Copyright (c) 2013 Shiv Shankar Dayal
# This file is part of Kunjika.
#
# Kunjika is free software: you can redistribute it and/or modify it
# under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License,
# or (at your option) any later version.
#
# Kunjika is distributed in the hope that it will be useful, but
# WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU
# General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program. If not, see http://www.gnu.org/licenses/.

# We index all the questions, tags and users to elasticsearch using this
# script.

import pyes
#from couchbase.views.iterator import View, Query
from couchbase import Couchbase
from couchbase.exceptions import *
import urllib2
import json

mb = Couchbase.connect("memoir")
es_conn = pyes.ES('http://localhost:9200/')
DB_URL = 'http://localhost:8092/'

questions_mapping = {
    'title': {
#        'boost': 1.0,
        'index': 'analyzed',
        'store': 'yes',
        'type': 'text',
    },
    'description': {
#        'boost': 1.0,
        'index': 'analyzed',
        'store': 'yes',
        'type': 'text',
#        "term_vector": "with_positions_offsets"
    },
    'qid': {
#        'boost': 1.0,
        'index': 'not_analyzed',
        'store': 'yes',
        'type': 'integer'
#        "term_vector": "with_positions_offsets"
    }
}

users_mapping = {
    'name': {
#        'boost': 1.0,
        'index': 'analyzed',
        'store': 'yes',
        'type': 'text',
        "term_vector": "with_positions_offsets"
    },
    'uid': {
#        'boost': 1.0,
        'index': 'not_analyzed',
        'store': 'yes',
        'type': 'integer'
#        "term_vector": "with_positions_offsets"
    }
}

tags_mapping = {
    'tag': {
#        'boost': 1.0,
        'index': 'analyzed',
        'store': 'yes',
        'type': 'text',
        "term_vector": "with_positions_offsets"
    },
    'tid': {
#        'boost': 1.0,
        'index': 'not_analyzed',
        'store': 'yes',
        'type': 'integer'
#        "term_vector": "with_positions_offsets"
    }
}

articles_mapping = {
    'title': {
#        'boost': 1.0,
        'index': 'analyzed',
        'store': 'yes',
        'type': 'text',
#        "term_vector": "with_positions_offsets"
    },
    'content': {
#        'boost': 1.0,
        'index': 'analyzed',
        'store': 'yes',
        'type': 'text',
#        "term_vector": "with_positions_offsets"
    },
    'qid': {
#        'boost': 1.0,
        'index': 'not_analyzed',
        'store': 'yes',
        'type': 'text',
#        "term_vector": "with_positions_offsets"
    }
}
# Initialize indices for different buckets
try:
    es_conn.indices.delete_index("questions")
    es_conn.indices.create_index("questions")
except:
    pass

try:
    es_conn.indices.delete_index("users")
    es_conn.indices.create_index("users")
except:
    pass

try:
    es_conn.indices.delete_index("tags")
    es_conn.indices.create_index("tags")
except:
    pass


es_conn.indices.put_mapping("questions-type", {'properties':questions_mapping}, ["questions"])
es_conn.indices.put_mapping("users-type", {'properties':users_mapping}, ["users"])
es_conn.indices.put_mapping("tags-type", {'properties':tags_mapping}, ["tags"])

questions = urllib2.urlopen(DB_URL + "memoir/_design/dev_questions/_view/get_questions?descending=true&stale=false").read()
questions = json.loads(questions)
##print questions
question_list = []
for i in questions['rows']:
    question_list.append(unicode(i['id']))

val_res = mb.get_multi(question_list)
questions = []
for qid in question_list:
	questions.append(val_res[unicode(qid)].value)
for question in questions:
    #print question
    #print type(es_conn)
    print question['qid']
    es_conn.index({'title': question['title'], 'description': question['content']['description'], 'qid': int(question['qid'][1:]),
                               'position': int(question['qid'][1:])}, 'questions', 'questions-type', int(question['qid'][1:]))

#es_conn.indices.refresh('questions')

rows = urllib2.urlopen(DB_URL + 'memoir/_design/dev_tags/_view/get_tag_by_id').read()
rows = json.loads(rows)['rows']
tids_list = []
for row in rows:
    tids_list.append(unicode(row['id']))

if len(tids_list) != 0:
    val_res = mb.get_multi(tids_list)

tags = []

for tid in tids_list:
    tags.append(val_res[unicode(tid)].value)

for tag in tags:
    es_conn.index({'tag':tag['tag'], 'tid':tag['tid'], 'position':tag['tid']}, 'tags', 'tags-type', tag['tid'])

#es_conn.indices.refresh('tags')

rows = urllib2.urlopen(DB_URL + 'memoir/_design/dev_users/_view/get_by_reputation').read()
rows = json.loads(rows)['rows']
uids_list = []
for row in rows:
    uids_list.append(unicode(row['id']))

if len(uids_list) != 0:
    val_res = mb.get_multi(uids_list)

users = []

for uid in uids_list:
    users.append(val_res[unicode(uid)].value)

for user in users:
    es_conn.index({'name':user['name'], 'uid':int(user['id'][1:]), 'position':int(user['id'][1:])}, 'users', 'users-type', int(user['id'][1:]))
#es_conn.indices.refresh('users')
