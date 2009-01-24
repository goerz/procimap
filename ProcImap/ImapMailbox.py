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

""" This module provides the ImapMailbox class, which is a wrapper around
    the imaplib module of the standard library, and a full implementation
    of the mailbox.Mailbox interface.
"""

import imaplib
from email.generator import Generator
from cStringIO import StringIO
from mailbox import Mailbox
from mailbox import Message

from ProcImap.ImapServer import ImapServer
from ProcImap.ImapMessage import ImapMessage


FIX_BUGGY_IMAP_FROMLINE = False # I used this for the standard IMAP server
                                # on SuSe Linux, which seems to be extremely
                                # buggy, and responds to requests for messages
                                # with an escaped(!) envelope-header. Don't
                                # use that server!



class ImapNotOkError(Exception):
    """ Raised if the imap server returns a non-OK status on any request """
    pass

class NoSuchUIDError(Exception):
    """ Raised if a message is requested with a non-existing UID """
    pass

class ReadOnlyError(Exception):
    """ Raised if you try to make a change to a mailbox that was opened 
        read-only """
    pass

class NotSupportedError(Exception):
    """ Raised if a method is called that the Mailbox interface demands,
        but that cannot be surported in IMAP
    """
    pass

class ServerNotAvailableError(Exception):
    """ Raised if you try to open a ImapMailbox using an instance of ImapServer
        that is already used for another ImapMailbox """
    pass



