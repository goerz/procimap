############################################################################
#    Copyright (C) 2008 by Michael Goerz                                   #
#    http://www.physik.fu-berlin.de/~goerz                                 #
#                                                                          #
#    This program is free software; you can redistribute it and#or modify  #
#    it under the terms of the GNU General Public License as published by  #
#    the Free Software Foundation; either version 3 of the License, or     #
#    (at your option) any later version.                                   #
#                                                                          #
#    This program is distributed in the hope that it will be useful,       #
#    but WITHOUT ANY WARRANTY; without even the implied warranty of        #
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the         #
#    GNU General Public License for more details.                          #
#                                                                          #
#    You should have received a copy of the GNU General Public License     #
#    along with this program; if not, write to the                         #
#    Free Software Foundation, Inc.,                                       #
#    59 Temple Place - Suite 330, Boston, MA  02111-1307, USA.             #
############################################################################
"""
    This module contains the MailboxFactory class, together with some
    Exceptions that are thrown by MailboxFactory, and the pathgenerator
    functions used for the default mailbox types (see documentation
    of MailboxFactory class)


"""

import mailbox
from ConfigParser import ConfigParser

from ProcImap.ImapServer import ImapServer
from ProcImap.ImapMailbox import ImapMailbox

class UnknownMailboxTypeError(Exception):
    """ Raised when there is a mailbox type in the config file that is
        unknown to MailboxFactory. You may have to add it first with the
        'set_type' method.
    """
    pass

class FactoryIsNotMailboxTypeError(Exception):
    """ Raised when you supplied a factory that is not a subclass of
        mailbox.Mailbox.
    """
    pass

class PathgeneratorNotCallableError(Exception):
    """ Raised when you supplied a pathgenerator that is not callable """
    pass

class MailboxOptionsNotCompleteError(Exception):
    """ Raised if there are options missing in the config file that are
        needed in order to produce a mailbox object
    """
    pass

