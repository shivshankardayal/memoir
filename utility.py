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
import memoir
from flask import jsonify, g, render_template, flash, redirect, abort
from math import ceil
import urllib2
import json
from time import strftime, localtime, time
from flask import url_for, request
import pyes
import question
from flask.ext.mail import Message
from couchbase.views.iterator import View
from couchbase.views.params import Query
# from threading import Thread
from uuid import uuid1
from forms import *
import urllib
import markdown
import bleach
import re

def common_data():
    tag_list = []
    done = None
    while done is None:
        try:
            #qcount = memoir.mb.get('qcount').value
            #ucount = memoir.mb.get('count').value
            #tcount = memoir.mb.get('tcount').value
            val_res = memoir.mb.get_multi(['qcount', 'count', 'tcount'])
            qcount = val_res[u'qcount'].value
            ucount = val_res[u'count'].value
            tcount = val_res[u'tcount'].value
            #print(val_res)
            acount = urllib2.urlopen(memoir.DB_URL + 'memoir/_design/dev_questions/_view/get_acount?reduce=true').read()
            acount = json.loads(acount)
            if len(acount['rows']) is not 0:
                acount = acount['rows'][0]['value']
            else:
                acount = 0

            if tcount > 0:
                tag_list = get_popular_tags()
            done = True
        except:
            pass

    return (qcount, acount, tcount, ucount, tag_list)


def common_rendering(results, query, page):
    (qcount, acount, tcount, ucount, tag_list) = common_data()
    results_set = set(results)
    questions_list = []

    for qid in results_set:
        questions_list.append(memoir.mb.get(u'q' + unicode(qid)).value)

    for i in questions_list:
        i['tstamp'] = strftime("%a, %d %b %Y %H:%M", localtime(i['content']['ts']))

        user = memoir.mb.get(i['content']['op']).value
        i['opname'] = user['name']

    pagination = Pagination(page, memoir.QUESTIONS_PER_PAGE, len(questions_list))

    if g.user is None:
        return render_template('search.html', title='Search results for ' + query, qpage=True,
                               questions=questions_list[(page-1)*memoir.QUESTIONS_PER_PAGE:(page-1)*memoir.QUESTIONS_PER_PAGE + memoir.QUESTIONS_PER_PAGE],
                               pagination=pagination, qcount=qcount, ucount=ucount, tcount=tcount, acount=acount, tag_list=tag_list, query=query, APP_ROOT=memoir.APP_ROOT)
    elif g.user is not None and g.user.is_authenticated:
        if (len(questions_list) - (page-1)*memoir.QUESTIONS_PER_PAGE) < memoir.QUESTIONS_PER_PAGE:
            return render_template('search.html', title='Search results for ' + query, qpage=True,
                                   questions=questions_list[(page-1)*memoir.QUESTIONS_PER_PAGE:],
                                   pagination=pagination, qcount=qcount, ucount=ucount, tcount=tcount, acount=acount, tag_list=tag_list, query=query, APP_ROOT=memoir.APP_ROOT)
        else:
            return render_template('search.html', title='Search results for ' + query, qpage=True,
                                   questions=questions_list[(page-1)*memoir.QUESTIONS_PER_PAGE:(page-1)*memoir.QUESTIONS_PER_PAGE +
                                                            memoir.QUESTIONS_PER_PAGE],
                                   pagination=pagination, qcount=qcount, ucount=ucount, tcount=tcount, acount=acount, tag_list=tag_list, query=query, APP_ROOT=memoir.APP_ROOT)
    if ((page-1)*memoir.QUESTIONS_PER_PAGE + memoir.QUESTIONS_PER_PAGE - page-1*memoir.QUESTIONS_PER_PAGE) < memoir.QUESTIONS_PER_PAGE:
        return render_template('search.html', title='Search results for ' + query, qpage=True, questions=questions_list[(page-1)*memoir.QUESTIONS_PER_PAGE:],
                               pagination=pagination, qcount=qcount, ucount=ucount, tcount=tcount, acount=acount, tag_list=tag_list, query=query, APP_ROOT=memoir.APP_ROOT)
    else:
        return render_template('search.html', title='Search results for ' + query, qpage=True,
                               questions=questions_list[(page-1)*memoir.QUESTIONS_PER_PAGE:(page-1)*memoir.QUESTIONS_PER_PAGE +
                                                        memoir.QUESTIONS_PER_PAGE],
                               pagination=pagination, qcount=qcount, ucount=ucount, tcount=tcount, acount=acount, tag_list=tag_list, query=query, APP_ROOT=memoir.APP_ROOT)


def search(query, page):
    title_q = pyes.MatchQuery('title', query)
    question_q = pyes.MatchQuery('description', query)
    title_results = memoir.es_conn.search(query=title_q)
    question_results = memoir.es_conn.search(query=question_q)

    results = []

    for r in title_results:
        if 'qid' in r:
            results.append(r['qid'])
    for r in question_results:
        if 'qid' in r:
            results.append(r['qid'])

    return common_rendering(results, query, page)


def search_title(query, page):
    title = query[6:].strip()
    q = pyes.MatchQuery('title', title)
    title_results = memoir.es_conn.search(query=q)
    results = []

    for r in title_results:
        if 'qid' in r:
            results.append(r['qid'])

    return common_rendering(results, query, page)


def search_description(query, page):
    description = query[12:].strip()
    q = pyes.MatchQuery('description', description)
    question_results = memoir.es_conn.search(query=q)

    results = []

    for r in question_results:
        if 'qid' in r:
            results.append(r['qid'])

    return common_rendering(results, query, page)


