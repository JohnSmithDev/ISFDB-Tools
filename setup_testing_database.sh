#!/bin/bash
# Set up an ISFDB database for running tests.  This includes:
#
# * Creating a database named after the dated dump being used (if it doesn't
#   already exist)
# * (Optionally) Converting it from MyISAM to InnoDB (so that we can run -
#   and more importantly, roll back - transactions, which might be useful
#   for running tests in some circumstances.
# * Creating readwrite and readonly MySQL user accounts.  (readonly is
#   a slight misnomer, as it can write to the metadata table)
# * (Optionally) creating application accounts, using external code from
#   the ISFDB source code repo
#
# Usage:
#   setup_testing_database -d-u mysql-root-user -p mysql-root-password backup-MySQL-55-20yy-mm-dd
# will create a database called isdfdb-20yy-mm-dd
#
# This may need to be run as root (or a *nix user with mysql permissions) in
# order for stuff like the moving of directory (-d argument) to work.

DATABASE_DIR=""
CONVERT_TO_INNODB=0
CREATE_ACCOUNTS=0
# ISFDB_REPO_DIR="/proj/3rdparty/isfdb-code-svn"
ISFDB_REPO_DIR=""
while getopts "aid:p:r:u:" arg
do
    case $arg in
        a) CREATE_ACCOUNTS=1 ;;
        d) DATABASE_DIR="$OPTARG" ;;
        i) CONVERT_TO_INNODB=1 ;;
        p) MYSQL_ROOT_PASSWORD="$OPTARG" ;;
        r) ISFDB_REPO_DIR="$OPTARG" ;;
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
if [ $CONVERT_TO_INNODB -eq 1 ]
then
    DATABASE="${DATABASE}_innodb"
fi

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


#####################################################################

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
### Create the (MySQL/MariaDB) user accounts, and give them basic privs
###

HOSTS='localhost %' # Q: Is "%" alone sufficient?

create_database_user() {
    USER=$1
    for HOST in $HOSTS
    do
        echo "= Creating $USER@$HOST ="
        # TODO: don't create user if they already exist (avoids misleading error
        #       messages)
        run_mysql_statement "CREATE USER '${USER}'@'${HOST}' IDENTIFIED BY '${USER}';"
        run_mysql_statement "GRANT SELECT ON ${DATABASE}.* TO '${USER}'@'${HOST}';"
        echo
    done

    echo
    echo
}

create_database_user readonly
create_database_user readwrite

for HOST in $HOSTS
do
    # Q: Is "GRANT ALL" too generous?
    run_mysql_statement "GRANT ALL ON ${DATABASE}.* TO 'readwrite'@'${HOST}';"
done


###
### Run the dump restore script
###

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
### (Optionally) convert to InnoDB
###
if [ $CONVERT_TO_INNODB -eq 1 ]
then
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
fi


###
### Add the table specific GRANTs now that the tables exist
###
for HOST in $HOSTS
do
    # I think UPDATE is enough?
    run_mysql_statement "GRANT UPDATE ON ${DATABASE}.metadata TO 'readonly'@'${HOST}';"
done





###
### Create the application users
### See scripts/create_user.py in the ISFDB repo for the origin of this,
### especially the hashed password.
### Note: This relies on a refactored version of create_user.py which doesn't
###       currently exist in the ISFDB repo.
###

create_application_user() {
    USERNAME=$1
    PRIVILEGE=$2

    TEMP_DIR=/tmp/setup_testing_database.$$
    mkdir -p ${TEMP_DIR}


    cat <<EOF1 > ${TEMP_DIR}/localdefs.py
# This was automatically generated by setup_testing_database.sh

HTMLLOC = "localhost"
HTFAKE = "/localhost/cgi-bin"
DBASEHOST = "localhost"
HTMLHOST = "localhost"
COOKIEHOST = "localhost"
WIKILOC = "localhost/wiki"


# For most tests, it's the next three values that are the only ones that will
# be used
USERNAME = "readwrite"
PASSWORD = "readwrite"
DBASE = "$DATABASE"

UNICODE = "iso-8859-1"
DO_ANALYTICS = 0

EOF1


    # Copying the script is a hack to force it to use our localdefs.py
    # rather than the one in the repo directory - it seems that the directory
    # of the called script will always be at the front of sys.path regardless
    # of anything we set PYTHONPATH to.
    cp -p ${ISFDB_REPO_DIR}/scripts/create_user.py ${TEMP_DIR}
    python2 ${TEMP_DIR}/create_user.py ${USERNAME} ${USERNAME} ${PRIVILEGE}

    # Earlier version that required a refactored version of create_user.py - works,
    # but doesn't need to be this complicated

#    PYTHONPATH=${TEMP_DIR}:/proj/3rdparty/isfdb-code-svn/scripts python2 - <<EOF2
#from create_user import update_database, setup_database
#
#db = setup_database("localhost", "$MYSQL_ROOT_USER", "$MYSQL_ROOT_PASSWORD", "$DATABASE")
#print("$USERNAME","$PRIVILEGE")
#update_database(db, "$USERNAME", "$USERNAME", $PRIVILEGE)
#db.commit()
#db.close()
#EOF2


    /bin/rm -rf ${TEMP_DIR}
}


if [ $CREATE_ACCOUNTS -eq 1 ]
then
    create_application_user TestModerator 1
    create_application_user TestEditor 0
fi

