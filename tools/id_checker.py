#!/usr/bin/env python3
"""
A simple (?) Flask HTTP(S?) server to check if supplied ID(s) - ASINs and/or
ISBNs) are known to a running instance of the ISFDB database, returning a
JSON response.

Dependencies:

  Flash (installed from PyPI, or your distro's package manager, etc

Usage:

  export FLASK_ENV=development ; export FLASK_APP=tools/id_checker.py ; flask run

References:
* https://medium.com/@onejohi/building-a-simple-rest-api-with-python-and-flask-b404371dc699
"""

from datetime import datetime
import logging
import os
import sys
import time

# import json # flask.jsonify might be enough?

# isfdb_tools
from isfdb_lib.common import get_connection
from isfdb_lib.identifier_related import check_asin, check_isbn
from isfdb_lib.ids_in_memory import (initialise, # load_ids, load_fixer_ids,
                                     batch_check_in_memory, batch_check_with_stats)

IN_MEMORY_DATA = True

conn = get_connection()


from flask import Flask, jsonify, request, make_response
# https://stackoverflow.com/questions/25594893/how-to-enable-cors-in-flask
from flask_cors import CORS, cross_origin

app = Flask(__name__)
cors = CORS(app)
app.config['CORS_HEADERS'] = 'Content-Type'

@app.route('/')
def index():
    return 'ID Checker server running at %s' % (datetime.now())


def json_response(data):
    """
    JSON lists/arrays aren't ideal for passing back metadata, so use HTTP
    headers instead, which are arguably better suited for the task.
    """
    resp =  make_response(jsonify(data))
    resp.headers['X-ID-Checker-API-Version'] = '0.2'

    # Next line didn't seem to work; I'm guessing it only affected explicit
    # request handlers we define, not OPTIONS
    # resp.headers['Access-Control-Allow-Origin'] = '*' # Needed for Chrome 87+ ?
    # See https://stackoverflow.com/questions/25594893/how-to-enable-cors-in-flask
    return resp


@app.route('/check/<id_to_check>')
def check_id_response(id_to_check):
    """
    For simple tests only - use /batch_check/ for real production code.
    """

    if check_asin(conn, id_to_check) or check_isbn(conn, id_to_check):
        # return jsonify(True)
        return jsonify([{
            "id": id_to_check,
            "known": True
            }])
    else:
        return jsonify([{
            "id": id_to_check,
            "known": False
            }])

def batch_check_via_database(vals, output_function=print):
    ret = []
    known_count = 0
    start = time.time()

    for i, id_to_check in enumerate(vals):
        # print('%d. Checking %s ...' % (i, id_to_check))
        is_known = check_asin(conn, id_to_check) or check_isbn(conn, id_to_check)
        if is_known:
            known_count += 1
        ret.append({
            "id": id_to_check,
            "known": is_known
        })
    output_function('Checked %d IDs, of which %d were known, in %.3f seconds' %
                    (len(ret), known_count, time.time() - start))
    return ret


if IN_MEMORY_DATA:
    # Don't run this twice, per
    # https://stackoverflow.com/questions/9449101/how-to-stop-flask-from-initialising-twice-in-debug-mode
    if os.environ.get('WERKZEUG_RUN_MAIN') == 'true':
        checker_function = batch_check_in_memory
        def batch_stats_wrapper(vals):
            return batch_stats(vals, do_fixer_checks=True,
                               check_both_isbn10_and_13=True)

        checker_function = batch_check_with_stats
        print('About to call initialise()...')
        initialise(conn)
        print('Returned from initialise().')
        conn.close()
else:
    checker_function = batch_check_via_database

@app.route('/batch_check/', methods=['POST'])
@cross_origin()
def batch_check_response():

    # print(request) # Doesn't show anything useful
    # print(request.form) # "ImmutableMultiDict - also useless for JSON
    # print(request.get_json()) # Bingo

    # ret = batch_check_via_database(request.get_json())
    ret = checker_function(request.get_json())

    # return jsonify(ret)
    return json_response(ret)


