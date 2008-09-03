#!/usr/bin/env python
"""
    This example shows how to restore a backup created by backup_mailbox.py"
"""
from ProcImap.ImapMailbox import ImapMailbox
from ProcImap.MailboxFactory import MailboxFactory
from ProcImap.ImapMessage import ImapMessage
from mailbox import mbox
import sys

# usage: restore_mailbox.py backupmbox imapmailbox

mailboxes = MailboxFactory('/home/goerz/.procimap/mailboxes.cfg')
server = mailboxes.get_server('Gmail')
mailbox = ImapMailbox((server, sys.argv[2]))
backupsource = mbox(sys.argv[1], factory=ImapMessage)

for message in backupsource:
    if message.has_key("X-ProcImap-Imapflags"):
        message.flags_from_string(message["X-ProcImap-Imapflags"])
        del message["X-ProcImap-Imapflags"]
    if message.has_key("X-ProcImap-ImapInternalDate"):
        message. internaldate_from_string(message["X-ProcImap-ImapInternalDate"])
        del message["X-ProcImap-ImapInternalDate"]
    mailbox.add(message)

mailbox.close()
backupsource.close()
sys.exit(0)
