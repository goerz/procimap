# procimap

The ProcImap package provides an API for the IMAP protocol, subclassing from
the [mailbox][1] and [email][2] packages provided by the Python standard
library.

In addition, ProcImap contains a number of "utility" functions and classes,
targeted for automatic processing/filtering of email messages inside an IMAP
mailbox.

See the [API][3] for more information.

Author: [Michael Goerz](http://michaelgoerz.net)

This code is licensed under the [GPL](http://www.gnu.org/licenses/gpl.html)

## Install ##

### Preparations ###

You may have to edit some global variables *before* you install the package.
If you are on Windows, you might want to set

    DEFAULT_PAGER = 'more' in ProcImap/ImapMailbox.py, and
    STANDARD_IMAPLIB = True in ProcImap/ImapServer.py

Make sure that you have a working python environment. Preferably, get
Python from www.python.org. The Enthought Edition of Python on Windows
is broken! At least last time I tried it.

### Installation into your Python distro ###

To install the ProcImap package, run
    python setup.py install
with sufficient privileges (i.e. as root on linux)


## Usage ##

If you have run the installation successfully, the ProcImap package will
be available in Python. Start programming! For examples, look in the
example directory. Also, have a look at [http://github.com/goerz/gmailbkp][4]

The complete API is available at [http://goerz.github.com/procimap/doc/][3]

[1]: http://docs.python.org/library/mailbox.html
[2]: http://docs.python.org/library/email
[3]: http://goerz.github.com/procimap/doc/
[4]: http://github.com/goerz/gmailbkp
