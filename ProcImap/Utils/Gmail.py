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
from ProcImap.Utils.Processing import references_from_header


class GmailCache:
    """ Class for keeping track of all the messages and their 
        relationships on a Gmail account 
    """
    def __init__(self, server):
        """ Initialize cache for the given server """
        self.server = server
        self.cache = []
    def initialize(self):
        """ Discard all cached data, analyze and cache the gmail account"""
        pass
    def update(self):
        """ Update the cache """
        pass
    def save(self):
        """ Pickle the cache """
        pass
    def load(self):
        """ Load pickled cache """
        pass

def is_gmail_box(mailbox):
    """ Return True if the mailbox is on a Gmail server, False otherwise """
    # TODO: write this, and use it in the other procedures
    return True

def delete(mailbox, uid):
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
                mailbox.set_imapflags(message, '\\Deleted')
    except:
        return 2
    mailbox.flush() 
    mailbox.switch(mailboxname)
    return 0


def get_thread(mailbox, uid):
    """ Return a list of uid's from the mailbox that all belong to the same
        conversation as uid. This includes replys, but not necessarilly 
        forwards. The relationship between messages is determined from the 
        message ID and the appropriate reference headers.
        The result list will be sorted.
        You can use this on a non-Gmail server, too, provided that the
        messages on your server have proper message ids. Note that in some
        instances, Gmail (the web interface) will count an email as belonging
        to a certain thread without relying on the message-id references in 
        the headers. This happens with forwards, for example.
        Also, remember that you will only find messages that are in the
        mailbox. So, for complete threads, you should be in 
        '[Gmail]/All Mail'. On non-Gmail servers, you won't be able to
        get complete threads unless you keep all your messages in one
        imap folder.
    """
    thread_uids = set()
    open_ids = set() # id's with unprocessed references
    closed_ids = set() # id's with all references processed
    # look at the "past" of uid (messages referenced by uid)
    header = mailbox.get_header(uid)
    for id in references_from_header(header):
        open_ids.add(id)
    thread_uids.add(uid)
    id = mailbox.get_fields(uid, 'message-id')['message-id'] 
    closed_ids.add(id)
    # look at the "future" of uid (messages referencing uid)
    referencing_uids = mailbox.search(
        "OR (HEADER references %s) (HEADER in-reply-to %s)" % (id, id))
    for referencing_uid in referencing_uids:
        id = mailbox.get_fields(referencing_uid, 'message-id')['message-id'] 
        if id not in closed_ids:
            open_ids.add(id)
        thread_uids.add(referencing_uid)
    # go through all the ids that were found so far, and get their references
    # in turn
    while len(open_ids) > 0:
        open_id = open_ids.pop()
        uids = mailbox.search("HEADER message-id %s" % open_id)
        for uid in uids: 
            # there should only be one uid, unless there are duplicate ids
            thread_uids.add(uid)
        # for open ids, we only need to look into the "future"; the "past"
        # is guaranteed to be known already
        referencing_uids = mailbox.search(
            "OR (HEADER references %s) (HEADER in-reply-to %s)" 
            % (open_id, open_id))
        for referencing_uid in referencing_uids:
            id = mailbox.get_fields(referencing_uid, 
                                    'message-id')['message-id'] 
            if id not in closed_ids:
                open_ids.add(id)
        closed_ids.add(open_id)
    result = list(thread_uids)
    result.sort()
    return result

def get_labels(mailbox, uid):
    """ Return the list of mailboxes on the server that contain the message
        with uid. As in general, message identity is established by the
        message id and the message size
    """
    pass
