#!/usr/bin/env python
"""
This example shows how to decrypt a mailbox that has GPG-encrypted emails.
"""
import sys

from ProcImap.Utils.Processing import pipe_message
from ProcImap.Utils.CLI import ProcImapOptParser
from ProcImap.ImapMailbox import ImapMailbox
from ProcImap.Utils.Gmail import GmailCache, is_gmail_box, delete
import mailbox as Mailbox # I'm already using 'mailbox' as a variable name

decryptprogram = "/Users/goerz/bin/eml_decrypt.pl -mbox -w"

opt = ProcImapOptParser()
opt.usage = '%prog [options] SERVER MAILBOXES'
opt.add_option('--backup', dest='backup', 
               help='backup mailbox (local mbox file)')
opt.add_option('--cache', dest='cachefile', 
               help='cache file for gmail accounts')
(options, args) = opt.parse_args(args=sys.argv)

if len(args) < 2:
    opt.print_usage()
    sys.exit(1)

mailbox_server_name = args[1]
mailbox_server = options.profile.get_server(mailbox_server_name)

if options.backup is not None:
    backupbox = Mailbox.mbox(options.backup)
else:
    print >> sys.stderr, "You must use a backup mailbox"
    sys.exit(1)

if 'imap.gmail.com' in mailbox_server.servername:
    if options.cachefile is None:
        print >> sys.stdout, "Gmail Mailboxes require a cache"
        sys.exit(1)
    else:
        cache = GmailCache(mailbox_server)
        cache.load(options.cachefile)
        cache.autosave = options.cachefile
        cache.update()


for mailbox_name in args[2:]:
    mailbox =  ImapMailbox((mailbox_server.clone(), mailbox_name))
    print "\n\nProcessing mailbox %s" % mailbox.name
    encrypted = mailbox.search('UNDELETED HEADER Content-Type encrypted')
    for uid in encrypted:
        print "    Decrypting UID %s" % uid
        message = mailbox[uid]
        labels = [mailbox_name] # all the mailboxes the mail appears (for gmail)
        if options.backup is not None:
            print "        Backing up the original (encrypted) message"
            backupbox.add(message)
        print "        Deleting the original (encrypted) message"
        if is_gmail_box(mailbox):
            labels = cache.get_labels("%s.%s" % (mailbox_name, uid))
            delete(mailbox, uid)
        else:
            mailbox.discard(uid)
        print "        Piping message through decryption program"
        try:
            message = pipe_message(message, decryptprogram)
        except:
            # the decryption program sometimes stalls. This try-except block
            # allows to use Ctrl+C to get out of processing this specific mail
            pass
        print "        Done"
        for labelbox_name in labels:
            # this can be done more efficiently once we are able to find the UID
            # of a message that was just uploaded to the mailbox
            labelbox = ImapMailbox((mailbox_server.clone(), labelbox_name))
            print "        Putting decrypted text into mailbox %s" % labelbox_name
            labelbox.add(message)
            labelbox.close()
    mailbox.close()
sys.exit(0)
