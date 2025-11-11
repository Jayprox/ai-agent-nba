import requests

url = "https://api.balldontlie.io/v1/players?search=lebron"
headers = {"Authorization": "Bearer d2ca1dd0-abb7-475b-a805-9f42ce88a160"}

resp = requests.get(url, headers=headers)
print(resp.status_code)
print(resp.json())