class MailboxFactory:
    """ MailboxFactory is a factory class for Mailbox objects. You can define
        mailboxes of different types in an INI-style config file (the file
        has to parsable by ConfigParser.ConfigParser; the exceptions defined
        in ConfigParser may be thrown if the config file is not well-formed.)
        Each section in the config file describes one mailbox.

        An example of a valid config file 'mailboxes.cfg' is the following:

            [Standard]
            type = IMAP
            mailbox = INBOX
            server = mail.physik.fu-berlin.de
            username = goerz
            password = secret
            ssl = True
            port = 933

            [Sent]
            type = IMAP
            mailbox = Sent
            server = mail.physik.fu-berlin.de
            username = goerz
            password = secret

            [Backup]
            type = mbox
            path = /home/goerz/Mail/backup.mbox

        The type of the mailbox is described by the 'type' parameters. The
        types known by default are 'imap', 'mbox', 'maildir', 'MH', 'Babyl',
        and 'MMDF', all of which have corresponding subclasses of
        mailbox.Mailbox (all except ImapMailbox are defined in the standard
        library). The type specification is not case sensitive.

        The remaining parameters in a specific section depend on the type. The
        Mailbox classes from the standard library need only a path; IMAP needs
        type, mailbox, server, username, and password. The ssl and port
        parameters are optional. ssl is enabled by default; the port, if
        unspecified, is the standard port (933 for ssl, 433 otherwise).

        MailboxFactory has capabilities to extend the set of known types by
        using the set_type method.

        The MailboxFactory partly supports a read-only dictionary interface.
    """
    def __init__(self, configfilename):
        """ Initialize MailboxFactory files.
            The mailbox objects that can be generated must be described in
            configfilename.
        """
        self._types = {}
        self.set_type('mbox', mailbox.mbox, standard_pathgenerator)
        self.set_type('maildir', mailbox.Maildir, standard_pathgenerator)
        self.set_type('mh', mailbox.MH, standard_pathgenerator)
        self.set_type('babyl', mailbox.Babyl, standard_pathgenerator)
        self.set_type('mmdf', mailbox.MMDF, standard_pathgenerator)
        self.set_type('imap', ImapMailbox, imap_pathgenerator)
        self._configparser = ConfigParser()
        self._configparser.read(configfilename)

    def get(self, name):
        """ Create the Mailbox object that is described in section 'name'
            in the config file. For example,
                >>> mailboxes = MailboxFactory("mailboxes.cfg")
                >>> mb = mailboxes.get('Standard')
            mb would now be an object of type ImapMailbox if mailboxes.cfg
            contained the data as the example in the class docstring.
        """
        mailboxtype = self._configparser.get(name, 'type').lower()
        if not mailboxtype in self._types.keys():
            raise UnknownMailboxTypeError, "Unknown type: %s" % mailboxtype
        factory, pathgenerator = self._types[mailboxtype]
        path = pathgenerator(dict(self._configparser.items(name)))
        return(factory(path))

    def __getitem__(self, name):
        """ Shorthand for the get method.
            For example,
                >>> mailboxes = MailboxFactory("mailboxes.cfg")
                >>> mb = mailboxes['Standard']
        """
        return self.get(name)


    def get_server(self, name):
        """ Return an ImapServer instance from the server data that is
            described in section 'name'. The section must have the form of
            an imap mailbox (as described above). A TypeError will be raised
            if the section is not of type IMAP. The 'mailbox' key is ignored.

            For example, you could create an ImapServer like this:

                >>> mailboxes = MailboxFactory("mailboxes.cfg")
                >>> server = mailboxes.get_server('StandardServer')
        """
        mailboxtype = self._configparser.get(name, 'type').lower()
        if mailboxtype != 'imap':
            raise TypeError, "You can only create a server from an IMAP mailbox"
        factory, pathgenerator = self._types[mailboxtype]
        path = pathgenerator(dict(self._configparser.items(name)))
        return(path[0])

    def __contains__(self, name):
        """ Return True if there is a mailbox with the given name, 
            False otherwise """
        return (name in self._configparser.sections())


    def list(self):
        """ List all mailboxes defined in the config file """
        return self._configparser.sections()

    def data(self, name):
        """ List all the data associated with the mailbox name """
        return self._configparser.items(name)

    def set_type(self, typename, factory, pathgenerator):
        """ Make a new typename of Mailbox known. This allows you to
            handle new types of Mailbox objects beyond IMAP and the
            mailboxes of the standard library.

            factory is the class that generates the Mailbox object and must
            be a subclass of mailbox.Mailbox

            pathgenerator is a callable that receives a dict of options set
            in a section of the config file, and returns the 'path' that
            is passed as the first argument to the factory. For the standard
            mailboxes of the standard library, the 'path' is just a string,
            the path of the mailbox in the filesystem. For IMAP, the path
            is a tuple (server, name). For new types, this may be anything.

            For example the constructor of this class makes the 'mbox'
            type known as:
            self.set_type('mbox', mailbox.mbox, standard_pathgenerator)

            In combination,
            factory(pathgenerator(dict_of_options_in_configfile_section))
            should create a Mailbox object of the appropriate type.
        """
        if not issubclass(factory, mailbox.Mailbox):
            raise FactoryIsNotMailboxTypeError
        if not callable(pathgenerator):
            raise PathgeneratorNotCallableError
        self._types[str(typename).lower()] = (factory, pathgenerator)


def imap_pathgenerator(optionsdict):
    """ Converts options into (server, name) tuple """
    try:
        name = optionsdict['mailbox']
        serveraddress = optionsdict['server']
        username = optionsdict['username']
        password = optionsdict['password']
        ssl = True
        if optionsdict.has_key('ssl'):
            if optionsdict['ssl'].lower() in ['0', 'false', 'no']:
                ssl = False
        port = None
        if optionsdict.has_key('port'):
            port = int(optionsdict['port'])
    except KeyError:
        raise MailboxOptionsNotCompleteError, \
              "IMAP Mailbox object needs the following parameters\n " \
              + "'mailbox', 'server', 'username', 'password'.\n" \
              + "The 'ssl' and 'port' parameters are optional."
    server = ImapServer(serveraddress, username, password, ssl, port)
    return(tuple((server, name)))


def standard_pathgenerator(optionsdict):
    """ Extract 'path' from options """
    try:
        return optionsdict['path']
    except KeyError:
        raise MailboxOptionsNotCompleteError, \
              "Standard Mailbox object needs 'path' parameter"
