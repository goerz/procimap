#!/usr/bin/env python
"""
    This example shows how to read mail on an imap server.
"""
import sys

from ProcImap.Utils.MailboxFactory import MailboxFactory
from ProcImap.Utils.Server import summary, display

mailboxes = MailboxFactory('/home/goerz/.procimap/mailboxes.cfg')
mailbox = mailboxes["Physik"]


def help():
    """ Print help message """
    print "\nEnter message number to read the message"
    print "Enter 'd #', with # being a message number to delete a message"
    print "Press enter to quit\n"


unseen = mailbox.get_unseen_uids()
if len(unseen) == 0:
    print "No unread messages"
    sys.exit(0)
else:
    if '--check' in sys.argv:
        sys.stdout.write("%s unread message" % len(unseen))
        if len(unseen) > 1:
            sys.stdout.write("s\n")
        else:
            sys.stdout.write("\n")
        sys.exit(1)

    # display selector
    print ""
    summary(mailbox, unseen, printuid=False)
    print "\nEnter 'h' for help\n"
    while True:
        # ask for input
        sys.stdout.write("> ")
        answer = sys.stdin.readline().strip()
        try:
            if answer == '' or answer == 'q' or answer == 'exit':
                sys.exit(0)
            elif answer == 'h':
                help()
            elif answer.startswith("d") \
            and len(answer) > 1:
                index_to_delete = int(answer[1:]) -1
                uid_to_delete = unseen[index_to_delete]
                mailbox.discard(uid_to_delete)
                print "Message %s deleted" % (index_to_delete + 1)
            else:
                wanted_index = int(answer) - 1
                wanted_uid = unseen[wanted_index]
                display(mailbox, wanted_uid)
        except Exception, data:
            print "Illegal input: %s" % data
