#!/bin/sh
echo `cat .bumpversion.cfg | grep current_version | awk '{ print $3 }'`
