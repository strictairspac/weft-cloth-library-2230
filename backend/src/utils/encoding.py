import json


def canonical(value):
    return json.dumps(value, ensure_ascii=False, separators=(',', ':'), sort_keys=True,
                      allow_nan=False).encode('utf-8')