def search_user(query, page):
    (qcount, acount, tcount, ucount, tag_list) = common_data()
    user = query[5:].strip()
    q = pyes.PrefixQuery('name', user)
    question_results = memoir.es_conn.search(query=q)

    results = []
    for r in question_results:
        print r
        results.append(r['uid'])

    questions_list = []

    for uid in results:
        question_view = urllib2.urlopen(
            memoir.DB_URL + 'memoir/_design/dev_questions/_view/get_questions_by_userid?key=' + '"u' + unicode(uid) + '"').read()
        rows = json.loads(question_view)['rows']
        qids_list = []
        for row in rows:
            qids_list.append(unicode(row['id']))
        if len(qids_list) != 0:
            val_res = memoir.mb.get_multi(qids_list)

        for id in qids_list:
            questions_list.append(val_res[unicode(id)].value)

    for i in questions_list:
        i['ts'] = strftime("%a, %d %b %Y %H:%M", localtime(i['content']['ts']))

        user = memoir.mb.get(i['content']['op']).value
        i['opname'] = user['name']

    pagination = Pagination(page, memoir.QUESTIONS_PER_PAGE, len(questions_list))

    if g.user is None:
        return render_template('search.html', title='Search results for ' + query, qpage=True, questions=questions_list[(page-1)*memoir.QUESTIONS_PER_PAGE:page*memoir.QUESTIONS_PER_PAGE],
                               pagination=pagination, qcount=qcount, ucount=ucount, tcount=tcount, acount=acount, tag_list=tag_list, query=query, APP_ROOT=memoir.APP_ROOT)
    elif g.user is not None and g.user.is_authenticated:
        return render_template('search.html', title='Search results for ' + query, qpage=True, questions=questions_list[(page-1)*memoir.QUESTIONS_PER_PAGE:page*memoir.QUESTIONS_PER_PAGE],
                               pagination=pagination, qcount=qcount, ucount=ucount, tcount=tcount, acount=acount, tag_list=tag_list, query=query,
                               name=g.user.name, role=g.user.role, user_id=g.user.id, APP_ROOT=memoir.APP_ROOT)
    else:
        return render_template('search.html', title='Search results for ' + query, qpage=True, questions=questions_list[(page-1)*memoir.QUESTIONS_PER_PAGE:page*memoir.QUESTIONS_PER_PAGE],
                               pagination=pagination, qcount=qcount, ucount=ucount, tcount=tcount, acount=acount, tag_list=tag_list, query=query, name=g.user.name,
                               user_id=g.user.id, APP_ROOT=memoir.APP_ROOT)


def search_tag(query, page):
    (qcount, acount, tcount, ucount, tag_list) = common_data()
    tag = query[4:].strip()
    q = pyes.MatchQuery('tag', tag)
    question_results = memoir.es_conn.search(query=q)

    results = []

    for r in question_results:
        results.append(r['tag'])

    questions_list = []
    for tag in results:
        #    kunjika.DB_URL + 'questions/_design/dev_questions/_view/get_questions_by_tag?key=' + '"' + tag + '"').read()
        q = Query(key=tag)
        for result in View(memoir.mb, "dev_questions", "get_questions_by_tag", include_docs=True, query=q):
            questions_list.append(result.doc.value)

    for i in questions_list:
        i['tstamp'] = strftime("%a, %d %b %Y %H:%M", localtime(i['content']['ts']))

        user = memoir.mb.get(i['content']['op']).value
        i['opname'] = user['name']

    pagination = Pagination(page, memoir.QUESTIONS_PER_PAGE, len(questions_list))

    if g.user is None:
        return render_template('search.html', title='Search results for ' + query, qpage=True, questions=questions_list[(page-1)*memoir.QUESTIONS_PER_PAGE:],
                               pagination=pagination, qcount=qcount, ucount=ucount, tcount=tcount, acount=acount, tag_list=tag_list, query=query, APP_ROOT=memoir.APP_ROOT)
    elif g.user is not None and g.user.is_authenticated:
        return render_template('search.html', title='Search results for ' + query, qpage=True, questions=questions_list[(page-1)*memoir.QUESTIONS_PER_PAGE:],
                               pagination=pagination, qcount=qcount, ucount=ucount, tcount=tcount, acount=acount, tag_list=tag_list, query=query, APP_ROOT=memoir.APP_ROOT)
    else:
        return render_template('search.html', title='Search results for ' + query, qpage=True, questions=questions_list[(page-1)*memoir.QUESTIONS_PER_PAGE:],
                               pagination=pagination, qcount=qcount, ucount=ucount, tcount=tcount, acount=acount, tag_list=tag_list, query=query, APP_ROOT=memoir.APP_ROOT)


def generate_url(title):
    length = len(title)
    prev_dash = False
    url = ""
    for i in range(length):
        c = title[i]
        if (c >= 'a' and c <= 'z') or (c >= '0' and c <= '9'):
            url += c
            prev_dash = False
        elif c >= 'A' and c <= 'Z':
            url += c
            prev_dash = False
        elif c == ' ' or c == ',' or c == '.' or c == '/' or c == '\\' or c == '-' or c == '_' or c == '=':
            if not prev_dash and len(url) > 0:
                url += '-'
                prev_dash = True
        elif ord(c) > 160:
            #c = c.decode('UTF-8').lower()
            url += c
            prev_dash = False
        if i == 80:
            break

    if prev_dash is True:
        url = url[:-1]

    return url


def accept_answer(idntfr):

    idntfr = idntfr[4:]

    idntfr_list = idntfr.split('-')
    qid = idntfr_list[0]
    aid = idntfr_list[1]

    question = memoir.mb.get(qid).value

    voter = memoir.mb.get(unicode(g.user.id)).value

    if int(question['content']['op']) != g.user.id:
        return jsonify({"success": False})
    for answer in question['answers']:
        if answer['aid'] != int(aid):
            if answer['best'] == True:
                receiver = memoir.mb.get(unicode(answer['poster'])).value
                receiver['rep'] -= 10
                voter['rep'] -= 2
                memoir.mb.replace(unicode(answer['poster']), receiver)
                memoir.mb.replace(unicode(voter['id']), voter)
                answer['best'] = False

        else:
            if answer['best'] != True:
                answer['best'] = True
                receiver = memoir.mb.get(unicode(answer['poster'])).value
                receiver['rep'] += 10
                voter['rep'] += 2
                memoir.mb.replace(unicode(answer['poster']), receiver)
                memoir.mb.replace(unicode(voter['id']), voter)
            else:
                receiver = memoir.mb.get(unicode(answer['poster'])).value
                receiver['rep'] -= 10
                voter['rep'] -= 2
                memoir.mb.replace(unicode(answer['poster']), receiver)
                memoir.mb.replace(unicode(voter['id']), voter)
                answer['best'] = False


    memoir.mb.replace(qid, question)

    return jsonify({"success": True})

def handle_favorite(idntfr):
    if g.user.id == -1:
        return jsonify({"success": False})

    qid = idntfr[3:]

    ##print qid
    question = memoir.mb.get(qid).value
    #user = kunjika.cb.get(unicode(g.user.id)).value

    ##print question
    ##print user
    if 'users_fav' in question:
        if g.user.id in question['users_fav']:
            question['users_fav'].remove(g.user.id)
        else:
            question['users_fav'].append(g.user.id)
    else:
        question['users_fav'] = []
        question['users_fav'].append(g.user.id)

    # Issue #9
    #if 'fav_q' in user:
    #    if qid in user['fav_q']:
    #       user['fav_q'].remove(qid)
    #    else:
    #        user['fav_q'].append(qid)
    #else:
    #    user['fav_q'] = []
    #    user['fav_q'].append(qid)

    #kunjika.cb.replace(unicode(g.user.id), user)
    memoir.mb.replace(qid, question)

    return jsonify({"success": True})


