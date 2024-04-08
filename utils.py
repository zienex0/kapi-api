from flask import Response
import json

# TODO: Sprawdzanie czy wszystkie pola sa wypelnione
def fields_not_empty(data):
    if isinstance(data, dict):
        pass
    pass


def pretty_json_response(data, status=200):
    response = Response(
        response=json.dumps(data, indent=2, ensure_ascii=False),
        status=status,
        mimetype='application/json'
    )
    return response

