import requests, sys, json

requestURL = "https://www.ebi.ac.uk/proteins/api/proteomics/ptm?offset=0&size=100&accession=B9FXV5"

r = requests.get(requestURL, headers={ "Accept" : "application/json"})

if not r.ok:
  r.raise_for_status()
  sys.exit()

responseBody = r.json()
with open ("Scripts/try1.json", "w") as fd:
  json.dump(responseBody, fd, indent=4)