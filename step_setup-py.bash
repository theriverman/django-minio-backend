#!/usr/bin/env bash

sed -i "s/{{ VERSION_FROM_GIT_TAG }}/$(git describe --tags)/g;s/{{ CURRENT_DATE_YEAR }}/$(date +"%Y")/g" setup.py

echo "The user setup.py contents:"
cat setup.py