class Pagination(object):

    def __init__(self, page, per_page, total_count):
        self.page = page
        self.per_page = per_page
        self.total_count = total_count

    @property
    def pages(self):
        return int(ceil(self.total_count / float(self.per_page)))

    @property
    def has_prev(self):
        return self.page > 1

    @property
    def has_next(self):
        return self.page < self.pages

    def iter_pages(self, left_edge=2, left_current=2,
                   right_current=5, right_edge=2):
        last = 0
        for num in xrange(1, self.pages + 1):
            if num <= left_edge or \
                (num > self.page - left_current - 1 and \
                num < self.page + right_current) or \
                num > self.pages - right_edge:
                if last + 1 != num:
                    yield None
                yield num
                last = num

def get_questions_for_page(page, QUESTIONS_PER_PAGE, count):

    skip = (page - 1) * QUESTIONS_PER_PAGE
    questions = urllib2.urlopen(
                memoir.DB_URL + 'memoir/_design/dev_questions/_view/get_questions?limit=' +
                unicode(QUESTIONS_PER_PAGE) + '&skip=' + unicode(skip) + '&descending=true').read()

    rows = json.loads(questions)['rows']
    qids_list = []
    questions_list = []
    for row in rows:
        ##print row['id']
        qids_list.append(unicode(row['id']))
    if len(qids_list) != 0:
        val_res = memoir.mb.get_multi(qids_list)

    for id in qids_list:
        questions_list.append(val_res[unicode(id)].value)


    for i in questions_list:
        i['tstamp'] = strftime("%a, %d %b %Y %H:%M", localtime(i['content']['ts']))

        user = memoir.mb.get(i['content']['op']).value
        i['opname'] = user['name']
        if i['views'] > 1000000:
            i['views'] /= 1000000
            i['views'] = unicode(i['views']) + 'M'
        elif i['views'] > 1000:
           i['views'] /= 1000
           i['views'] = unicode(i['views']) + 'K'

    return questions_list


def get_tags_per_page(page, TAGS_PER_PAGE, count):

    skip = (page - 1) * TAGS_PER_PAGE
    tags = urllib2.urlopen(
                memoir.DB_URL + 'memoir/_design/dev_tags/_view/get_by_count?limit=' +
                unicode(TAGS_PER_PAGE) + '&skip=' + unicode(skip) + '&descending=true').read()
    rows = json.loads(tags)['rows']
    tids_list = []
    tags_list = []

    for row in rows:
        tids_list.append(unicode(row['id']))

    if len(tids_list) != 0:
        val_res = memoir.mb.get_multi(tids_list)
    for id in tids_list:
        tags_list.append(val_res[unicode(id)].value)

    return tags_list


def get_groups_per_page(page, GROUPS_PER_PAGE, document):

    skip = (page - 1) * GROUPS_PER_PAGE
    group_list = []
    ##print document
    for row in document:
        ##print row['id']
        group_list.append(memoir.mb.get(row['id'].split(':')[1]).value)

    #print group_list
    groups = sorted(group_list, key=lambda k: k['member_count'], reverse=True)
    return groups


def get_users_per_page(page, USERS_PER_PAGE, count):

    skip = (page - 1) * USERS_PER_PAGE
    ids = urllib2.urlopen(
                memoir.DB_URL + 'memoir/_design/dev_users/_view/get_by_reputation?limit=' +
                unicode(USERS_PER_PAGE) + '&skip=' + unicode(skip) + '&descending=true').read()
    rows = json.loads(ids)['rows']

    users_list = []

    for row in rows:
        user = memoir.mb.get(unicode(row['id'])).value
        users_list.append(user)

    return users_list

def get_questions_for_tag(page, QUESTIONS_PER_PAGE, tag):

    skip = (page - 1) * QUESTIONS_PER_PAGE
    tag = urllib2.quote(tag.encode('utf8'), '')
    print tag
    rows = urllib2.urlopen(memoir.DB_URL + 'memoir/_design/dev_questions/_view/get_qid_from_tag?limit=' +
                unicode(QUESTIONS_PER_PAGE) + '&skip=' + unicode(skip) + '&key="' + unicode(tag) + '"&reduce=false').read()
    count = urllib2.urlopen(memoir.DB_URL + 'memoir/_design/dev_questions/_view/get_qid_from_tag?key="' + unicode(tag) + '"&reduce=true').read()
    count = json.loads(count)['rows']
    print rows
    if len(count) == 0:
        count = 0
    else:
        count = count[0]['value']
    #tag = kunjika.tb.get(tag).value
    rows = json.loads(rows)['rows']
    question_list = []
    qids_list = []
    for row in rows:
        ##print row
        m = re.search(r"""_v\d+$""", row['id'])
        if m is None:
            qids_list.append(unicode(row['id']))

    if len(qids_list) != 0:
        val_res = memoir.mb.get_multi(qids_list)

    for qid in qids_list:
        question_list.append(val_res[qid].value)

    for i in question_list:
        i['tstamp'] = strftime("%a, %d %b %Y %H:%M", localtime(i['content']['ts']))

        user = memoir.mb.get(i['content']['op']).value
        i['opname'] = user['name']

    return [question_list, count]

def url_for_other_page(page):
    args = request.view_args.copy()
    args['page'] = page
    return url_for(request.endpoint, **args)

def url_for_other_user_question_page(page):
    args = request.view_args.copy()
    args['qpage'] = page
    return url_for(request.endpoint, **args)

def url_for_other_user_answer_page(page):
    args = request.view_args.copy()
    args['apage'] = page
    return url_for(request.endpoint, **args)

def url_for_search_page(page, query):
    args = request.view_args.copy()
    args['page'] = page
    return url_for(request.endpoint, query=query, **args)

def url_for_browse_page(page):
    args = request.view_args.copy()
    args['page'] = page
    return url_for(request.endpoint, **args)

