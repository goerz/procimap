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
from ProcImap.ImapMailbox import ImapMailbox

import hashlib
import cPickle
import re

class GmailCache:
    """ Class for keeping track of all the messages and their 
        relationships on a Gmail account 
    """
    def __init__(self, server, autosave=None):
        """ Initialize cache for the given server """
        self._mb = ImapMailbox((server, 'INBOX'))
        self.hash_ids    = {} # sha244hash.size => {...}
                              # {[local_uids], message_id, [references]}
        self.local_uids  = {} # mailboxname.UID => sha244hash.size
        self.message_ids = {} # message-id      => set([sha244hash.size, ..])
        self.mailboxnames = self._mb.server.list()
        self._attempts = 0
        self.autosave = autosave

    def initialize(self, ignore=None):
        """ Discard all cached data, analyze and cache the gmail account"""
        if ignore is None:
            ignore = ['[Gmail]/Trash]', '[Gmail]/Spam']
        self.hash_ids    = {}
        self.local_uids  = {}
        self.message_ids = {}
        self.update(ignore=ignore)
    
    def update(self, ignore=None):
        """ Update the cache """
        if ignore is None:
            ignore = ['[Gmail]/Trash]', '[Gmail]/Spam']
        self._attempts = 0
        try:

            self._mb = ImapMailbox((self._mb.server.clone(), 'INBOX'))
            self.mailboxnames = self._mb.server.list()
            for mailboxname in self.mailboxnames:
                if mailboxname in ignore:
                    continue
                print ("Processing Mailbox %s" % mailboxname)
                self._mb.switch(mailboxname)
                uids_on_server = self._mb.get_all_uids()

                # delete mails that were deleted on the server from the cache

                print ("  Removing mails that were deleted on the server ...")
                # find local_uids in the current mailbox which are in the
                # cache but not on the server anymore
                local_uids_to_delete = [] 
                local_mailbox_uids = self.local_mailbox_uids(mailboxname)
                local_mailbox_uids.sort(key = lambda x: int(x.split('.')[-1]))
                local_uid_iterator = iter(local_mailbox_uids)
                try:
                    for uid_on_server in uids_on_server:
                        local_uid = local_uid_iterator.next()
                        while not local_uid.endswith(str(uid_on_server)):
                            local_uids_to_delete.append(local_uid)
                            local_uid = local_uid_iterator.next()
                except StopIteration:
                    pass
                # For all the mails found above, remove the data from
                # self.local_uids, self.hash_uids, and self.message_ids
                for local_uid in local_uids_to_delete:
                    print "    Removing %s from cache" % local_uid
                    hash_id = self.local_uids[local_uid]['hash_id']
                    message_id = self.hash_ids[hash_id]['message-id']
                    del self.local_uids[local_uid]
                    self.hash_ids[hash_id]['local_uids'].remove(local_uid)
                    if len(self.hash_ids[hash_id]['local_uids']) == 0:
                        del self.hash_ids[hash_id]
                        self.message_ids[message_id].remove(hash_id)
                        if len(self.message_ids[message_id]) == 0:
                            del self.message_ids[message_id]
                print ("  Done.")

                # process new mails 

                print ("  Processing existing/new mails on server")
                iteration = 0

                for uid in uids_on_server:

                    local_uid = "%s.%s" % (mailboxname, uid)

                    print "    Processing %s" % local_uid
                    if self.local_uids.has_key(local_uid):
                        # skip mails that are already in the cache
                        continue
                    iteration += 1
                    if iteration == 1000:
                        # Autosave every 1000 new mails
                        iteration = 0
                        self._autosave()

                    header = self._mb.get_header(uid)
                    sha244hash = hashlib.sha224(header.as_string()).hexdigest()
                    size = self._mb.get_size(uid)
                    hash_id = "%s.%s" % (sha244hash, size)
                    message_id = header['message-id']

                    # put into self.message_ids
                    if message_id is None:
                        print("%s has no message-id!" % local_uid)
                        print("You are strongly advised to give each message "
                              "a unique message-id")
                    else:
                        if self.message_ids.has_key(message_id):
                            self.message_ids[message_id].add(hash_id)
                            if len(self.message_ids[message_id]) > 1:
                                print("WARNING: You have different messages "
                                      "with the same message-id. This is "
                                      "pretty bad. Try to fix your message-ids")
                        else:
                            self.message_ids[message_id] = set([hash_id])

                    # put into self.hash_ids
                    if self.hash_ids.has_key(hash_id):
                        self.hash_ids[hash_id]['local_uids'].append(local_uid)
                    else:
                        references = references_from_header(header)
                        self.hash_ids[hash_id] = { 'local_uids' : [local_uid],
                                                   'message_id' : message_id,
                                                   'references' : references }
                    # put into self.local_uids
                    self.local_uids[local_uid] = hash_id

                self._autosave()
                print("  Done.")

        except Exception, data:

            # reconnect
            self._autosave()
            self._attempts += 1
            print "Exception occured: %s (attempt %s). Reconnect." \
                % (data, self._attempts)
            if self._attempts > 500:
                self._attempts = 0
                raise
            self._mb = ImapMailbox((self._mb.server.clone(), 'INBOX'))
            self.update()
        self._attempts = 0

    def local_mailbox_uids(self, mailboxname):
        """ Return a sorted list of all the keys stored in self.local_uids
            that belong to the mailbox with mailboxname. E.g. a call
            to local_mailbox_uids('[Gmail]/All Mail') might return
            ['[Gmail]/All Mail.4', '[Gmail]/All Mail.10', 
             '[Gmail]/All Mail.12']
        """
        luid_pattern = re.compile(r'(.*)\.[0-9]+')
        result = [luid for luid in self.local_uids.keys() 
                  if (luid_pattern.match(luid).group(1) == mailboxname)]
        result.sort(key = lambda x: int(x.split('.')[-1]))
        return result

    def save(self, picklefile):
        """ Pickle the cache """
        data = { 'hash_ids' : self.hash_ids,
                 'local_uids' : self.local_uids,
                 'message_ids' : self.message_ids}
        output = open(picklefile, 'wb')
        cPickle.dump(data, output, protocol=2)
        output.close()

    def _autosave(self):
        if self.autosave is not None:
            print "Auto-save to %s" % self.autosave
            self.save(self.autosave)

    def load(self, picklefile):
        """ Load pickled cache """
        try:
            input = open(picklefile, 'rb')
            data = cPickle.load(input)
            input.close()
            self.hash_ids = data['hash_ids']
            self.local_uids = data['local_uids']
            self.message_ids = data['message_ids']
        except (IOError, EOFError), exc_message:
            print("Could not read data from %s: %s" % (picklefile, exc_message))
            print("No cached data read")
           

def is_gmail_box(mailbox):
    """ Return True if the mailbox is on a Gmail server, False otherwise """
    # TODO: write this, and use it in the other procedures
    return True

def get_hash_id(mailbox, uid):
    """ Get the hash_id of the message with the given uid in the mailbox.
        mailbox has to be an instance of ImapMailbox

        The hash_id is computed as the sha224 hash of the message's
        header, appended with a dot and the size of the message in
        bytes.
    """
    sha244hash = hashlib.sha224(mailbox.get_header(uid).as_string()).hexdigest()
    size = mailbox.get_size(uid)
    return "%s.%s" % (sha244hash, size)

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
        # is guaranteed to be known already FIXME: THIS IS INCORRECT
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
