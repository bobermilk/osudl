#!/bin/bash
key=""
rm -rf osudl.spec dist build
pyinstaller --onefile --key=key --clean osudl.py