def get_popular_tags():

    tag_list = urllib2.urlopen(memoir.DB_URL + 'memoir/_design/dev_tags/_view/get_by_count?descending=true').read()
    rows = json.loads(tag_list)['rows']
    tids_list = []
    tags_list = []

    for row in rows:
        tids_list.append(unicode(row['id']))

    if len(tids_list) != 0:
        val_res = memoir.mb.get_multi(tids_list)
    for id in tids_list:
        tags_list.append(val_res[unicode(id)].value)

    return tags_list[:25]

def filter_by(email):

    user = urllib2.urlopen(
                memoir.DB_URL + 'memoir/_design/dev_users/_view/get_id_from_email?key=' + '"' + urllib2.quote(email).encode('utf8') + '"').read()
    try:
      id = json.loads(user)['rows'][0]['id']
    except:
      return None
    try:
        user = memoir.mb.get(unicode(id)).value
        return user
    except:
        return None


def get_user_questions_per_page(user, qpage, USER_QUESTIONS_PER_PAGE, qcount):
    # Issue 9

    #if 'questions' in user:
    #    qid_list = user['questions'][(qpage - 1)*USER_QUESTIONS_PER_PAGE:qpage*USER_QUESTIONS_PER_PAGE]
    #else:
    #    return None

    skip = (qpage - 1) * USER_QUESTIONS_PER_PAGE
    question_list = []
    question_view = urllib2.urlopen(
        memoir.DB_URL + 'memoir/_design/dev_questions/_view/get_questions_by_userid?key=' + '"' +unicode(user['id'])
        + '"' + '&desending=true&skip=' + unicode(skip) + '&limit=' + unicode(USER_QUESTIONS_PER_PAGE)
    ).read()
    rows = json.loads(question_view)['rows']
    ##print rows
    qids_list = []
    questions = []

    for row in rows:
        ##print row['id']
        qids_list.append(unicode(row['id']))
    if len(qids_list) != 0:
        val_res = memoir.mb.get_multi(qids_list)

    for id in qids_list:
        questions.append(val_res[unicode(id)].value)
    ##print questions
    for q in questions:
        #print q
        question = {}
        question['qid'] = q['qid']
        question['votes'] = q['votes']
        question['acount'] = q['acount']
        question['title'] = q['title']
        question['url'] = q['content']['url']
        question['views'] = q['views']
        question['ts'] = q['updated']
        question['op'] = q['content']['op']
        question['tags'] = q['content']['tags']
        question_list.append(question)

    #for qid in qid_list:
    #    question = kunjika.qb.get(unicode(qid)).value
    #    question_list.append(question)

    ##print question_list
    return question_list

def get_user_answers_per_page(user, apage, USER_ANSWERS_PER_PAGE, acount):
    #the following is aid in the form of 'qid-aid'
    # Issue 9
    #if 'answers' in user:
    #    aid_list = user['answers'][(apage - 1)*USER_ANSWERS_PER_PAGE:apage*USER_ANSWERS_PER_PAGE]
    #else:
    #    return None

    skip = (apage - 1)*USER_ANSWERS_PER_PAGE
    question_list = []
    aids = []
    question_view = urllib2.urlopen(
        memoir.DB_URL + 'memoir/_design/dev_questions/_view/get_ans_by_userid?key="' +user['id']
        + '"&desending=true&skip=' + unicode(skip) + '&limit=' + unicode(USER_ANSWERS_PER_PAGE)
    ).read()
    question_view = json.loads(question_view)['rows']
    print question_view
    for row in question_view:
        #print row['value']
        question = {}
        question['qid'] = row['value'][0]
        question['votes'] = row['value'][1]
        question['acount'] = row['value'][2]
        aids.append(row['value'][3])
        question['title'] = row['value'][4]
        question['url'] = row['value'][5]
        question['views'] = row['value'][6]
        question_list.append(question)
    #let us get question ids and questions
    #for aid in aid_list:
    #    qid = aid.split('-')[0]
    #    single_aid = aid.split('-')[1]
    #    ##print qid
    #    ##print single_aid
    #    question = kunjika.qb.get(qid).value
    #    question_list.append(question)
    #    aids.append(single_aid)

    return question_list, aids

def get_similar_questions(title, qid):
    #print title
    title_q=pyes.MatchQuery('title', title)
    title_results=memoir.es_conn.search(query=title_q)

    results=[]
    for r in title_results:
        # print r
        if 'qid' in r:
            if r['qid'] != qid:
                question_dict = {}
                question_dict = question.get_question_by_id('q' + unicode(r['qid']), question_dict)
                #print question_dict
                results.append([r['qid'], r['title'], question_dict['content']['url']])

    return results[:10]

def get_autocomplete(request):
    ##print request.args.get('val')
    q=pyes.PrefixQuery('title', request.args.get('val'))
    title_results=memoir.es_conn.search(query=q)
    results=[]

    for r in title_results:
        if 'qid' in r:
            results.append(r['qid'])

    questions_list = []

    if len(results) > 10:
        for i in range(0, len(results)):
            print i
            question = memoir.mb.get('q' + unicode(results[i])).value
            questions_list.append({'title':question['title'], 'qid': question['qid'], 'url':question['content']['url']})
            ##print question['title'] + ' ' + question['content']['url'] + unicode(question['qid'])
    else:
        for i in range(0, len(results)):
            question = memoir.mb.get('q' + unicode(results[i])).value
            questions_list.append({'title':question['title'], 'qid': question['qid'], 'url':question['content']['url']})
            ##print question['title'] + ' ' + question['content']['url'] + unicode(question['qid'])
    print results
    if len(results) > 10:
        return jsonify({'data': questions_list[0:10]})
    else:
        return jsonify({'data':questions_list[0:len(results)]})


def send_invites(request):
    user = memoir.mb.get(unicode(g.user.id)).value
    ##print user
    try:
        email_list = request.form['email_list']
        email_list = email_list.split(';')
        msg = Message("Invitation to Kunjika from " + user['name'])
        msg.recipients = email_list
        msg.sender = user['email']
        msg.html = "<p>Hi,<br/><br/> You have been invited to join Kunjika by " + user['name'] +\
            ". We would like you to join our family of friends. Please register yourself at " +\
            memoir.HOST_URL +\
            " <br/><br/>Best regards,<br/>Kunjika Team<p>"
        memoir.mail.send(msg)
        return True
    except:
        return False

