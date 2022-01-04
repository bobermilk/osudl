# osudl
## Running not from source instructions
1. Download the osudl binary from https://www.mediafire.com/file/yzj51ll4x6y9960/osudl/file
2. Open terminal and cd to cloned repo directory 
3. ```chmod 755 osudl && ./osudl```

## Running from source instructions
1. Go to your osu dashboard and create a new application. Leave the application redirect url blank and name it whatever you want.
2. Copy the id and secret and POST in headers to /authorize endpoint to obtain ouauth token
3. Set the OAUTH_TOKEN variable in osudl.py with your own
4. ```pip install -r requirements.txt```
5. ```python osudl.py```
