from requests import get, post, delete

print(get('http://127.0.0.1:5000/api/events/all').json())
print(get('http://127.0.0.1:5000/api/events/age/5').json())
print(get('http://127.0.0.1:5000/api/events/place/6').json())
print(get('http://127.0.0.1:5000/api/events/id/2').json())
print(get('http://127.0.0.1:5000/api/events/id_leader/1').json())