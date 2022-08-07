import os
for beatmap in os.listdir("/home/milk/Desktop/osu!/Songs/Failed"):
    os.remove("/home/milk/tournament/beatmaps/{}".format(beatmap))



