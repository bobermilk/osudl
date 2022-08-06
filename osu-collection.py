from urlextract import URLExtract

from buffer import WriteBuffer
import json
import os
import re
import requests
import time
import osudl
API_URL = "https://osu.ppy.sh/api/v2"
TOKEN_URL = 'https://osu.ppy.sh/oauth/token'
missing=""

def get_token():
    data = {
        'client_id': client_id,
        'client_secret': client_secret,
        'grant_type': 'client_credentials',
        'scope': 'public'
    }

    response = requests.post(TOKEN_URL, data=data)

    return response.json().get('access_token')

OAUTH_TOKEN=get_token()
def get_beatmaphash(name,beatmap_id):
    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json",
        "Authorization": f"Bearer {OAUTH_TOKEN}",
    }
    response = requests.get(f"{API_URL}/beatmaps/{beatmap_id}", headers=headers)
    time.sleep(1)
    j=json.loads(response.text)
    try:
        return j["checksum"], j["beatmapset_id"]
    except:
        global missing
        missing+=f"{name}: {beatmap_id}\n"
        return 0,0

def create_collection(tournament_collections, version: int, filename: str):
    b = WriteBuffer()
    b.write_uint(version)
    b.write_uint(len(tournament_collections))
    for name, checksums in tournament_collections.items():
        b.write_string(name)
        b.write_uint(len(checksums))
        for checksum in checksums:
            b.write_string(checksum)
    try:
        os.remove(filename)
    except OSError:
        pass
    db = open(filename, "xb")
    db.write(b.data)
    db.close()
    pass


if __name__ == "__main__":
    urlextractor = URLExtract()
    maps="" # for use with the main program
    tournament_dict={}
    # hardcoded for now
    tourney_dir=os.path.join(os.getcwd(),"md","mania")
    for filename in os.listdir(tourney_dir):
        with open(os.path.join(tourney_dir, filename)) as f:
            name = filename[:-3]
            print(f"downloading {name}...")
            urls=[x for x in urlextractor.find_urls(f.read()) if "beatmapsets" in x]
            tourney_hash=[]
            for url in urls:
                maps+=url
                maps+="\n"
                url=url.replace(')', '/')
                ids=[x for x in url.split("/") if x.isdigit()]
                if len(ids) > 0:
                    beatmapid=int(ids[-1])
                else:
                    continue
                hash, beatmapsetid=get_beatmaphash(name, beatmapid)
                if hash != 0:
                    tourney_hash.append(hash)
            tournament_dict[name]=tourney_hash
    create_collection(tournament_dict, 1, "tournament.db")
    print()
    with open("missing.txt", "w+") as f:
        f.write(missing)
    with open("maps.txt", "w+") as f:
        f.write(maps)

    print("wrote the missing maps to ./missing.txt")
    print()
    print("wrote the tournaments to ./tournament.db")



