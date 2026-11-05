import requests

url = "https://images.unsplash.com"

try:
    response = requests.get(url, timeout=15)

    print("Connection successful")
    print("HTTP status:", response.status_code)

except requests.RequestException as error:
    print("Connection failed:")
    print(error)