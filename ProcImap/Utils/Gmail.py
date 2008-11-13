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

""" This module contains functions that make it easier to work with Gmail.
    Identity is established by message-id and size
"""

def is_gmail_box(mailbox):
    """ Return True if the mailbox is on a Gmail server, False otherwise """
    pass

def gmail_delete(mailbox, uid):
    """ Delete the message with uid in the mailbox by moving it to the Trash,
    and then deleting it from there.  This removes all copies of the mail from
    other mailboxes on the Gmail server as well.

    Return 0 if mail was removed successfully
    Return 1 if mail was not moved to the Trash folder
    Return 2 if mail was moved to Trash folder, but not removed from there
    """
    header = mailbox.get_header(uid)
    messageid = header['message-id']
    size = mailbox.get_size(uid)
    mailboxname = mailbox.name
    try:
        mailbox.move(uid, '[Gmail]/Trash')
    except:
        return 1
    mailbox.flush()
    try:
        mailbox.switch('[Gmail]/Trash')
        to_delete = mailbox.search("HEADER message-id %s" % messageid)
        for message in to_delete:
            if mailbox.get_size(message) == size:
                mailbox.add_imapflag(uid, "\\Deleted")
    except:
        return 2
    mailbox.flush() 
    mailbox.switch(mailboxname)


def gmail_get_conversation(mailbox, uid):
    """ Return a list of uid's from the mailbox that contain all messages
        belonging to the same conversation as uid. This includes reply's
        and forwards. The relationship between messages is determined from
        the message ID and the appropriate reference headers.
        You can use this on a non-Gmail server, too, if you are sure that
        all messages on the server have message id's.
    """
    pass

def gmail_get_labels(mailbox, uid):
    """ Return the list of mailboxes on the server that contain the message
        with uid. As in general, message identity is established by the
        message id and the message size
    """
    pass
