# ISFDB Tools - Tools to query a local copy of the ISFDB database

A collection of Python 3 scripts and libraries to do analysis on a locally
running copy of the [ISFDB](http://www.isfdb.org) database.  Whilst there are
several scripts that replicate some of the functionality of that website at the
*nix command line, the main aim is to providing tooling to do more complicated
and resource-intensive analyses.

Some of the scripts are intended primarily for use as libraries to feed data
into code outside of this repository for further processing, data visualization,
etc, and so may have fairly rudimentary/user-unfriendly output.

## Licence

GPL v3 - see [LICENCE.txt](docs/LICENCE.txt) for full text.

All the code is heavily dependent on the ISFDB database, I'm not sure how exactly
that is licenced, but that's a question for them to answer, not me ;_)

## Disclaimers

As per the licence, but also I should explicitly note that this project has no
affiliation with ISFDB, beyond that I have an account there which I've used to
contribute a few updates/bug reports, when these tools have highlighted an
issue with the data.

## Dependencies, installation and configuration

See [INSTALLATION.txt](docs/INSTALLATION.txt).


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

