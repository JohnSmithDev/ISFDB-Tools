# ISFDB Tools - Work-in-progress tools to query a local copy of the ISFDB database.

## Dependencies

Most dependencies should be available by default, or as an optional but 'official'
package from a modern mainstream Linux distribution.  Not sure what the situation
is like for MacOS or Windows - I haven't used the former as a dev platform for
years, and on the latter I usually install a Linux virtual machine (e.g. via
VMWare Player) for anything development like.

Python package dependencies in many cases will be available from Linux distro
repositories, but failing that from PyPI, and thus downloadable via 'pip' or
similar.  (At some point I might get around to doing a `setup.py`.)

* MySQL or MariaDB running the ISFDB database
* Python 3
* SQLAlchemy

### Optional dependencies

* colorama (for nicer output on some scripts; without it you'll get the same
  output, but monochrome)


## Licence

GPL v3 - see [LICENCE.txt](licence.txt) for full text.

All the code is heavily dependent on the ISFDB database, I'm not sure how exactly
that it licenced, but that's a question for them to answer, not me ;_)

## Disclaimers

As per the licence, but also I should explicitly note that this project has no
affiliation with ISFDB, beyond that I have an account there which I've used to
contribute a few updates/bug reports, when these tools have highlighted an
issue with the data.

## Installation

### Prerequisites

I'm afraid I'm unable unwilling to provide much, if any, support for these
steps.

* Install Python 3 and MySQL/MariaDB either via your distribution's package
  repository, or by installing them yourself, or maybe via some pre-built
  container?
* Install Python packages similarly, or via a tool like `pip`
* Download an ISFDB database backup from http://isfdb.org/wiki/index.php/ISFDB_Downloads#Database_Backups
* Get the database set up via the instructions at the bottom of that page e.g.
  http://isfdb.org/wiki/index.php/ISFDB:MySQL_Only_Setup  Those instructions are
  pretty straightforward if you're reasonably comfortable with command-line tools.

You should get to the point where you can connect to the database and run SQL
queries e.g.

    isfdb_tools $ mysql --user=<mysql-username> --password=<mysql-password> isfdb
    Reading table information for completion of table and column names
    You can turn off this feature to get a quicker startup with -A

    Welcome to the MariaDB monitor.  Commands end with ; or \g.
    Your MariaDB connection id is 6
    Server version: 10.1.33-MariaDB MariaDB Server

    Copyright (c) 2000, 2018, Oracle, MariaDB Corporation Ab and others.

    Type 'help;' or '\h' for help. Type '\c' to clear the current input statement.

    MariaDB [isfdb]> select count(1) from titles;
    +----------+
    | count(1) |
    +----------+
    |  1606900 |
    +----------+
    1 row in set (0.00 sec)

(Obviously the total number of titles, database version, etc) depending on what
precise download, database, etc you have.)

## Configuration

Once you have a working database instance that you can connect to, define an
environment variable ISFDB_CONNECTION_DETAILS with the connection string for it.
This is a standard format (documented elsewhere online), and should look something
like

    mysql://isfdb:databaseusername@localhost/databasepassword

For convenience, the environment variable should be set in an initialization
file such as `.bashrc`.  Failing that, you can always either

* Set it manually in your shell session e.g. `export ISFDB_CONNECTION_DETAILS=whatever`
* Prefix it whenever you run a script e.g.

    ISFDB_CONNECTION_DETAILS=whatever ./publication_history.py -a "Stephen Baxter" -T Raft -n novel

At some point I might make this also definable by a command-line argument to the
scripts, but setting an environment variable is surely the best solution for
most/all use cases.

## Running the scripts

Scripts are run in the standard Unix/Linux command line way e.g.

    ./publication_history.py -a "Stephen Baxter" -T Raft -n novel

All scripts support `-h` as an argument to display valid options for that
script e.g.

    isfdb_tools $ ./publication_history.py -h
    usage: publication_history.py [-h] [-a [AUTHOR]] [-A [EXACT_AUTHOR]]
                                  [-t [TITLE]] [-T [EXACT_TITLE]] [-n WORK_TYPES]
                                  [-v]

    List publication countries and dates for a book

    optional arguments:
      -h, --help         show this help message and exit
      -a [AUTHOR]        Author to search on (pattern match, case insensitive)
      -A [EXACT_AUTHOR]  Author to search on (exact match, case sensitive)
      -t [TITLE]         Title to search on (pattern match, case insensitive)
      -T [EXACT_TITLE]   Title to search on (exact match, case sensitive)
      -n WORK_TYPES      Types of work to search on e.g. novels, novellas, etc
                         (case insensitive but otherwise exact match, multiple
                         "OR" values allowed)
      -v                 Log verbosely

Many scripts share common options, e.g. -a/-A for author name, -t/-T for
(book/story) title, -y for year or year range.  A common convention for some
options is that lower case options are case insensitive pattern matches, and
the comparable upper case option is an exact match e.g.

    ./publication_history.py -a "baxter" -t medusa
    ./publication_history.py -a "baxter" -T "The Medusa Chronicles"
    ./publication_history.py -A "Stephen Baxter" -t medusa
    ./publication_history.py -A "Stephen Baxter" -T "The Medusa Chronicles"

all produce the same output (but may not do in the future, if other authors
called Baxter write a book of the same name, or Stephen Baxter writes another
"medusa" novel, etc.)