def create_group(request):
    try:
        group_name = request.form['group-name']
        group = {}
        member = {}

        group['group_name'] = group_name
        group['id'] = unicode(uuid1())
        group['owner'] = g.user.id
        group['member_count'] = 1
        group['type'] = 'private-group'

        member['member-id'] = g.user.id
        member['type'] = 'group-member'

        memoir.mb.add(group['id'], group)

        memoir.mb.add(unicode(member['member-id']) + ':' + unicode(group['id']), member)

        return True
    except:
        return False


def endorse():
    tuid = request.referrer.split('/')[5]
    to_user = memoir.mb.get(unicode(tuid)).value
    print request.args['id']
    
    skill = request.args['id'][1:]

    print 'memoir/_design/dev_kunjika/_view/get_end_by_uid?key=[' + unicode(to_user['id'])
    print ',"' + urllib.quote(skill).encode('utf8') + '"]&stale=false&reduce=false'
    sid_doc = urllib2.urlopen(memoir.DB_URL + 'memoir/_design/dev_kunjika/_view/get_end_by_uid?key=["' + unicode(to_user['id']) +
                              '","' + urllib.quote(skill).encode('utf8') + '"]&stale=false&reduce=false').read()
    sid_doc = json.loads(sid_doc)

    endorsed = False
    if len(sid_doc['rows']) != 0:
        for row in sid_doc['rows']:
            endorsement = memoir.mb.get(row['id']).value
            if endorsement['fuid'] == g.user.id:
                endorsed = True
                memoir.mb.delete(row['id'])
                break
    if endorsed is False:
        doc = {}
        doc['id'] = 'e' + unicode(uuid1())
        doc['fuid'] = g.user.id
        doc['tuid'] = tuid
        doc['femail'] = g.user.user_doc['email']
        doc['_type'] = 'e'
        doc['skill'] = skill
        memoir.mb.add(doc['id'], doc)

    return jsonify({'success': True})


def write_article():
    articleForm = ArticleForm(request.form)
    if g.user is not None and g.user.is_authenticated:
        if articleForm.validate_on_submit() and request.method == 'POST':
            article = {}
            article['content'] = {}
            title = articleForm.title.data
            article['content'] = articleForm.content.data
            article['html'] = bleach.clean(markdown.markdown(article['content'], extensions=['extra', 'codehilite'],
                                                             output_format='html5'), memoir.tags_wl, memoir.attrs_wl)
            article['tags'] = []
            article['tags'] = articleForm.tags.data.split(',')
            article['tags'] = [tag.strip(' \t').lower() for tag in article['tags']]
            new_tag_list = []
            for tag in article['tags']:
                tag = list(tag)
                for i in range(0, len(tag)):
                    if tag[i] == ' ':
                        tag[i] = '-'
                new_tag_list.append(''.join(tag))
            article['tags'] = new_tag_list
            article['title'] = title
            article['_type'] = 'a'

            url = generate_url(title)

            article['url'] = url
            article['op'] = unicode(g.user.id)
            article['ts'] = int(time())
            article['updated'] = article['ts']
            article['ip'] = request.remote_addr
            aid = memoir.mb.incr('acount').value
            article['aid'] = 'a-' + unicode(aid)
            article['opname'] = g.user.name
            article['cids'] = []
            user = memoir.mb.get(unicode(g.user.id)).value
            user['rep'] += 25
            memoir.mb.replace(unicode(g.user.id), user)

            memoir.es_conn.index({'title': title, 'content': article['content'], 'aid': article['aid'],
                                   'position': article['content']}, 'articles', 'articles-type', article['aid'])
            #memoir.es_conn.indices.refresh('articles')
            memoir.mb.add(unicode(article['aid']), article)

            return redirect(url_for('browse_articles', aid=article['aid'], url=article['url']))

        return render_template('write_article.html', title='Write Artcile', form=articleForm, artpage=True, name=g.user.name, role=g.user.role,
                               user_id=g.user.id, APP_ROOT=memoir.APP_ROOT)
    return redirect(url_for('login'))


def browse_articles(page, aid, tag):
    if tag is not None:
        [articles_list, count] = get_articles_for_tag(page, memoir.ARTICLES_PER_PAGE, tag)
        if not articles_list and page != 1:
            abort(404)
        pagination = Pagination(page, memoir.ARTICLES_PER_PAGE, count)
        if g.user is None:
            return render_template('browse_articles.html', title='Articles for tag ' + tag, qpage=True, articles=articles_list,
                                   pagination=pagination, APP_ROOT=memoir.APP_ROOT)
        elif g.user is not None and g.user.is_authenticated:
            return render_template('browse_articles.html', title='Articles for tag ' + tag, qpage=True, articles=articles_list,
                                   name=g.user.name, role=g.user.role, user_id=g.user.id, pagination=pagination, APP_ROOT=memoir.APP_ROOT)
        else:
            return render_template('browse_articles.html', title='Articles for tag ' + tag, qpage=True, articles=articles_list,
                                   pagination=pagination, APP_ROOT=memoir.APP_ROOT)

    if aid is None:
        count_doc = urllib2.urlopen(memoir.DB_URL + 'memoir/_design/dev_kunjika/_view/get_articles').read()
        count_doc = json.loads(count_doc)
        count = 0
        if len(count_doc['rows']) != 0:
            count = count_doc['rows'][0]['value']
        articles_list = get_articles_for_page(page, memoir.ARTICLES_PER_PAGE, count)
        if not articles_list and page != 1:
            abort(404)
        pagination = Pagination(page, memoir.ARTICLES_PER_PAGE, count)
        if g.user is None:
            return render_template('browse_articles.html', title='Articles', artpage=True, articles=articles_list,
                                   pagination=pagination, APP_ROOT=memoir.APP_ROOT)
        elif g.user is not None and g.user.is_authenticated:
            return render_template('browse_articles.html', title='Articles', artpage=True, articles=articles_list,
                                   name=g.user.name, role=g.user.role, user_id=g.user.id, pagination=pagination, APP_ROOT=memoir.APP_ROOT)
        else:
            return render_template('browse_articles.html', title='Articles', artpage=True, articles=articles_list,
                                   pagination=pagination, APP_ROOT=memoir.APP_ROOT)
    else:
        article = memoir.mb.get(aid).value
        article['tstamp'] = strftime("%a, %d %b %Y %H:%M", localtime(article['ts']))
        user = memoir.mb.get(article['op']).value
        article['email'] = user['email']
        article['opname'] = user['name']

        form = CommentForm(request.form)
        article['comments'] = []

        if(len(article['cids'])) != 0:
            val_res = memoir.mb.get_multi(article['cids'])
        for cid in article['cids']:
            article['comments'].append(val_res[unicode(cid)].value)
        article['comments'] = sorted(article['comments'], key=lambda k: k['ts'], reverse=True)
        for comment in article['comments']:
            comment['tstamp'] = strftime("%a, %d %b %Y %H:%M", localtime(comment['ts']))
        if g.user is None:
            return render_template('single_article.html', title='Articles', artpage=True, article=article, APP_ROOT=memoir.APP_ROOT)

        elif g.user is not None and g.user.is_authenticated:
            return render_template('single_article.html', title='Articles', artpage=True, article=article, form=form,
                                   name=g.user.name, role=g.user.role, user_id=g.user.id, APP_ROOT=memoir.APP_ROOT)
        else:
            return render_template('single_article.html', title='Articles', artpage=True, article=article, APP_ROOT=memoir.APP_ROOT)