class ImapMailbox(object, Mailbox):
    """ An abstract representation of a mailbox on an IMAP Server.
        This class implements the mailbox.Mailbox interface, insofar
        possible. Methods for changing a message in-place are not
        available for IMAP; the 'update' and '__setitem__' methods
        will raise a NotSupportedError.
        By default deleting messages (discard/remove) just adds the 
        \\Deleted flag to the message. Optionally, you can define a 
        trash folder for any ImapMailbox. If set, "deleted" messages 
        will be moved to the trash folder. Note that you must set the
        trash folder to '[Gmail]/Trash' if you are using Gmail, as 
        the Gmail IMAP server has a different interpretation of what
        deletion means.

        The class specific attributes are:

        name             name of the mailbox (readonly, see below)
        server           ImapServer object (readonly, see below)
        trash            Trash folder
        readonly         True if mailbox is readonly, false otherwise
        
        The 'trash' attribute may a string, another instance 
        of ImapMailbox, or an instance of mailbox.Mailbox.
        If not set, it is None.

        If the 'readonly' attribute is set, all subsequent calls that would
        change the mailbox will raise a ReadOnlyError. Note that setting the
        readonly attribute does not prevent you from making changes through 
        the methods of the server attribute.
    """
    def __init__(self, path, factory=ImapMessage, readonly=False, create=True):
        """ Initialize an ImapMailbox
            path is a tuple with two elements, consisting of
            1) an instance of ImapServer in any state
            2) the name of a mailbox on the server as a string
            If the mailbox does not exist, it is created unless
            create is set to False, in which case NoSuchMailboxError
            is raised.
            The 'factory' parameter determines to which type the
            messages in the mailbox should be converted.

            Note that two instances of ImapMailbox can never share the 
            same instance of server. If you try to create an ImapMailbox
            with an instance of ImapServer that you already used for
            another mailbox, a ServerNotAvailableError will be thrown.
        """
        # not calling Mailbox.__init__(self) is on purpose:
        #  my definition of 'path' is incompatibel
        self._factory = factory
        try:
            (server, name) = path
        except:
            raise TypeError, "path must be a tuple, consisting of an "\
                            + " instance of ImapServer and a string"
        if isinstance(server, ImapServer):
            if hasattr(server, 'locked') and server.locked:
                raise ServerNotAvailableError, "This instance of ImapServer"\
                                    + " is already in use for another mailbox"
            self._server = server
        else:
            raise TypeError, "path must be a tuple, consisting of an "\
                            + " instance of ImapServer and a string"
        if not isinstance(name, str):
            raise TypeError("path must be a tuple, consisting of an "\
                            + " instance of ImapServer and a string")
        self._server.select(name, create)
        self._cached_uid = None
        self._cached_mailbox = None
        self._cached_text = None
        self.trash = None
        self.readonly = readonly
        server.locked = True

    name = property(lambda self: self._server.mailboxname, None, 
                    doc="Name of the mailbox on the server")

    server = property(lambda self: self._server, None,
            doc="Instance of the ImapServer that is being used as a backend")

    def reconnect(self):
        """ Renew the connection to the mailbox """
        name = self.name
        self._server.reconnect()
        self._server.login()
        try:
            self._server.select(name)
        except:
            # for some reason I have to do the whole thing twice if the
            # connection was really broken. I'm getting an exception the
            # first time. Not completely sure what's going on.
            self._server.reconnect()
            self._server.login()
            self._server.select(name) 


    def switch(self, name, readonly=False, create=False):
        """ Switch to a different Mailbox on the same server """
        self.flush()
        if not isinstance(name, str):
            raise TypeError("name must be the name of a mailbox " \
                            + "as a string")
        self._server.select(name, create)
        self._cached_uid = None
        self._cached_text = None
        self.readonly = readonly

    def search(self, criteria='ALL', charset=None ):
        """ Return a list of all the UIDs in the mailbox (as integers)
            that match the search criteria. See documentation
            of imaplib and/or RFC3501 for details.
            Raise ImapNotOkError if a non-OK response is received from
            the server or if the response cannot be parsed into a list
            of integers.

            charset indicates the charset
            of the strings that appear in the search criteria.

            In all search keys that use strings, a message matches the key if
            the string is a substring of the field.  The matching is
            case-insensitive.

            The defined search keys are as follows.  Refer to RFC 3501 for detailed definitions of the
            arguments.

            <sequence set>
            ALL
            ANSWERED
            BCC <string>
            BEFORE <date>
            BODY <string>
            CC <string>
            DELETED
            DRAFT
            FLAGGED
            FROM <string>
            HEADER <field-name> <string>
            KEYWORD <flag>
            LARGER <n>
            NEW
            NOT <search-key>
            OLD
            ON <date>
            OR <search-key1> <search-key2>
            RECENT
            SEEN
            SENTBEFORE <date>
            SENTON <date>
            SENTSINCE <date>
            SINCE <date>
            SMALLER <n>
            SUBJECT <string>
            TEXT <string>
            TO <string>
            UID <sequence set>
            UNANSWERED
            UNDELETED
            UNDRAFT
            UNFLAGGED
            UNKEYWORD <flag>
            UNSEEN

        Example:    search('FLAGGED SINCE 1-Feb-1994 NOT FROM "Smith"')
                    search('TEXT "string not in mailbox"')
        """
        (code, data) = self._server.uid('search', charset, "(%s)" % criteria)
        uidlist = data[0].split()
        if code != 'OK':
            raise ImapNotOkError, "%s in search" % code
        try:
            return [int(uid) for uid in uidlist]
        except ValueError:
            raise ImapNotOkError, "received unparsable response."

    def get_unseen_uids(self):
        """ Get a list of all the unseen UIDs in the mailbox
            Equivalent to search(None, "UNSEEN UNDELETED")
        """
        return(self.search("UNSEEN UNDELETED"))

    def get_all_uids(self):
        """ Get a list of all the undeleted UIDs in the mailbox
            (as integers).
            Equivalent to search(None, "UNDELETED")
        """
        return(self.search("UNDELETED"))

    def _cache_message(self, uid):
        """ Download the RFC822 text of the message with UID and put
            in in the cache. Return the RFC822 text of the message. If the
            message is already in the cache, it is returned directly.
            Raise KeyError if there if there is no message with that UID.
        """
        if (self._cached_uid != uid) or (self._cached_mailbox != self.name):
            try:
                (code, data) = self._server.uid('fetch', uid, "(RFC822)")
                if code != 'OK':
                    raise ImapNotOkError, "%s in fetch_message(%s)" \
                                                                   % (code, uid)
                try:
                    rfc822string = data[0][1]
                except TypeError:
                    raise KeyError, "No message %s in _cache_message" % uid
            except MemoryError:
                # this happens sometimes for unknown reasons. Try do download
                # in chunks instead
                self.reconnect()
                size = self.get_size(uid)
                octets_read = 0
                chunksize = 204800
                chunks = []
                while octets_read < size:
                    attempts = 0
                    while True:
                        try:
                            (code, data) = self._server.uid('fetch', uid, 
                                  "(BODY[]<%s.%s>)" % (octets_read, chunksize))
                            if code != 'OK':
                                raise ImapNotOkError, "%s in fetch_message(%s)"\
                                                                   % (code, uid)
                            break
                        except:
                            self.reconnect()
                            attempts += 1
                            continue
                        if attempts > 10:
                            break
                        chunksize = chunksize / (attempts + 1)
                    try:
                        chunks.append(data[0][1])
                    except TypeError:
                        raise KeyError, "No message %s in _cache_message" % uid
                    octets_read += chunksize
                rfc822string = ''.join(chunks)
            if FIX_BUGGY_IMAP_FROMLINE:
                if rfc822string.startswith(">From "):
                    rfc822string = rfc822string[rfc822string.find("\n")+1:]
            self._cached_uid = uid
            self._cached_mailbox = self.name
            self._cached_text = rfc822string
        return self._cached_text

    def get_message(self, uid):
        """ Return an ImapMessage object created from the message with UID.
            Raise KeyError if there if there is no message with that UID.
        """
        rfc822string = self._cache_message(uid)
        result = ImapMessage(rfc822string)
        result.set_imapflags(self.get_imapflags(uid))
        result.internaldate = self.get_internaldate(uid)
        result.size = self.get_size(uid)
        if self._factory is ImapMessage:
            return result
        return self._factory(result)

    def __getitem__(self, uid):
        """ Return an ImapMessage object created from the message with UID.
            Raise KeyError if there if there is no message with that UID.
        """
        return self.get_message(uid)

    def get(self, uid, default=None):
        """ Return an ImapMessage object created from the message with UID.
            Return default if there is no message with that UID.
        """
        try:
            return self[uid]
        except KeyError:
            return default

    def get_string(self, uid):
        """ Return a RFC822 string representation of the message
            corresponding to key, or raise a KeyError exception if no
            such message exists.
        """
        return self._cache_message(uid)

    def get_file(self, uid):
        """ Return a cStringIO.StringIO of the message corresponding
            to key, or raise a KeyError exception if no such message
            exists.
        """
        return StringIO(self._cache_message(uid))

    def has_key(self, uid):
        """ Return True if key corresponds to a message, False otherwise.
        """
        return (uid in self.search('ALL'))

    def __contains__(self, uid):
        """ Return True if key corresponds to a message, False otherwise.
        """
        return self.has_key(uid)

    def __len__(self):
        """ Return a count of messages in the mailbox. """
        return len(self.search('ALL'))

    def clear(self):
        """ Delete all messages from the mailbox and expunge"""
        if self.readonly:
            raise ReadOnlyError, "Tried to clear read-only mailbox"
        for uid in self.get_all_uids():
            self.discard(uid)
        self.expunge()

    def pop(self, uid, default=None):
        """ Return a representation of the message corresponding to key,
            delete and expunge the message. If no such message exists,
            return default if it was supplied (i.e. is not None) or else
            raise a KeyError exception. The message is represented as an
            instance of ImapMessage unless a custom message factory was
            specified when the Mailbox instance was initialized.
        """
        if self.readonly:
            raise ReadOnlyError, "Tried to pop read-only mailbox"
        try:
            message = self[uid]
            del self[uid]
            self.expunge()
            return message
        except KeyError:
            if default is not None:
                return default
            else:
                raise KeyError, "No such UID"

    def popitem(self):
        """ Return an arbitrary (key, message) pair, where key is a key
            and message is a message representation, delete and expunge
            the corresponding message. If the mailbox is empty, raise a
            KeyError exception. The message is represented as an instance
            of ImapMessage unless a custom message factory was specified
            when the Mailbox instance was initialized.
        """
        if self.readonly:
            raise ReadOnlyError, "Tried to pop item from read-only mailbox"
        self.expunge()
        uids = self.search("ALL")
        if len(uids) > 0:
            uid = uids[0]
            result = (uid, self[uid])
            del self[uid]
            self.expunge()
            return result
        else:
            raise KeyError, "Mailbox is empty"

    def update(self, arg=None):
        """ Parameter arg should be a key-to-message mapping or an iterable
            of (key, message) pairs. Updates the mailbox so that, for each
            given key and message, the message corresponding to key is set
            to message as if by using __setitem__().
            This operation is not supported for IMAP mailboxes and will
            raise NotSupportedError
        """
        raise NotSupportedError, "Updating items in IMAP not supported"


    def flush(self):
        """ Equivalent to expunge() """
        if not self.readonly:
            self.expunge()

    def lock(self):
        """ Do nothing """
        pass

    def unlock(self):
        """ Do nothing """
        pass

    def get_header(self, uid):
        """ Return an ImapMessage object containing only the Header
            of the message with UID.
            Raise KeyError if there if there is no message with that UID.
        """
        (code, data) = self._server.uid('fetch', uid, "(BODY.PEEK[HEADER])")
        if code != 'OK':
            raise ImapNotOkError, "%s in fetch_header(%s)" % (code, uid)
        try:
            rfc822string = data[0][1]
        except TypeError:
            raise KeyError, "No UID %s in get_header" % uid
        result = ImapMessage(rfc822string)
        result.set_imapflags(self.get_imapflags(uid))
        result.internaldate = self.get_internaldate(uid)
        result.size = self.get_size(uid)
        if self._factory is ImapMessage:
            return result
        return self._factory(result)

    def get_fields(self, uid, fields):
        """ Return an mailbox.Message object containing only the requested
            header fields of the message with UID.
            The fields parameter is a string ofheader fields seperated by
            spaces, e.g. 'From SUBJECT date'
            Raise KeyError if there if there is no message with that UID.
        """
        (code, data) = self._server.uid('fetch', uid, 
                                        "(BODY.PEEK[HEADER.FIELDS (%s)])" 
                                        % fields)
        if code != 'OK':
            raise ImapNotOkError, "%s in fetch_header(%s)" % (code, uid)
        try:
            rfc822string = data[0][1]
        except TypeError:
            raise KeyError, "No UID %s in get_fields" % uid
        result = Message(rfc822string)
        return result

     
    def get_size(self, uid):
        """ Get the number of bytes contained in the message with UID """
        try:
            (code, data) = self._server.uid('fetch', uid, '(RFC822.SIZE)')
            sizeresult = data[0]
            if code != 'OK':
                raise ImapNotOkError, "%s in get_imapflags(%s)" % (code, uid)
            if sizeresult is None:
                raise NoSuchUIDError, "No message %s in get_size" % uid
            startindex = sizeresult.find('SIZE') + 5
            stopindex = sizeresult.find(' ', startindex)
            return int(sizeresult[startindex:stopindex])
        except (TypeError, ValueError):
            raise ValueError, "Unexpected results while fetching flags " \
                              + "from server for message %s" % uid

    def get_imapflags(self, uid):
        """ Return a list of imap flags for the message with UID
            Raise exception if there if there is no message with that UID.
        """
        try:
            (code, data) = self._server.uid('fetch', uid, '(FLAGS)')
            flagresult = data[0]
            if code != 'OK':
                raise ImapNotOkError, "%s in get_imapflags(%s)" % (code, uid)
            return list(imaplib.ParseFlags(flagresult))
        except (TypeError, ValueError):
            raise ValueError, "Unexpected results while fetching flags " \
                         + "from server for message %s; response was (%s, %s)" \
                                                             % (uid, code, data)

    def get_internaldate(self, uid):
        """ Return a time tuple representing the internal date for the
            message with UID
            Raise exception if there if there is no message with that UID.
        """
        try:
            (code, data) = self._server.uid('fetch', uid, '(INTERNALDATE)')
            dateresult = data[0]
            if code != 'OK':
                raise ImapNotOkError, "%s in get_internaldate(%s)" % (code, uid)
            if dateresult is None:
                raise NoSuchUIDError, "No message %s in get_internaldate" % uid
            return imaplib.Internaldate2tuple(dateresult)
        except (TypeError, ValueError):
            raise ValueError, "Unexpected results while fetching flags " \
                              + "from server for message %s" % uid


    def __eq__(self, other):
        """ Equality test:
            mailboxes are equal if they are equal in server and name
        """
        if not isinstance(other, ImapMailbox):
            return False
        return (    (self._server == other.server) \
                and (self.name == other.name) \
               )

    def __ne__(self, other):
        """ Inequality test:
            mailboxes are unequal if they are not equal
        """
        return (not (self == other))

    def copy(self, uid, targetmailbox, exact=False):
        """ Copy the message with UID to the targetmailbox and try to return
            the key that was assigned to the copied message in the
            targetmailbox.  If targetmailbox is an ImapMailbox, this is
            the target-UID.
            targetmailbox can be a string (the name of a mailbox on the
            same imap server), any of mailbox.Mailbox. Note that not all
            imap flags will be preserved if the targetmailbox is not on
            an ImapMailbox. Copying is efficient (i.e. the message is not
            downloaded) if the targetmailbox is on the same server.
            Do nothing and return None if there if there is no message with
            that UID.
            Unless 'exact' is set to True, the return value will be None if
            the targetmailbox is an ImapMailbox. This is because finding out
            the new UID of the copied message on an IMAP server is non-trivial.
            Giving 'exact' as True means that additional work will be done to
            find the accurate result. This operation can be relatively
            expensive. If targetmailbox is not an ImapMailbox, the value of
            'exact' is irrelevant, and the return value will always be
            accurate.
        """
        result = None
        if isinstance(targetmailbox, ImapMailbox):
            if targetmailbox.server == self._server:
                targetmailbox = targetmailbox.name # set as string
        if isinstance(targetmailbox, Mailbox):
            if self != targetmailbox:
                targetmailbox.lock()
                result = targetmailbox.add(self[uid])
                if isinstance(targetmailbox, ImapMailbox):
                    result = None
                    targetmailbox.flush()
                    if exact:
                        pass
                        # TODO: get more exact result
                targetmailbox.unlock()
        elif isinstance(targetmailbox, str):
            if targetmailbox != self.name:
                (code, data) = self._server.uid('copy', uid, targetmailbox)
                if code != 'OK':
                    raise ImapNotOkError, "%s in copy: %s" % (code, data)
                if exact:
                    pass
                    # TODO: get more exact result

            else:
                return uid
        else:
            raise TypeError, "targetmailbox in copy is of unknown type."
        return result



    def move(self, uid, targetmailbox, exact=False):
        """ Copy the message with UID to the targetmailbox, delete it in the
            original mailbox, and try to return the key that was assigned to
            the copied message in the targetmailbox. 
            The discussions of the copy method concerning 'targetmailbox' and
            'exact' apply here as well.
            Do nothing and return None if there if there is no message with that UID.
        """
        result = None
        if self.readonly:
            raise ReadOnlyError, "Tried to move message from read-only mailbox"
        if (targetmailbox != self) and (targetmailbox != self.name):
            result = self.copy(uid, targetmailbox, exact)
            (code, data) = self._server.uid('store', uid, \
                                           '+FLAGS', "(\\Deleted)")
            if code != 'OK':
                raise ImapNotOkError, "%s in move: %s" % (code, data)
        else:
            return uid
        return result


    def discard(self, uid, exact=False):
        """ If trash folder is defined, move the message with UID to 
            trash and try to return the key assigned to the message in the
            trash; else, just add the \Deleted flag to the message with UID and
            return None.
            If a trash folder is defined, this method is equivalent to
            self.move(uid, self.trash). The discussions of the move/copy method
            apply.
            Do nothing and return None if there if there is no message with
            that UID.
        """
        result = None
        if self.readonly:
            raise ReadOnlyError, "Tried to discard from read-only mailbox"
        if self.trash is None:
            self.add_imapflag(uid, "\\Deleted")
        else:
            print "Moving to %s" % self.trash
            return self.move(uid, self.trash, exact)
        return result

    def remove(self, uid, exact=False):
        """ Discard the message with UID.
            If there is no message with that UID, raise a KeyError
            This is exactly equivalent to self.discard(uid), except for
            the KeyError exception.
        """
        if self.readonly:
            raise ReadOnlyError, "Tried to remove from read-only mailbox"
        if uid not in self.search("ALL"):
            raise KeyError, "No UID %s" % uid
        return self.discard(uid, exact)

    def __delitem__(self, uid):
        """ Discard the message with UID.
            If there is no message with that UID, raise a KeyError
        """
        self.remove(uid)

    def __setitem__(self, uid, message):
        """ Replace the message corresponding to key with message.
            This operation is not supported for IMAP mailboxes
            and will raise NotSupportedError
        """
        raise NotSupportedError, "Setting items in IMAP not supported"

    def iterkeys(self):
        """ Return an iterator over all UIDs
            This is an iterator over the list of UIDs at the time iterkeys()
            is a called.
        """
        return iter(self.search("ALL"))

    def keys(self):
        """ Return a list of all UIDs """
        return self.search("ALL")

    def itervalues(self):
        """ Return an iterator over all messages. The messages are
            represented as instances of ImapMessage unless a custom message
            factory was specified when the Mailbox instance was initialized.
        """
        for uid in self.search("ALL"):
            yield self[uid]

    def __iter__(self):
        """ Return an iterator over all messages.
            Identical to itervalues
        """
        return self.itervalues()

    def values(self):
        """ Return a list of all messages
            The messages are represented as instances of ImapMessage unless
            a custom message factory was specified when the Mailbox instance
            was initialized.
            Beware that this method can be extremely expensive in terms
            of time, bandwidth, and memory.
        """
        messagelist = []
        for message in self:
            messagelist.append(message)
        return messagelist

    def iteritems(self):
        """ Return an iterator over (uid, message) pairs,
            where uid is a key and message is a message representation.
        """
        for uid in self.keys():
            yield((uid, self[uid]))

    def items(self):
        """ Return a list (uid, message) pairs,
            where uid is a key and message is a message representation.
            Beware that this method can be extremely expensive in terms
            of time, bandwidth, and memory.
        """
        result = []
        for uid in self.keys():
            result.append((uid, self[uid]))
        return result

    def add(self, message):
        """ Add the message to mailbox.
            Message can be an instance of email.Message.Message
            (including instaces of mailbox.Message and its subclasses );
            or an open file handle or a string containing an RFC822 message.
            Return the highest UID in the mailbox, which should be, but
            is not guaranteed to be, the UID of the message that was added.
            Raise ImapNotOkError if a non-OK response is received from
            the server
        """
        if self.readonly:
            raise ReadOnlyError, "Tried to add to a read-only mailbox"
        message = ImapMessage(message)
        flags = message.flagstring()
        date_time = message.internaldatestring()
        memoryfile = StringIO()
        generator = Generator(memoryfile, mangle_from_=False)
        generator.flatten(message)
        message_str = memoryfile.getvalue()
        (code, data) = self._server.append(self.name, flags, \
                                      date_time, message_str)
        if code != 'OK':
            raise ImapNotOkError, "%s in add: %s" % (code, data)
        try:
            return self.get_all_uids()[-1]
        except IndexError:
            return 0


    def add_imapflag(self, uid, *flags):
        """ Add imap flag to message with UID.
        """
        if self.readonly:
            raise ReadOnlyError, \
                       "Tried to add imap flag for message in read-only mailbox"
        for flag in flags:
            (code, data) = self._server.uid('store', uid, '+FLAGS', \
                                           "(%s)" % flag )
            if code != 'OK':
                raise ImapNotOkError, "%s in add_flags(%s, %s): %s" \
                                                       % (uid, flag, code, data)

    def remove_imapflag(self, uid, *flags):
        """ Remove imap flags from message with UID
        """
        if self.readonly:
            raise ReadOnlyError, \
                   "Tried to remove imap flag from message in read-only mailbox"
        for flag in flags:
            (code, data) = self._server.uid('store', uid, '-FLAGS', \
                                           "(%s)" % flag )
            if code != 'OK':
                raise ImapNotOkError, "%s in remove_flag(%s, %s): %s" \
                                                       % (uid, flag, code, data)

    def set_imapflags(self, uid, flags):
        """ Set imap flags for message with UID
            flags must be an iterable of flags, or a string.
            If flags is a string, it is taken as the single flag
            to be set.
        """
        if self.readonly:
            raise ReadOnlyError, \
                      "Tried to set imap flags for message in read-only mailbox"
        if isinstance(flags, str):
            flags = [flags]
        flagstring = "(%s)" % ' '.join(flags)
        (code, data) = self._server.uid('store', uid, 'FLAGS', flagstring )
        if code != 'OK':
            raise ImapNotOkError, "%s in set_imapflags(%s, %s): %s" \
                                                      % (code, uid, flags, data)

    def close(self):
        """ Flush mailbox, close connection to server """
        self.flush()
        self._server.close()
        self._server.logout()
        if hasattr(self._server, 'locked'):
            del self._server.locked

    def expunge(self):
        """ Expunge the mailbox (delete all messages marked for deletion)"""
        if self.readonly:
            raise ReadOnlyError, "Tried to expunge read-only mailbox"
        self._server.expunge()

