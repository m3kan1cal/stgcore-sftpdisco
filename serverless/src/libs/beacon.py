import json

from src.libs.jsonencoder import JsonEncoder


response = {
    'isBase64Encoded': False,
    'headers': {
        'Content-Type': 'application/json',
        'Access-Control-Allow-Origin': '*',
        'Access-Control-Allow-Credentials': True
    },
    'statusCode': 0,
    'body': {}
}


def ok(payload):
    """Wrap up our response for API messaging."""

    try:
        response['statusCode'] = 200
        response['body'] = json.dumps(payload, cls=JsonEncoder)
    except TypeError as exc:
        raise exc

    return response


def bad_request(payload):
    """Wrap up our response for API messaging."""

    try:
        response['statusCode'] = 400
        response['body'] = json.dumps(payload, cls=JsonEncoder)
    except TypeError as exc:
        raise exc

    return response


def server_error(payload):
    """Wrap up our response for API messaging."""

    try:
        response['statusCode'] = 500
        response['body'] = json.dumps(payload, cls=JsonEncoder)
    except TypeError as exc:
        raise exc

    return response
