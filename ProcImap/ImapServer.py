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

""" This module contains a wrapper around an IMAP Server. It only implements
    the minimum methods needed to work with UID. You'll have to use the
    uid command for almost everything, the commands for the "regular" IDs
    are not supported.
"""

STANDARD_IMAPLIB = True    # this module can use the multithreaded imaplib2
                            # replacement of the standard imaplib module.
                            # If you find imaplib2 to cause problems, you can
                            # switch to to the standard library module
                            # As a consequence, the idle command will not
                            # be available (it will be replace by a dummy).

IDLE_TIMEOUT = 120 # max time to wait in the idle command (this must be less
                   # than 29 minutes)

if STANDARD_IMAPLIB:
    import imaplib
    IDLE_TIMEOUT = 5 # that's how long we sleep in the bogus idle
else:
    # imaplib2 from http://www.cs.usyd.edu.au/~piers/python/imaplib2
    # enables idle command
    import imaplib2 as imaplib

import time
import re


class ClosedMailboxError(Exception):
    """ Raised if a method is called on a closed mailbox """
    pass

class NoSuchMailboxError(Exception):
    """ Raised if a non-existing mailbox is opened """
    pass

class ImapServer:
    """ A small lowlevel representation of an imap server 
    
        Public attributes are:
        servername      address of the server
        username        authentication username
        password        authentication password
        port            server port
        mailboxname     currently active mailbox on the server
    """

    def __init__(self, servername, username, password, ssl=True, port=None):
        """ Initialize the IMAP Server, connect and log in. 
            If you leave the port unspecified, the default port will be used.
            This is port 143 is ssl is disabled, and port 933 if ssl is 
            enabled.
        """
        self.servername = servername
        self.username = username
        self.password = password
        self.port = port # if None, connect() will set this
        self.ssl = ssl
        self._server = None
        self._flags = {
            'connected' : False,    # connected?        connect/disconnect
            'logged_in' : False,    # authenticated?    login/logout
            'open' : False          # opened a mailbox? select/close
        }
        self.mailboxname = None
        self.connect()
        self.login()

    def clone(self):
        """ Return a new instance of ImapServer that points to the same server,
            in a connected and authenticated state.

                >>> server1 = ImapServer('localhost','user','secret')
                >>> server2 = ImapServer('localhost','user','secret')
            is equivalant to
                >>> server1 = ImapServer('localhost','user','secret')
                >>> server2 = server1.clone()
        """
        return ImapServer(self.servername, self.username, 
                          self.password, self.ssl, self.port)

    def connect(self):
        """ Connect to servername """
        if self.ssl:
            if self.port is None:
                self.port = 993
            self._server = imaplib.IMAP4_SSL(self.servername, self.port)
        else:
            if self.port is None:
                self.port = 143
            self._server = imaplib.IMAP4(self.servername, self.port)
        self._flags['connected'] = True

    def disconnect(self):
        """ Disconnect from the server
            If looged in, log out
        """
        if self._flags['logged_in']:
            self.logout()
        self._server = None
        self._flags['connected'] = False


    def login(self):
        """ Identify the client using a plaintext password.
            The password will be quoted.
            Connect to the server is not connected already. If any  problems 
            occur during a login attempt, this method may cause a reconnect
            to the server.
        """
        if not self._flags['connected']:
            self.connect()
        if not self._flags['logged_in']:
            try:
                result =  self._server.login(self.username, self.password)
            except:
                self.reconnect()
                result =  self._server.login(self.username, self.password)
            self._flags['logged_in'] = True
            return result

    def reconnect(self):
        """ Close and then reopen the connection to the server """
        try:
            self.disconnect()
        except:
            pass
        self.connect()

    def idle(self, timeout=IDLE_TIMEOUT):
        """ Put server into IDLE mode until server notifies some change,
            or 'timeout' (secs) occurs (default: 29 minutes),
            or another IMAP4 command is scheduled.
        """
        if STANDARD_IMAPLIB:
            time.sleep(IDLE_TIMEOUT)
        else:
            return self._server.idle(timeout)

    def create(self, name):
        """ Create new mailbox """
        return self._server.create(name)

    def delete(self, name):
        """ Delete old mailbox """
        return self._server.delete(name)

    def subscribe(self, name):
        """ Subscribe to new mailbox """
        return self._server.subscribe(name)

    def unsubscribe(self, name):
        """ Unsubscribe from old mailbox """
        return self._server.unsubscribe(name)

    def logout(self):
        """ Shutdown connection to server. Returns server "BYE"
            response.
        """
        if self._flags['open']:
            self.close()
        self._flags['logged_in'] = False
        return self._server.logout()

    def append(self, mailbox, flags, date_time, messagestr):
        """ Append message to named mailbox. All parameters are strings which
            need to be in the appropriate format as described in RFC3501"""
        if not self._flags['open']:
            raise ClosedMailboxError, "called append on closed mailbox"
        flags = flags.replace("\\Recent", '')
        return self._server.append(mailbox, flags, date_time, messagestr)

    def uid(self, command, *args):
        """ uid(command, arg[, ...])
            Execute command with messages identified by UID.
            Returns response appropriate to command.
        """
        if not self._flags['open']:
            raise ClosedMailboxError, "called uid on closed mailbox"
        return self._server.uid(command, *args)

    def expunge(self):
        """ Permanently remove deleted items from selected mailbox.
            Generates an "EXPUNGE" response for each deleted message.
            Returned data contains a list of "EXPUNGE" message numbers
            in order received.
        """
        if not self._flags['open']:
            raise ClosedMailboxError, "called expunge on closed mailbox"
        return self._server.expunge()

    def close(self):
        """ Close currently selected mailbox. Deleted messages are
            removed from writable mailbox. This is the recommended
            command before "LOGOUT"."""
        self._flags['open'] = False
        self.mailboxname = None
        return self._server.close()

    def select(self, mailbox = 'INBOX', create=False):
        """ Select a mailbox. Log in if not logged in already.
            Return number of messages in mailbox if successful.
            If the mailbox does not exist, create it if 'create' is True,
            else raise NoSuchMailboxError.
            The name of the mailbox will be stored in the mailboxname 
            attribute if selection was successful
        """
        if not self._flags['logged_in']:
            self.login()
        data = self._server.select(mailbox)
        code = data[0]
        count = data[1][0]
        if code == 'OK':
            self._flags['open'] = True
            self.mailboxname = mailbox
            return int(count)
        else:
            if create:
                self.create(mailbox)
                self.select(mailbox, create=False)
            else:
                raise NoSuchMailboxError, "mailbox %s does not exist." \
                                           % mailbox

    def list(self):
        """ Return list mailbox names, or None if the server does
            not send an 'OK' reply.
        """
        if not self._flags['logged_in']:
            raise ClosedMailboxError, "called list before logging in"
        mailbox_pattern = re.compile(
            r'\(\\HasNoChildren\) "/" "(?P<mailboxname>.+)"')
        code, mailboxlist = self._server.list()
        result = []
        if code == 'OK':
            for raw_mailbox in mailboxlist:
                mailbox_match = mailbox_pattern.match(raw_mailbox)
                if mailbox_match:
                    result.append(mailbox_match.group('mailboxname'))
        else:
            return None
        return result

    def lsub(self):
        """ List subscribed mailbox names """
        if not self._flags['logged_in']:
            raise ClosedMailboxError, "called lsub before logging in"
        return self._server.lsub()

    def __eq__(self, other):
        """ Equality test:
            servers are equal if they are equal in servername, username,
            password, port, and ssl.
        """
        return (    (self.servername == other.servername) \
                and (self.username == other.username) \
                and (self.password == other.password) \
                and (self.port == other.port) \
                and (self.ssl == other.ssl) \
               )

    def __ne__(self, other):
        """ Inequality test:
            servers are unequal if they are not equal
        """
        return (not (self == other))
