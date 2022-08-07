import os
f=open("failed.txt","w+")
for beatmap in os.listdir("/home/milk/Desktop/osu!/Songs/Failed"):
    f.write("https://osu.ppy.sh/beatmapsets/{}".format(beatmap[:-4]))
    f.write("\n")



