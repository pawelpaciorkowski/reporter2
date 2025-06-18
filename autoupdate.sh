#!/bin/bash

DEST_HOST=2.0.205.117
DEST_DIR=/var/www/reporter/backend

pushd `dirname $0` > /dev/null

for fn in `git status --porcelain backend-reporter | awk 'match($1, "M"){print $2}'` ; do
  dest_fn=`echo $fn | sed -e s#backend-reporter#${DEST_DIR}#`
  scp $fn $DEST_HOST:$dest_fn
done

popd > /dev/null
