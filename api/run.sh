#!/bin/bash
cd /Users/Joaquin/Desktop/MENTORIA/api
export PYTHONPATH=/Users/Joaquin/Desktop/MENTORIA
/Library/Frameworks/Python.framework/Versions/3.14/bin/uvicorn main:app --host 0.0.0.0 --port 8000
