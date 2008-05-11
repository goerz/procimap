#!/usr/bin/env python
"""
This example shows how to decrypt a mailbox that has GPG-encrypted emails.
"""
import sys

from ProcImap.Utils import pipe_message
from ProcImap.MailboxFactory import MailboxFactory


mailboxes = MailboxFactory('/home/goerz/.procimap/mailboxes.cfg')
encr_boxes = [mailboxes.get("Physik"), mailboxes.get("PhysikSent")]
backupmailbox = mailboxes.get("Backup")

decryptprogram = "/home/goerz/bin/eml_decrypt.pl -mbox -w"


for mailbox in encr_boxes:
    print "Processing mailbox %s" % mailbox.name
    encrypted = mailbox.search('UNDELETED HEADER Content-Type encrypted')
    for uid in encrypted:
        print "    Decrypting UID %s" % uid
        mailbox.copy(uid, backupmailbox)
        message = mailbox[uid]
        mailbox.discard(uid)
        message = pipe_message(message, decryptprogram)
        mailbox.add(message)
    mailbox.close()
sys.exit(0)



