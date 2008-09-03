#!/usr/bin/env python
"""
This example shows how to set Message-IDs for all messages in a mailbox
"""
import sys

from ProcImap.ProcImap import AbstractProcImap
from ProcImap.ImapMailbox import ImapMailbox
from ProcImap.ImapServer import ImapServer
from ProcImap.ImapMessage import ImapMessage
from ProcImap.Utils import log, pipe_message
from ProcImap.MailboxFactory import MailboxFactory
from email.Utils import make_msgid


mailboxes = MailboxFactory('/home/goerz/.procimap/mailboxes.cfg')
mailbox = mailboxes["Physik"]
mailbox.trash = mailboxes["Backup"]

class IDCreator(AbstractProcImap):

    def preprocess(self, header):
        """ Find Messages without Message ID """
        if header['Message-Id'] is None:
            header.myflags['needs_id'] = True
            log("email without ID")
            header.fullprocess = True

        return header


    def fullprocess(self, message):
        """ Add Message ID's """
        if 'needs_id' in message.myflags.keys():
            message.add_header("Message-Id", make_msgid('procimap') )
        return message


idcreator = IDCreator(mailbox)
idcreator.run_once = True                    # run through all messages and exit.
idcreator.no_processed_flag = True           # don't set the processed flag.
idcreator.ignore_processed_flag = True       # process messages even if they
                                             # have the processed flag set.
idcreator.run()
sys.exit(0)



