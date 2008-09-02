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

""" This module provides the AbstractProcImap class """


import sys
from Utils import log
import select
from mailbox import Mailbox
import time

import ImapServer
from ImapMailbox import ImapMailbox
from ImapMessage import ImapMessage

if ImapServer.STANDARD_IMAPLIB:
    import imaplib
else:
    import imaplib2 as imaplib
 
PROCESSED = 'procimap' # the imap flag used to indicate that a
                       # message has been processed.

TIMEOUT = 120 # max seconds to idle. The idle commands sometimes messes up
              # and doesn't register a new email, so I'm setting this
              # timeout to a rather low value of only two minutes.



class ImplementationError(Exception):
    """  Raised by AbstractProcImap if process_msginfo and process_fullmsg
        did not return values of the required type. This means the user
        made a mistake in implementing them.
    """
    pass


class AbstractProcImap:
    """ Abstract Class ProcImap """
    def __init__(self, mailbox):
        """ Initialize ProcImap
            mailbox must be an instance of ImapMailbox
        """
        if isinstance(mailbox, ImapMailbox):
            self.mailbox = mailbox
            if mailbox.trash is None:
                log("WARNING: There is no trash folder set for the mailbox." \
                    + "No backups will be made! This is very unsafe!")
        else:
            raise TypeError, "mailbox must be an instance of ImapMailbox"
        self.run_once = False
        self.no_processed_flag = False
        self.ignore_processed_flag = False
        self.logfile = None

    def set_unprocessed(self):
        """ Remove the PROCESSED flag to all messages in mailbox """
        for uid in self.mailbox.get_all_uids():
            self.mailbox.remove_imapflag(uid, PROCESSED)

    def set_processed(self):
        """ Add the PROCESSED flag to all messages in mailbox """
        for uid in self.mailbox.get_all_uids():
            self.mailbox.add_imapflag(uid, PROCESSED)

    def set_logfile(self, logfile):
        """ Set a logfile. STDOUT is rerouted to the logfile """
        log("ProcImap: opening logfile %s" % logfile)
        self.logfile = logfile
        sys.stdout = open(logfile, "a", 0)

    def run(self):
        """ Run ProcImap. Refer to the manual for details """
        # TODO: check if this could be done with threading
        if self.run_once:
            uids = self.mailbox.get_all_uids()
            self._process_uids(uids)
            self.mailbox.close()
            sys.exit()
        else:
            while True:
                try:
                    unseen_msgs = self.mailbox.get_unseen_uids()
                    if len(unseen_msgs) > 0:
                        self._process_uids(unseen_msgs)
                        self.mailbox.expunge()
                    try:
                        self.mailbox.server.idle(TIMEOUT)
                    except:
                        log("IDLE caused exception. Sleeping for %s seconds" \
                                                                      % TIMEOUT)
                        time.sleep(TIMEOUT)
                except imaplib.IMAP4.abort, data:
                    log("In run(): caught exception: %s" % str(data))
                    self.mailbox.reconnect()
                    log("Reconnected mailbox")
                    # TODO: check if this could end in an infinite try-except
                    # loop.  It might be a good idea to add rate limiting to
                    # the reconnects

    def _process_uids(self, uids):
        """ Process a list of UIDs """
        for uid in uids:
            # Skip processed (unless ignore_processed_flag)
            if PROCESSED in self.mailbox.get_imapflags(uid) \
            and not self.ignore_processed_flag :
                continue
            # Skip deleted
            if '\\Deleted' in self.mailbox.get_imapflags(uid):
                continue
            # preprocessing
            log("Processing ID %s" % uid)
            header = self.mailbox.get_header(uid)
            header.myflags = {}
            header = self.preprocess(header)
            if not isinstance(header, ImapMessage):
                raise ImplementationError, \
                      "preprocess did not return an ImapMessage"
            # delete if deleted
            if ('\\Deleted' in header.get_imapflags()): 
                log("Deleting Message")
                self.mailbox.discard(uid)
                continue
            # fullprocessing ?
            if hasattr(header, 'fullprocess') and header.fullprocess:
                log("Full processing  of ID %s" % uid)
                # discard original
                message = self.mailbox.get_message(uid)
                self.mailbox.discard(uid)
                # transfer non-standard attributes
                if hasattr(header, 'myflags'):
                    message.myflags = header.myflags
                if hasattr(header, 'mailbox'):
                    message.mailbox = header.mailbox
                # tranfer imap flags from header object
                message.set_imapflags(header.get_imapflags())
                # do full processing
                message = self.fullprocess(message)
                if not isinstance(message, ImapMessage):
                    raise ImplementationError, \
                        "fullprocess did not return an ImapMessage"
                # set processed flag
                if not self.no_processed_flag:
                    message.add_imapflag(PROCESSED)
                # put in target mailbox
                targetmailbox = self.mailbox
                if hasattr(message, 'mailbox'):
                    if isinstance(message.mailbox, Mailbox):
                        if message.mailbox != self.mailbox:
                            targetmailbox = message.mailbox
                log("Putting message in target mailbox")
                targetmailbox.add(message)
            else: # no full processing
                # just copy flags and put in right mailbox
                if not self.no_processed_flag:
                    header.add_imapflag(PROCESSED)
                self.mailbox.set_imapflags(uid, header.get_imapflags())
                if hasattr(header, 'mailbox'):
                    if header.mailbox != self.mailbox:
                        log("Moving message to target mailbox")
                        self.mailbox.move(uid, header.mailbox)

    def preprocess(self, header):
        """ You must override this function
            This function receives an ImapMessage object 'header'
            (consisting only of an email header; the message body will be
            empty), and must return the same 'header' object with
            modifications. The 'header' object that is received has
            a non-standard attribute 'myflags' that is initinalized
            as an empty dict.

            Modifications to the header object have the following
            consequences:

            If you have added a non-standard attribute 'fullprocess' with 
            any value, the full message is downloaded and then passed to
            fullprocess(message). Changes to header fields are discarded.

            If there is no attribute 'fullprocess', the imap flags set
            for the header object are transferred to the server. If the
            \Deleted flag is set, the message is deleted. Otherwise,
            if you have added a non-standard attribute 'mailbox', the
            message is moved to the mailbox set there. The 'mailbox'
            attribute should be a string (indicating a mailbox on the
            current server) or an instance of mailbox.Mailbox. The message
            stays in its current mailbox if there is no
            'mailbox'-attribute.

            You may modify or replace the non-standard attribute
            'myflags', which is intialized as an empty dict, and fill
            it with arbitrary data. The attribute will be present with all
            its data in the full message object that is passed to
            fullprocess(message). The purpose of the 'myflags' attribute
            is to tell fullprocess(message) what to do.

            Note that you may also set the non-standard 'mailbox'
            attribute as described above in combination with the
            'fullprocess' attribute. The 'mailbox' attribute will have no
            direct consequence in this case, but it will be present in
            the message object passed to fullprocess(message). Likewise,
            changes to the imap flags of the 'header' object will also
            be present in the 'message' object.

            In summary, you may modify the 'header' object by changing
            its imapflags, and by adding any of the non-standard
            attributes 'fullprocess', 'mailbox', and 'myflags'. All other
            changes (e.g. to header fields) are discarded. All changes to
            the header fields or the body of the message need to be
            done in fullprocess(message)
        """
        raise NotImplementedError, \
            "You must subclass AbstractProcImap and override the preprocess " \
            +"method. Please refer to the documentation."

    def fullprocess(self, message):
        """ You must override this function
            This function receives an ImapMessage object 'message'
            and must return the same 'message' object with modifications.
            The 'message' object will have the non-standard attributes
            'myflags', and 'mailbox', each containing the data set in
            the previously executed preprocess(header). If these
            attributes were not set in preprocess(header), they will
            not be present in 'message' either.

            You may change the 'message' object in any way at all. The
            changed 'message' object that is returned will be added to
            the target mailbox, the original message will be deleted.

            If the non-standard attribute 'mailbox' is present in
            'message', the target mailbox will be the mailbox set in
            the 'mailbox' attribute. Otherwise, the target mailbox
            will be the original mailbox.
        """
        raise NotImplementedError, \
            "You must subclass AbstractProcImap and override the fullprocess " \
            +"method. Please refer to the documentation."
