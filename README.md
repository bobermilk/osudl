# osudl
[![demo video](https://img.youtube.com/vi/cAqbzolegeU/0.jpg)](https://www.youtube.com/watch?v=cAqbzolegeU)
## Running not from source instructions
0. Have chrome installed. 
1. Download the osudl binary from https://www.mediafire.com/file/yzj51ll4x6y9960/osudl/file
2. Open terminal and cd to cloned repo directory.
3. ```chmod 755 osudl && ./osudl```

## Running from source instructions
0. Have chrome and latest python installed.
1. Go to your osu settings and create a new application. Leave the application callback url blank and name it whatever you want.
3. Set the OAUTH_TOKEN variable in osudl.py with your secret obtained in (1).
4. ```pip install -r requirements.txt``` or ```python -m pip install -r requirements.txt```
5. ```python osudl.py```
