import urllib.request, json, sys
req = urllib.request.Request(
    'http://127.0.0.1:8080/api/v1/chat/chat-sessions/1/stream', 
    method='POST', 
    data=json.dumps({'mensaje':'hola', 'fuentes_ids':[]}).encode('utf-8'), 
    headers={'Content-Type': 'application/json'}
)
try:
    urllib.request.urlopen(req)
except Exception as e:
    print(e.read().decode('utf-8'))