def get_articles_for_page(page, ARTICLES_PER_PAGE, count):
    skip = (page - 1) * ARTICLES_PER_PAGE
    articles = urllib2.urlopen(
        memoir.DB_URL + 'memoir/_design/dev_kunjika/_view/get_articles?limit=' +
        unicode(ARTICLES_PER_PAGE) + '&skip=' + unicode(skip) + '&descending=true&reduce=false&stale=false').read()

    rows = json.loads(articles)['rows']
    aids_list = []
    articles_list = []
    for row in rows:
        aids_list.append(unicode(row['id']))
    if len(aids_list) != 0:
        val_res = memoir.mb.get_multi(aids_list)

    for id in aids_list:
        articles_list.append(val_res[unicode(id)].value)

    for i in articles_list:
        i['tstamp'] = strftime("%a, %d %b %Y %H:%M", localtime(i['ts']))

        user = memoir.mb.get(i['op']).value
        i['opname'] = user['name']

    return articles_list


def get_articles_for_tag(page, ARTICLES_PER_PAGE, tag):

    skip = (page - 1) * ARTICLES_PER_PAGE
    tag = urllib2.quote(tag.encode('utf8'), '')
    rows = urllib2.urlopen(memoir.DB_URL + 'memoir/_design/dev_kunjika/_view/get_aid_from_tag?limit=' +
                           unicode(ARTICLES_PER_PAGE) + '&skip=' + unicode(skip) + '&key="' + tag + '"&reduce=false&stale=false').read()
    count_doc = urllib2.urlopen(memoir.DB_URL + 'memoir/_design/dev_kunjika/_view/get_aid_from_tag?key="' + tag + '"&reduce=true').read()
    count_doc = json.loads(count_doc)
    count = 0
    if len(count_doc['rows']) != 0:
        count = count_doc['rows'][0]['value']

    rows = json.loads(rows)['rows']
    aids_list = []
    for row in rows:
        aids_list.append(unicode(row['id']))

    if len(aids_list) != 0:
        val_res = memoir.mb.get_multi(aids_list)

    articles_list = []
    for aid in aids_list:
        articles_list.append(val_res[aid].value)

    for i in articles_list:
        i['tstamp'] = strftime("%a, %d %b %Y %H:%M", localtime(i['ts']))

        user = memoir.mb.get(i['op']).value
        i['opname'] = user['name']

    return [articles_list, count]


def article_comment():
    if len(request.form['comment']) < 10 or len(request.form['comment']) > 5000:
        return "Comment must be between 10 and 5000 characters."
    else:
        elements = request.form['element']
        aid = elements
    comment = {}
    comment['comment'] = request.form['comment']
    comment['html'] = bleach.clean(markdown.markdown(comment['comment'], extensions=['extra', 'codehilite'],
                                   output_format='html5'), memoir.tags_wl, memoir.attrs_wl)
    comment['poster'] = g.user.id
    comment['opname'] = g.user.name
    comment['ts'] = int(time())
    comment['ip'] = request.remote_addr
    comment['aid'] = aid
    comment['_type'] = 'ac'
    cid = 'ac-' + unicode(uuid1())
    comment['cid'] = cid
    article = memoir.mb.get(aid).value
    article['cids'].append(cid)
    memoir.mb.replace(aid, article)
    memoir.mb.add(cid, comment)

    email_list = []
    email_list.append(unicode(article['op']))
    if(len(article['cids'])) != 0:
        val_res = memoir.mb.get_multi(article['cids'])
    for cid in article['cids']:
        email_list.append(unicode(val_res[unicode(cid)].value['poster']))

    email_list = set(email_list)

    current_user_list = [unicode(g.user.id)]
    email_list = email_list - set(current_user_list)
    email_list = list(email_list)

    if len(email_list) != 0:
        email_users = memoir.mb.get_multi(email_list)
        email_list = []

        for id in email_users:
            email_list.append(email_users[unicode(id)].value['email'])

        msg = Message("A new comment has been posted to the article you have written or to the article where you" +
                      "have commented.")
        msg.recipients = email_list
        msg.sender = memoir.admin
        msg.html = "<p>Hi,<br/><br/> A new comment has been posted which you can read at " +\
        memoir.HOST_URL + "articles/" + unicode(article['aid']) + '/' + article['url'] + \
        " <br/><br/>Best regards,<br/>Kunjika Team<p>"
        memoir.mail.send(msg)

    ts = strftime("%a, %d %b %Y %H:%M", localtime(comment['ts']))
    return json.dumps({"id": cid, "comment": comment['html'], "user_id": g.user.id,
                       "uname": g.user.name, "ts": ts, "aid": aid})


