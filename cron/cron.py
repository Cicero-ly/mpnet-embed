import requests
import os
import sys
import time


class Job:
    def __init__(self):
        endpoint_url = os.environ["EMBED_JOB_ENDPOINT"]
        self.job_start_url = f"{endpoint_url}/run-embed"
        self.job_status_url = f"{endpoint_url}/get-job-status"
    
    def start_job(self):
        print("Starting job...")
        response = requests.post(self.job_start_url, json={"max_size": 5000})
        print(response.text)
        if response.status_code != 200:
            return response
        return self.poll_job_status(response)
    
    def poll_job_status(self, response):
        print("Job started/resumed successfully.")
        job_id = response.json()["job_id"]
        data = {"id": job_id}
        for i in range(1,13):
            print(f"Polling job status ({i}/12)...")
            response = requests.get(self.job_status_url, params=data)
            if response.status_code != 200:
                return response
            status = response.json()["status"]
            if "error" in status.lower():
                print("Job failed with status: " + status)
                response.status_code = 500
                return response
            if "success" in status.lower():
                print("Job complete with status: " + status)
                return response
            time.sleep(10)
        return response


if __name__ == "__main__":
    job = Job()
    response = job.start_job()

    if response.status_code != 200:
        sys.exit(1)
    else:
        sys.exit(0)