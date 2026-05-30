import subprocess
import sys
import os

gcloud_path = r"C:\Users\ashwa\linkedin_ai_bot\gcloud_sdk\google-cloud-sdk\bin\gcloud.cmd"
python_path = r"C:\Users\ashwa\linkedin_ai_bot\venv\Scripts\python.exe"

env = os.environ.copy()
env["CLOUDSDK_PYTHON"] = python_path

code = sys.argv[1]

print(f"Logging in with code: {code}")
p = subprocess.Popen([gcloud_path, "auth", "login", "--no-launch-browser"], 
                     stdin=subprocess.PIPE, 
                     stdout=subprocess.PIPE, 
                     stderr=subprocess.PIPE,
                     env=env,
                     text=True)

stdout, stderr = p.communicate(input=code + "\n")
print("STDOUT:", stdout)
print("STDERR:", stderr)
