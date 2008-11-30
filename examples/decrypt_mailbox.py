#!/usr/bin/env python
"""
This example shows how to decrypt a mailbox that has GPG-encrypted emails.
"""
import sys

from ProcImap.Utils.Processing import pipe_message
from ProcImap.Utils.CLI import ProcImapOptParser
from ProcImap.ImapMailbox import ImapMailbox

opt = ProcImapOptParser()
opt.add_option('--backup', dest='backup', help='backup mailbox')
(options, args) = opt.parse_args(args=sys.argv)

mainbox = args.pop(0)
if options.backup is not None:
    mainbox.trash = options.profile[options.backup]
encr_boxes = [opt.profile[mainbox]]
for mb in args:
    encr_boxes.append(ImapMailbox((opt.profile.get_server(mainbox), mb)))

decryptprogram = "/home/goerz/bin/eml_decrypt.pl -mbox -w"


for mailbox in encr_boxes:
    mailbox.trash = encr_boxes[0].trash
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
