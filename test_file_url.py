import requests

url = 'https://jcmc.com.np/jcmc/files/journals/1/articles/1784/6911b2f55ca5e.pdf'
r = requests.get(url)
print(f'Status: {r.status_code}')
print(f'Content-Type: {r.headers.get("Content-Type")}')
print(f'Size: {len(r.content)} bytes')
if r.status_code == 200:
    print('✓ Direct file URL works!')
