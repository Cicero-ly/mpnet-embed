import requests
import os


def make_request():
    endpoint_url = os.environ["EMBED_JOB_ENDPOINT"]
    url = f"{endpoint_url}/run-embed"
    data = {"max_size": 5000}
    response = requests.post(url, json=data)
    return response

if __name__ == "__main__":
    response = make_request()
    print(response.status_code)
    print(response.text)