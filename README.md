# osudl

# Command used to get tournament md files
```
for i in MWC SEAC SOFT 4DM TMT TNMT CMC CJB_4K CMT_4K GBC MBS MXB MP MCNC FL4T OMIC SAS SOL THOM_CUP TMC o\!mLN o\!mAC; do for j in $(find $i -type f -name "en.md"); do cd `dirname $j` && k=$(basename "$PWD") && mv en.md ~/Desktop/osudl/md/"$i-$k.md" && cd ~/Desktop/osu-wiki/wiki/Tournaments; done; && cd ~/Desktop/osudl/md/ && do rm "$i-$i.md" done
```

## Features
1. Batch downloads - Get beatmaps from sources (userpages, beatmap packs, mappools, .db/.txt files, google sheets)
2. Post download verification - after imports, db read again to verify map has been imported, collection can be added from (1) to group downloaded maps
3. maybe: Modern Web GUI - dashboard to do score tracking / session planner, osu collection viewer (group maps by tags), preview and rate change maps
