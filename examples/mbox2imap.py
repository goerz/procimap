#!/usr/bin/env python
"""
"""

from ProcImap.ImapMailbox import ImapMailbox
from ProcImap.ImapServer import ImapServer
from ProcImap.ImapMailbox import ImapNotOkError
import sys
import time
import mailbox
from email.Utils import make_msgid

if len(sys.argv) < 3:
    print "Usage: mbox2imap.py <mboxpath> <imapfolder>"
    print "To change the imap server, edit the script"
    sys.exit(2)

# Variables

toserver = ImapServer("imap.gmail.com", "username@gmail.com", "secret", ssl=True)
toboxname = sys.argv[2]

# Processing

tobox = ImapMailbox((toserver, toboxname))
fromboxname = sys.argv[1]
frombox = mailbox.mbox(fromboxname)
frombox.lock()
tobox.lock()


i = 1
print "Processing mbox file %s with %s messages" % (fromboxname, len(frombox))
for message in frombox:
    print "%s" % i
    if message['Message-Id'] is None:
        print "   WARNING: message has no message-id (mesage ID will be added)"
        message.add_header("Message-Id", make_msgid('katamon.mbox2imap') )
    if True:
        try:
            tobox.add(message)
        except ImapNotOkError:
            print "   ERROR: Transaction failed for message %s" % i
            toserver.reconnect()
            tobox = ImapMailbox((toserver, toboxname))
            time.sleep(5)
        time.sleep(1)
        number_in_tobox = len(tobox.get_all_uids())
        #time.sleep(1)
        print "    Added Message, %s in mailbox" % number_in_tobox
    i = i + 1

frombox.close()
tobox.close()
sys.exit(0)