def edit_article(element):
    type = element[:2]
    id = element[3:]
    aid = id.split('_')[0]
    cid = None
    comment = {}
    tags = str
    article = memoir.mb.get(aid).value
    if type == 'ce':
        cid = id.split('_')[1]
        comment = memoir.mb.get(cid).value
        if comment['poster'] != g.user.id:
            flash('You did not write this comment!', 'error')
            return redirect(request.referrer)
        form = CommentForm(request.form)
    elif type == 'ae':
        print article['op'] + ' ' + g.user.id
        if g.user.id !='u1':
            if article['op'] != g.user.id:
                flash('You did not write this article!', 'error')
                return redirect(request.referrer)
        form = ArticleForm(request.form)
        tags = ', '.join(article['tags'])

    if request.method == 'POST':
        if type == 'ce':
            if form.validate_on_submit():
                if len(form.comment.data) < 10 or len(form.comment.data) > 5000:
                    flash("Comment must be between 10 and 5000 characters.", 'error')
                    return redirect(request.referrer)
                comment['comment'] = form.comment.data
                comment['html'] = bleach.clean(markdown.markdown(comment['comment'], extensions=['extra', 'codehilite'],
                                                                 output_format='html5'), memoir.tags_wl, memoir.attrs_wl)
                comment['ts'] = int(time())
                memoir.mb.replace(comment['cid'], comment)

            return redirect(url_for('browse_articles', aid=aid, url=article['url']))
        elif type == 'ae':
            if form.validate_on_submit():
                #print form.content.data
                #print form.tags.data
                article['content'] = form.content.data
                article['html'] = bleach.clean(markdown.markdown(article['content'], extensions=['extra', 'codehilite'],
                                                                 output_format='html5'), memoir.tags_wl, memoir.attrs_wl)
                tags = form.tags.data.split(',')
                article['tags'] = [tag.strip(' \t').lower() for tag in tags]
                new_tag_list = []
                for tag in article['tags']:
                    tag = list(tag)
                    for i in range(0, len(tag)):
                        if tag[i] == ' ':
                            tag[i] = '-'
                    new_tag_list.append(''.join(tag))
                article['tags'] = new_tag_list
                article['ts'] = int(time())
                title = form.title.data
                article['title'] = title

                url = generate_url(title)

                article['url'] = url
                memoir.mb.replace(unicode(article['aid']), article)
                memoir.es_conn.index({'title':article['title'], 'content':article['content'], 'aid':article['aid'],
                                     'position':article['content']}, 'articles', 'articles-type', article['aid'])
                #memoir.es_conn.indices.refresh('articles')

            return redirect(url_for('browse_articles', aid=aid, url=article['url']))
    else:
        return render_template('edit_article.html', title='Edit Article', form=form, article=article, comment=comment, type=type, aid=aid,
                               cid=cid, name=g.user.name, role=g.user.role, user_id=g.user.id, tags=tags, APP_ROOT=memoir.APP_ROOT)


def article_tags(page):
    tags_count = urllib2.urlopen(memoir.DB_URL + 'memoir/_design/dev_kunjika/_view/get_unique_article_tag_count?reduce=true').read()
    tags_count = json.loads(tags_count)

    if 'rows' in tags_count and len(tags_count['rows']):
        if 'value' in tags_count['rows'][0]:
            tags_count = tags_count['rows'][0]['value']
    else:
        tags_count = 0
    print tags_count
    tags = {}

    skip = (page - 1) * memoir.TAGS_PER_PAGE
    tags = urllib2.urlopen(
        memoir.DB_URL + 'memoir/_design/dev_kunjika/_view/get_tags_from_article?limit=' +
        unicode(memoir.TAGS_PER_PAGE) + '&skip=' + unicode(skip) + '&group=true').read()
    tags = json.loads(tags)['rows']

    if not tags and page != 1:
        abort(404)
    pagination = Pagination(page, memoir.TAGS_PER_PAGE, tags_count)
    no_of_tags = len(tags)
    if g.user is not None and g.user.is_authenticated:
        logged_in = True
        return render_template('article_tags.html', title='Article Tags', logged_in=logged_in, pagination=pagination,
                               tags=tags, no_of_tags=no_of_tags, name=g.user.name, role=g.user.role, user_id=g.user.id, APP_ROOT=memoir.APP_ROOT)
    return render_template('article_tags.html', title='Articles Tags', pagination=pagination, tags=tags,
                           no_of_tags=no_of_tags, APP_ROOT=memoir.APP_ROOT)


def save_draft(element):
    if g.user.id == -1:
        return redirect(url_for('login'))
    articleForm = ArticleForm(request.form)
    if g.user is not None and g.user.is_authenticated:
        if articleForm.validate_on_submit() and request.method == 'POST':
            user = g.user.user_doc
            try:
                memoir.mb.get(element).value
            except:
                if 'draft_count' not in user:
                    user['draft_count'] = 1
                    doc = {}
                    doc['drafts_list'] = []
                    doc['drafts_list'].append(1)
                    memoir.mb.add('dl-' + unicode(g.user.id), doc)
                else:
                    user['draft_count'] += 1
                    drafts_list = memoir.mb.get('dl-' + unicode(g.user.id)).value
                    drafts_list['drafts_list'].append(user['draft_count'])
                    memoir.mb.replace('dl-' + unicode(g.user.id), drafts_list)

            memoir.mb.replace(unicode(g.user.id), user)
            article = {}
            article['content'] = {}
            title = articleForm.title.data
            article['content'] = articleForm.content.data
            article['html'] = bleach.clean(markdown.markdown(article['content'], extensions=['extra', 'codehilite'],
                                                             output_format='html5'), memoir.tags_wl, memoir.attrs_wl)
            article['tags'] = []
            article['tags'] = articleForm.tags.data.split(',')
            article['tags'] = [tag.strip(' \t').lower() for tag in article['tags']]
            new_tag_list = []
            for tag in article['tags']:
                tag = list(tag)
                for i in range(0, len(tag)):
                    if tag[i] == ' ':
                        tag[i] = '-'
                new_tag_list.append(''.join(tag))
            article['tags'] = new_tag_list
            article['title'] = title
            article['_type'] = 'd'

            url = generate_url(title)

            article['url'] = url
            article['op'] = unicode(g.user.id)
            article['ts'] = int(time())
            article['updated'] = article['ts']
            article['ip'] = request.remote_addr
            article['aid'] = 'ad-' + unicode(g.user.id) + '-' + unicode(user['draft_count'])
            article['opname'] = g.user.name
            article['cids'] = []

            memoir.mb.set(unicode(article['aid']), article)
            return redirect(url_for('drafts', did=article['aid'], url=article['url']))

        return render_template('write_article.html', title='Write Artcile', form=articleForm, artpage=True, name=g.user.name, role=g.user.role,
                               user_id=g.user.id, APP_ROOT=memoir.APP_ROOT)
    return redirect(url_for('login'))


