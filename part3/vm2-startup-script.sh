#!/bin/bash

set -e

apt-get update
apt-get install -y python3 python3-pip git

cd /opt

git clone https://github.com/cu-csci-4253-datacenter/flask-tutorial

cd flask-tutorial

python3 setup.py install
pip3 install -e .
export FLASK_APP=flaskr
flask init-db
nohup flask run -h 0.0.0.0 > /var/log/flask.log 2>&1 &
