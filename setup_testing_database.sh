#!/bin/bash
# Set up an ISFDB database for running tests.  This includes:
#
# * Creating a database named after the dated dump being used (if it doesn't
#   already exist)
# * Converting it from MyISAM to InnoDB (so that we can run - and more importantly,
#   roll back - transactions
# * Creating readwrite and readonly user accounts.  (readonly is a slight misnomer,
#   as it can write to the metadata table)
#
# Usage:
#   setup_testing_database backup-MySQL-55-20yy-mm-dd mysql-root-user mysql-root-password
# will create a database called isdfdb-20yy-mm-dd

DATABASE_DIR=""
while getopts "d:p:u:" arg
do
    case $arg in
        d) DATABASE_DIR="$OPTARG" ;;
        p) MYSQL_ROOT_PASSWORD="$OPTARG" ;;
        u) MYSQL_ROOT_USER="$OPTARG" ;;
    esac
done
shift `expr $OPTIND - 1`

if [ "${MYSQL_ROOT_PASSWORD}" = "" -o "${MYSQL_ROOT_USER}" = "" ]
then
    echo "Must provide MySQL/MariaDB root user and password (-u and -p args)!"
    exit 1
fi


DUMP_NAME=$1
DUMP_BASE=`basename $DUMP_NAME`
DATE=`echo $DUMP_BASE | sed 's/backup-MySQL-55-//g'`
DATABASE=`echo "isfdb-${DATE}" | sed 's/\-/_/g'` # Avoids needing to quote (I think)

# MYSQL_ROOT_USER=$2
# MYSQL_ROOT_PASSWORD=$3

# echo "$DUMP_NAME $MYSQL_ROOT_USER $MYSQL_ROOT_PASSWORD $DATABASE_DIR"


run_mysql_statement() {
    STATEMENT=$1
    echo "Running: ${STATEMENT}"
    mysql --user=${MYSQL_ROOT_USER} --password=${MYSQL_ROOT_PASSWORD} ${DATABASE} \
          -e "${STATEMENT}"
}

run_batch_mysql_statement() {
    # Use this version if you want to parse the output
    STATEMENT=$1
    mysql --user=${MYSQL_ROOT_USER} --password=${MYSQL_ROOT_PASSWORD} ${DATABASE} \
          -B -e "${STATEMENT}"
}

echo "Creating database ${DATABASE}"



###
### Create database, dropping any existing one
### This has to be run as *nix root user I think?!?
###
# Q: Is it correct that the password for mysqladmin is the same as the one
#    we later use for mysql + MYSQL_ROOT_USER?

MYSQL_DATABASE_ROOT=/var/lib/mysql # Q: Does this need to be configurable?
DATABASE_LOCATION="${MYSQL_DATABASE_ROOT}/${DATABASE}"

mysqladmin -f --password=${MYSQL_ROOT_PASSWORD} drop $DATABASE

if [ -L ${DATABASE_LOCATION} ]
then
    # See note a few lines down about hackery...
    /bin/rm -f ${DATABASE_LOCATION}
fi


mysqladmin --password=${MYSQL_ROOT_PASSWORD} create $DATABASE


# Ugly hack time: I don't want to put the test database on my small root
# partition.  However, I don't see there's a "proper" way to specify the DB
# location, hence this hackery with symlinks and moving
if [ "$DATABASE_DIR" != "" ]
then
    if [ -d "${DATABASE_DIR}/${DATABASE}" ]
    then
        # The drop should have gotten rid of these, but let's be sure
        echo "Deleting extant database files at ${DATABASE_DIR}/${DATABASE}..."
        /bin/rm -f ${DATABASE_DIR}/${DATABASE}
    fi
    echo "Moving newly created database at ${DATABASE_LOCATION} to ${DATABASE_DIR}..."
    mv ${DATABASE_LOCATION} ${DATABASE_DIR}
    ln -s ${DATABASE_DIR}/${DATABASE} ${DATABASE_LOCATION}
fi


###
### Create the user accounts, and give them basic privs
###

HOSTS='localhost %' # Q: Is "%" alone sufficient?

create_user() {
    USER=$1
    for HOST in $HOSTS
    do
        echo "= Creating $USER@$HOST ="
        # TODO: don't create user if they already exist (avoids misleading error
        #       messages)
        # mysql --user=${MYSQL_ROOT_USER} --password=${MYSQL_ROOT_PASSWORD} ${DATABASE} \
        #       -e "CREATE USER '${USER}'@'${HOST}' IDENTIFIED BY '${USER}';"
        run_mysql_statement "CREATE USER '${USER}'@'${HOST}' IDENTIFIED BY '${USER}';"
        run_mysql_statement "GRANT SELECT ON ${DATABASE}.* TO '${USER}'@'${HOST}';"
        #mysql --user=${MYSQL_ROOT_USER} --password=${MYSQL_ROOT_PASSWORD} ${DATABASE} \
        #      -e "GRANT SELECT ON '${DATABASE}.*' TO '${USER}'@'${HOST}';"

        echo
    done

    echo
    echo
}

create_user readonly
create_user readwrite

for HOST in $HOSTS
do
    # Q: Is "GRANT ALL" too generous?
    # mysql --user=${MYSQL_ROOT_USER} --password=${MYSQL_ROOT_PASSWORD} ${DATABASE} \
        #          -e "GRANT ALL ON ${DATABASE}.* TO 'readwrite'@'${HOST}';"
    run_mysql_statement "GRANT ALL ON ${DATABASE}.* TO 'readwrite'@'${HOST}';"
done

###
### Run the dump restore script
###

# Weird error message, not sure what this is about (didn't appear until script
# had been running for several minutes:
# Populating database from dump script /mnt/data2019/_isfdb_/cygdrive.20190928/c/ISFDB/Backups/backup-MySQL-55-2019-09-28 ...
# ./setup_testing_database.sh: line 98: --password=readwrite: command not found

# Ran again (after minor tweaks), and another WTF error:
# Populating database from dump script /mnt/data2019/_isfdb_/cygdrive.20190928/c/ISFDB/Backups/backup-MySQL-55-2019-09-28 ...
# ./setup_testing_database.sh: line 106: [: -ne: unary operator expected
# Although I think that's a typo on my part, on closer inspection



# TODO (maybe): Do a replace on the script of "MyISAM" to "InnoDB", so that
# we don't need the following InnoDB conversion step
echo "Populating database from dump script ${DUMP_NAME} ..."
# TODO: this doesn't echo any progress to screen for some reason
mysql --user=readwrite --password=readwrite ${DATABASE} -e "SOURCE ${DUMP_NAME};"

RETVAL=$?
if [ $RETVAL -ne 0 ]
then
    echo "WARNING: database population had non-zero exit status ($RETVAL)"
fi


echo
echo

###
### Convert to InnoDB
###

# See https://dba.stackexchange.com/questions/35073/modify-all-tables-in-a-database-with-a-single-command/35089
# for a (probably) better way of doing all the tables
run_batch_mysql_statement "SHOW TABLES;" | while read TABLE
do
    if [[ $TABLE =~ Tables_in ]]
    then
        # Skip header
        echo
    else
        # echo "Table ---> $TABLE"
        run_mysql_statement "ALTER TABLE $TABLE engine=innodb;"
    fi
done


###
### Add the table specific GRANTs now that the tables exist
###
for HOST in $HOSTS
do
    # I think INSERT is enough?
    run_mysql_statement "GRANT INSERT ON ${DATABASE}.metadata TO 'readonly'@'${HOST}';"
done
