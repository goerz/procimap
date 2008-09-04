#!/usr/bin/env python
"""
This example shows how to decrypt a mailbox that has GPG-encrypted emails.
"""
import sys

from ProcImap.Utils import pipe_message
from ProcImap.MailboxFactory import MailboxFactory
from ProcImap.ImapMailbox import ImapMailbox


mailboxes = MailboxFactory('/home/goerz/.procimap/mailboxes.cfg')
encr_boxes = [ImapMailbox((mailboxes.get_server("Gmail"), 'INBOX')), 
              ImapMailbox((mailboxes.get_server("Gmail"), '[Gmail]/Sent Mail'))
             ]

decryptprogram = "/home/goerz/bin/eml_decrypt.pl -mbox -w"


for mailbox in encr_boxes:
    mailbox.trash = '[Gmail]/Trash' # for backup (and obligatory for gmail)
    print "\n\nProcessing mailbox %s" % mailbox.name
    encrypted = mailbox.search('UNDELETED HEADER Content-Type encrypted')
    for uid in encrypted:
        print "    Decrypting UID %s" % uid
        message = mailbox[uid]
        print "        Deleting the original (encrypted) message"
        mailbox.discard(uid)
        print "        Piping message through decryption program"
        message = pipe_message(message, decryptprogram)
        print "        Putting decrypted text back into original mailbox %s" \
              % mailbox.name
        mailbox.add(message)
    mailbox.close()
sys.exit(0)
