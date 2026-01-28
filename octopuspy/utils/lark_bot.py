import os
import time
import json
import requests
from datetime import datetime

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_PATH = os.path.join(BASE_DIR, 'data')
if not os.path.exists(DATA_PATH):
    os.mkdir(DATA_PATH)


HEADERS = {"Content-Type": "application/json"}
BASE_URL = '' # larkbot hook url

def send_message(mid, message, hook):
    if mid:
        cached_warning = get_local_cache(mid)
        if cached_warning and (time.time() - float(cached_warning['last_report'])) < 30 * 60:
            return

    if type(message) is dict:
        message = json.dumps(message, indent=4)

    body = json.dumps({
        "msg_type": "text",
        "content": {
            "text": message,
        }
    })
    res = requests.post(f'{BASE_URL}{hook}', data=body, headers=HEADERS)
    if mid:
        cached_warning['last_report'] = int(time.time())
        cached_warning['message'] = message
        save_local_cache(mid, cached_warning)
    return res

def get_local_cache(fn):
    fn += '.json'
    if os.path.exists(os.path.join(DATA_PATH, fn)):
        return json.load(open(os.path.join(DATA_PATH, fn)))
    return {}

def save_local_cache(fn, data):
    fn += '.json'
    return json.dump(data, open(os.path.join(DATA_PATH, fn), 'w'))
