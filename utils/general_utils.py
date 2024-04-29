from flask import Response, request
import logging

import os
import json


logging.basicConfig(level=logging.INFO)

def fields_not_empty(data):
    if isinstance(data, dict):
        return all(bool(value) for value in data.values())
    return True

def make_cache_key(*args, **kwargs):
    path = request.path
    args = str(hash(frozenset(request.args.items())))
    return (path + args).encode('utf-8')


def pretty_json_response(data, status=200):
    response = Response(
        response=json.dumps(data, indent=2, ensure_ascii=False),
        status=status,
        mimetype='application/json'
    )
    return response
