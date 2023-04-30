#!/bin/bash -x

FILE=$1
echo $FILE
DT=`echo $FILE | sed 's/backup.MySQL.[0-9][0-9].//g' | sed 's/\.zip//g' | sed 's/\-//g'`
echo $DT

unzip $FILE
mv cygdrive cygdrive.${DT}
(
    cd cygdrive.${DT}/c/ISFDB/Backups
    mysql --user=root --password=isfdbtest isfdb < backup-MySQL*
)

