#!/bin/bash

exec uwsgi -p 4 -s /tmp/kunjika.sock --module memoir --callable kunjika --uid www-data --gid www-data --logto /var/log/uwsgi/uwsgi.log --static-gzip-ext .css
