# osu! assistant
## sonarr app but for osu beatmaps


# Command used to get tournament md files
```
for i in MWC SEAC SOFT 4DM TMT TNMT CMC CJB_4K CMT_4K GBC MBS MXB MP MCNC FL4T OMIC SAS SOL THOM_CUP TMC o\!mLN o\!mAC; do for j in $(find $i -type f -name "en.md"); do cd `dirname $j` && k=$(basename "$PWD") && mv en.md ~/Desktop/osudl/md/"$i-$k.md" && cd ~/Desktop/osu-wiki/wiki/Tournaments; done; && cd ~/Desktop/osudl/md/ && do rm "$i-$i.md" done
```

rewrite in C coming soon

## Features
1. Batch downloads with verification - Get beatmaps from sources (userpages, beatmap packs, mappools, .db/.txt files, google sheets)
2. Continuous updates - Acts like rsync for osu collections
3. User interface for collection management  - dashboard to do score tracking / session planner, osu collection viewer (group maps by tags), preview and rate change maps
4. Scans local beatmaps for adding beatmaps unavailable for download into pools,
removes extra downloads
5. Ensures beatmaps get successfully imported and watches beatmap changes