def drafts(page, did, request):
    if g.user.id == -1:  # -1 is the user id of anonymous user
        return redirect(url_for('login'))

    if did is None:
        try:
            count = len(memoir.mb.get('dl-' + unicode(g.user.id)).value)
        except:
            flash('You have no drafts!', 'error')
            return redirect(request.referrer)
        drafts_list = get_drafts_for_page(page, memoir.ARTICLES_PER_PAGE, count)
        if not drafts_list and page != 1:
            abort(404)
        pagination = Pagination(page, memoir.ARTICLES_PER_PAGE, count)
        if g.user is None:
            return render_template('drafts.html', title='Drafts', artpage=True, articles=drafts_list,
                                   pagination=pagination, APP_ROOT=memoir.APP_ROOT)
        elif g.user is not None and g.user.is_authenticated:
            return render_template('drafts.html', title='Drafts', artpage=True, articles=drafts_list,
                                   name=g.user.name, role=g.user.role, user_id=g.user.id, pagination=pagination, APP_ROOT=memoir.APP_ROOT)
        else:
            return render_template('drafts.html', title='Drafts', artpage=True, articles=drafts_list,
                                   pagination=pagination, APP_ROOT=memoir.APP_ROOT)
    else:
        article = memoir.mb.get(did).value
        article['tstamp'] = strftime("%a, %d %b %Y %H:%M", localtime(article['ts']))
        user = memoir.mb.get(article['op']).value
        article['email'] = user['email']
        article['opname'] = user['name']

        if g.user is None:
            return render_template('single_draft.html', title='Articles', artpage=True, article=article, APP_ROOT=memoir.APP_ROOT)

        elif g.user is not None and g.user.is_authenticated:
            return render_template('single_draft.html', title='Articles', artpage=True, article=article,
                                   name=g.user.name, role=g.user.role, user_id=g.user.id, APP_ROOT=memoir.APP_ROOT)
        else:
            return render_template('single_draft.html', title='Articles', artpage=True, article=article, APP_ROOT=memoir.APP_ROOT)


def get_drafts_for_page(page, ARTICLES_PER_PAGE, count):
    skip = (page - 1) * ARTICLES_PER_PAGE
    drafts_list = memoir.mb.get('dl-' + unicode(g.user.id)).value
    dl = drafts_list['drafts_list']
    dids_list = dl[skip:skip+ARTICLES_PER_PAGE]
    articles_list = []
    dl = []
    for did in dids_list:
        dl.append('ad-' + unicode(g.user.id) + '-' + unicode(did))
    if len(dl) != 0:
        val_res = memoir.mb.get_multi(dl)

    for id in dl:
        articles_list.append(val_res[unicode(id)].value)

    for i in articles_list:
        i['tstamp'] = strftime("%a, %d %b %Y %H:%M", localtime(i['ts']))

        user = memoir.mb.get(i['op']).value
        i['opname'] = user['name']

    return articles_list


def edit_draft(element):
    did = element
    tags = str
    article = memoir.mb.get(did).value
    if g.user.id !='u1':
        if int(article['op']) != int(g.user.id):
            flash('You did not write this article!', 'error')
            return redirect(request.referrer)
    form = ArticleForm(request.form)
    tags = ', '.join(article['tags'])

    if request.method == 'POST' and form.validate_on_submit():
        article['content'] = form.content.data
        article['html'] = bleach.clean(markdown.markdown(article['content'], extensions=['extra', 'codehilite'],
                                                         output_format='html5'), memoir.tags_wl, memoir.attrs_wl)
        tags = form.tags.data.split(',')
        article['tags'] = [tag.strip(' \t').lower() for tag in tags]
        new_tag_list = []
        for tag in article['tags']:
            tag = list(tag)
            for i in range(0, len(tag)):
                if tag[i] == ' ':
                        tag[i] = '-'
            new_tag_list.append(''.join(tag))
        article['tags'] = new_tag_list
        article['ts'] = int(time())
        memoir.mb.replace(unicode(article['aid']), article)

        return redirect(url_for('drafts', did=did, url=article['url']))
    else:
        return render_template('edit_draft.html', title='Edit', form=form, article=article, type=type, aid=did,
                               name=g.user.name, role=g.user.role, user_id=g.user.id, tags=tags, APP_ROOT=memoir.APP_ROOT)

 
def publish(element):
    print "In publish"
    articleForm = ArticleForm(request.form)
    did = element.split('-')[2:]
    article = memoir.mb.get(element).value
    if g.user.id !='u1':
        if int(article['op']) != int(g.user.id):
            flash('You did not write this article!', 'error')
            return redirect(request.referrer)

    if g.user is not None and g.user.is_authenticated:
        if articleForm.validate_on_submit() and request.method == 'POST':
            article = {}
            article['content'] = {}
            title = articleForm.title.data
            article['content'] = articleForm.content.data
            tags = articleForm.tags.data.split(',')
            article['html'] = bleach.clean(markdown.markdown(article['content'], extensions=['extra', 'codehilite'],
                                                             output_format='html5'), memoir.tags_wl, memoir.attrs_wl)
            article['tags'] = []
            article['tags'] = articleForm.tags.data.split(',')
            article['tags'] = [tag.strip(' \t').lower() for tag in article['tags']]
            new_tag_list = []
            for tag in article['tags']:
                tag = list(tag)
                for i in range(0, len(tag)):
                    if tag[i] == ' ':
                            tag[i] = '-'
                new_tag_list.append(''.join(tag))
            article['tags'] = new_tag_list
            article['title'] = title
            article['_type'] = 'a'

            url = generate_url(title)
            article['tags'] = [i for i in article['tags'] if i != "" ]
            article['url'] = url
            article['op'] = unicode(g.user.id)
            article['ts'] = int(time())
            article['updated'] = article['ts']
            article['ip'] = request.remote_addr
            aid = memoir.mb.incr('acount').value
            article['aid'] = 'a-' + unicode(aid)
            article['opname'] = g.user.name
            article['cids'] = []
            user = memoir.mb.get(unicode(g.user.id)).value
            user['rep'] += 25
            memoir.mb.replace(unicode(g.user.id), user)

            memoir.es_conn.index({'title': title, 'content': article['content'], 'aid': article['aid'],
                                   'position': article['content']}, 'articles', 'articles-type', article['aid'])
            #memoir.es_conn.indices.refresh('articles')
            memoir.mb.add(unicode(article['aid']), article)
            memoir.mb.delete(element)
            dl = memoir.mb.get('dl-' + unicode(g.user.id)).value
            dl['drafts_list'].remove(int(did[0]))
            memoir.mb.replace('dl-' + unicode(g.user.id), dl)
            return redirect(url_for('browse_articles', aid=article['aid'], url=article['url']))

        return render_template('edit_draft.html', title='Edit', form=articleForm, article=article, type=type, aid=element,
                               name=g.user.name, role=g.user.role, user_id=g.user.id, tags=tags, APP_ROOT=memoir.APP_ROOT)
    return redirect(url_for('login'))


def send_async_email(msg):
    memoir.mail.send(msg)

