import re
import argparse

from wget import bar_thermometer
try:
    import wget
    wg = True
except:
    wg = False
import requests
from zipfile import ZipFile
import tempfile
import os
from pathlib import Path
import time

def getIdsFromLinks(links):
    ra = "(?<=beatmapsets\/)([0-9]*)(?=#|\n)" # matches format /beatmapsets/xxxxx#xxxxx or /beatmapsets/xxxxx
    rb = "(.*\/b\/.*)" # matches format /b/xxxxx

    ids = []

    print("Gettings beatmapset IDs from links..............")

    for i in re.findall(ra, links):
        ids.append(i)

    for url in re.findall(rb, links):
        ids.append(re.findall(ra, r.url)[0])

    if len(ids) == 0:
        prefix = 'https://osu.ppy.sh/b/'
        beatmap_ids = links.split('\n')
        for beatmap_id in beatmap_ids:
            url = prefix + beatmap_id
            ids.append(re.findall(ra, r.url)[0])

    return ids

def download(ids, path, name):
    # use temp_dir if no path specified
    path=os.path.join(os.getcwd(),"downloads")

    mirrors = {
        "osu.ppy.sh": "https://osu.ppy.sh/beatmapsets/{}/download"
    }
    # mirrors = { 
        # "beatconnect.io": "https://beatconnect.io/b/{}"
        # }

    dled = []
    failed=""
    for id in ids:
        success = False

        # iterate through all available mirrors and try to download the beatmap
        for m in mirrors:
            url = mirrors[m].format(id)
            print("\nTrying to download #{0} from {1}. Press Ctrl + C if download gets stuck for too long.".format(id, m))

            timeout = False
            filename = os.path.join(path, id + ".osz")
            header={"referer":"https://osu.ppy.sh/beatmapsets/{}".format(id)}

            if os.path.isfile(filename):
                print("\n#{} exists".format(id))
                success = True

            else:
                try:
                    r = requests.get(url, allow_redirects=True, cookies=cookie, headers=header)
                    with open(filename, "wb") as f:
                        f.write(r.content)
                    time.sleep(2)
                except:
                    pass



                dled.append(filename)

                if os.path.isfile(filename):
                    print("\nDownloaded #{}".format(id))
                    success = True
                    

            break
        
        # print fail message if none of the mirrors work or if download didn't complete
        if not success:
            failed+=f"https://osu.ppy.sh/beatmapsets/{id}"
            failed+="\n"
    
    print("\nFinished downloading!")
    print(failed)


    return dled

def add_to_zip(paths, name):
    print("Adding to zip....")
    with ZipFile(name, 'w') as z:
        for f in paths:
            z.write(f, os.basename(f))

# Argument parsing
ap = argparse.ArgumentParser(description='Download beatmaps from a list of links.')

ap.add_argument("-f", "--file", required=True, metavar="pool.txt",
   help="a text file containing beatmap links seperated by newline")
ap.add_argument("-n", "--name", required=True, metavar="example.zip",
   help="the name of the zip file to be created")
ap.add_argument("-o", "--out", required=False, metavar="D:\match_pool\\", default="",
   help="the directory where downloaded beatmaps are to be saved, "
   "use this if you don't want the beatmaps to be deleted after zipping (make sure the folder exists)")
args = vars(ap.parse_args())

# Read ids from file
file = args["file"]

with open(file) as f:
    links = f.read()

ids = getIdsFromLinks(links)

#Start the download
dled = download(ids, args["out"], args["name"])

print("Done!")
