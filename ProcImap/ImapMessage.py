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

""" This module contains the ImapMessage class, which derives from
    mailbox.Message. The full interface of mailbox.Message including
    conversion to and from other subclasses of mailbox.Message is
    implemented.
"""

import imaplib
import mailbox
import time

INTTIME_FROM_MESSAGE = True # Some mailboxes do not support the notion of an
    # internal time (e.g. mbox). If you convert a message coming from one of 
    # these mailboxes into an ImapMessage, the internal time of the ImapMessage
    # will be set to the time that is specified in the Date header of the
    # original message, if the INTTIME_FROM_MESSAGE flag is set to True. If the
    # flag is set to False, no internal time will be set for the ImapMessage,
    # which usually means the internal time on the server will end up being the
    # upload time. Note that his flag has no effect if the message that is
    # being converted comes from a mailbox format that supports internal times

class ImapMessage(mailbox.Message):
    """ Message with IMAP-specific properties. This class holds information 
        about an IMAP email message that.
        IMAP specific properties consist of IMAP flags, the internal
        date (date when received by the server), and possibly the message
        size.

        Class specific attributes are:

        internaldate    the date and time when the IMAP server received
                        the message (time tuple)
        size            number of bytes of the message, 0 if unknown
    """
    def __init__(self, message=None):
        """ If message is omitted, create new instance in a default, empty 
            state. If message is an email.Message.Message instance, its 
            contents are copied; furthermore, any format-specific information 
            is converted insofar as possible if message is a Message instance. 
            If message is a string or a file, it should contain an 
            RFC 2822-compliant message, which is read and parsed.
            When a MaildirMessage instance is created based upon an 
            mailbox.mboxMessage or mailbox.MMDFMessage instance, the 
            Status: and X-Status: headers are omitted.
        """
        self._imapflags = []
        self.internaldate = time.localtime()
        self.size = 0
        mailbox.Message.__init__(self, message)
        self._get_explanation_from(message)
        if isinstance(message, (mailbox.mboxMessage, mailbox.MMDFMessage)):
            del self['status']
            del self['x-status']

    def _get_explanation_from(self, message):
        """Copy specific state from message to self insofar as possible."""
        if isinstance(message, mailbox.Message):
            if isinstance(message, mailbox.MaildirMessage):
                self._imapflags = imapflags_from_maildir_message(message)
                self.internaldate = time.localtime(message.get_date())
            elif isinstance(message, mailbox.mboxMessage):
                self._imapflags = imapflags_from_mbox_message(message)
                if INTTIME_FROM_MESSAGE:
                    try:
                        date = message['Date']
                        internaldate = seconds_from_date(date) # FIXME: what's this?
                        if internaldate is not None:
                            self.internaldate = internaldate
                    except KeyError:
                        pass
            elif isinstance(message, mailbox.MHMessage):
                self._imapflags = imapflags_from_mh_message(message)
                if INTTIME_FROM_MESSAGE:
                    try:
                        self.internaldate_from_string(message['Date'])
                    except KeyError:
                        pass
            elif isinstance(message, mailbox.BabylMessage):
                self._imapflags = imapflags_from_babyl_message(message)
                if INTTIME_FROM_MESSAGE:
                    try:
                        self.internaldate_from_string(message['Date'])
                    except KeyError:
                        pass
            elif isinstance(message, mailbox.MMDFMessage):
                self._imapflags = imapflags_from_mmdf_message(message)
                if INTTIME_FROM_MESSAGE:
                    try:
                        self.internaldate_from_string(message['Date'])
                    except KeyError:
                        pass

    def _explain_to(self, message):
        """Copy IMAP-specific state to message insofar as possible."""
        if isinstance(message, ImapMessage):
            message._imapflags = self._imapflags
            message.internaldate = self.internaldate
            message.size = self.size
        elif isinstance(message, mailbox.MaildirMessage):
            for flag in maildirflags_from_imap_message(self):
                message.add_flag(flag)
            message.set_date(time.mktime(self.internaldate))
        elif isinstance(message, (mailbox.mboxMessage, mailbox.MMDFMessage)):
            for flag in mboxflags_from_imap_message(self):
                message.add_flag(flag)
            message.set_from('MAILER-DAEMON', time.mktime(self.internaldate))
        elif isinstance(message, mailbox.MHMessage):
            for sequence in mhsequences_from_imap_message(self):
                message.add_sequence(sequence)
        elif isinstance(message, mailbox.BabylMessage):
            for label in babyllabels_from_imap_message(self):
                message.add_label(label)
        elif isinstance(message, mailbox.Message):
            pass
        else:
            raise TypeError('Cannot convert to specified type: %s' %
                            type(message))


    def flagstring(self):
        """ Return string for imap flags """
        return "(%s)" % ' '.join(self._imapflags)
    
    
    def flags_from_string(self, flagstring):
        """ Set the flags from a string as returned by 
            self.flagstring() 
        """
        self.set_imapflags(flagstring[1:-1].split())
    
    def delete(self):
        """ Add the \Deleted flag to the list of imap flags """
        if not "\\Deleted" in self._imapflags:
            self._imapflags.append("\\Deleted")
    
    def remove_imapflag(self, *flags):
        """ Remove flags from the list of imap flags. Do nothing if the 
            flag does not exist. Remember that this is a local modification.
        """
        new_imapflags = []
        flags = [flag.upper() for flag in flags]
        for flagname in self._imapflags:
            if not flagname.upper() in flags:
                new_imapflags.append(flagname)
        self._imapflags = new_imapflags

    def add_imapflag(self, *flags):
        """ Add a flag to the list of imap flags. 
            You cannot add "\RECENT" as a flag.
        """
        for flag in flags:
            if (flag.upper() != "\\RECENT"):
                if flag not in self._imapflags:
                    self._imapflags.append(flag)
    
    def set_imapflags(self, flags):
        """ Set imap flags to flags """
        if isinstance(flags, str):
            flags = [flags]
        self._imapflags = []
        for flag in flags:
            if (flag.upper() != "\\RECENT"):
                if flag not in self._imapflags:
                    self._imapflags.append(flag)

    def get_imapflags(self):
        """ Return a list of imap flags """
        return self._imapflags
    
    def internaldatestring(self):
        """ Return string for internaldate.
            Return None if internaldate is None.
        """
        if self.internaldate is None:
            return None
        return imaplib.Time2Internaldate(self.internaldate)
    
    def internaldate_from_string(self, internaldatestring):
        """ Set the internaldate from a string as it is returned
            by self.internaldatestring()
        """
        self.internaldate = imaplib.Internaldate2tuple(internaldatestring)



# Helper functions for conversion to/from other mailbox.Message instances

def _reverse_mappings(mappings):
    """ Switch key and value in the mappings dict
        Make new keys upper case
    """
    result = {}
    for (key, value) in mappings.items():
        value = value.upper()
        result[value] = key
    return result

def imapflags_from_maildir_message(message):
    """ Return a list of IMAP flags from an MaildirMessage"""
    flagstring = message.get_flags()
    flags = []
    mappings = {
        'D' : '\\Draft',
        'F' : '\\Flagged',
        'P' : '$Forwarded',
        'R' : '\\Answered',
        'S' : '\\Seen',
        'T' : '\\Deleted'
    }
    for (letter, imapflag) in mappings.items():
        if letter in flagstring:
            flags.append(imapflag)
    return flags


def maildirflags_from_imap_message(message):
    """ Return a string of maildir flags from an ImapMessage"""
    result = ""
    imapflags = message.imapflags()
    mappings = {
        'D' : '\\Draft',
        'F' : '\\Flagged',
        'P' : '$Forwarded',
        'R' : '\\Answered',
        'S' : '\\Seen',
        'T' : '\\Deleted'
    }
    mappings = _reverse_mappings(mappings)
    for imapflag in imapflags:
        if mappings.has_key(imapflag):
            result += mappings[imapflag]
    return result

def imapflags_from_mbox_message(message):
    """ Return a list of IMAP flags from an mboxMessage"""
    flagstring = message.get_flags()
    flags = []
    mappings = {
        'F' : '\\Flagged',
        'A' : '\\Answered',
        'R' : '\\Seen',
        'D' : '\\Deleted'
    }
    for (letter, imapflag) in mappings.items():
        if letter in flagstring:
            flags.append(imapflag)
    return flags
        
def mboxflags_from_imap_message(message):
    """ Return a string of mbox flags from an ImapMessage"""
    result = ""
    imapflags = message.imapflags()
    mappings = {
        'F' : '\\Flagged',
        'A' : '\\Answered',
        'R' : '\\Seen',
        'D' : '\\Deleted'
    }
    mappings = _reverse_mappings(mappings)
    for imapflag in imapflags:
        if mappings.has_key(imapflag):
            result += mappings[imapflag]
    return result

def imapflags_from_mh_message(message):
    """ Return a list of IMAP flags from an MHMessage"""
    sequences = message.get_sequences()
    flags = []
    mappings = {
        'flagged' : '\\Flagged',
        'replied' : '\\Answered'
    }
    for (sequence, imapflag) in mappings.items():
        if sequence in sequences:
            flags.append(imapflag)
    return flags

def mhsequences_from_imap_message(message):
    """ Return a list of MH sequences from an ImapMessage"""
    result = []
    imapflags = message.imapflags()
    mappings = {
        'flagged' : '\\Flagged',
        'replied' : '\\Answered'
    }
    mappings = _reverse_mappings(mappings)
    for imapflag in imapflags:
        if mappings.has_key(imapflag):
            result.append(mappings[imapflag])
    return result

def imapflags_from_babyl_message(message):
    """ Return a list of IMAP flags from an BabylMessage"""
    labels = message.get_labels()
    flags = []
    mappings = {
        'forwarded' : '$Forwarded',
        'answered' : '\\Answered',
        'deleted' : '\\Deleted'
    }
    for (label, imapflag) in mappings.items():
        if label in labels:
            flags.append(imapflag)
    return flags
        
def babyllabels_from_imap_message(message):
    """ Return a list of Babyl lables from an ImapMessage"""
    result = []
    imapflags = message.imapflags()
    mappings = {
        'forwarded' : '$Forwarded',
        'answered' : '\\Answered',
        'deleted' : '\\Deleted'
    }
    mappings = _reverse_mappings(mappings)
    for imapflag in imapflags:
        if mappings.has_key(imapflag):
            result.append(mappings[imapflag])
    return result

def imapflags_from_mmdf_message(message):
    """ Return a list of IMAP flags from an MMDFMessage"""
    return imapflags_from_mbox_message(message)

def mmdfflags_from_imap_message(message):
    """ Return a string of MMDF flags from an ImapMessage"""
    return mboxflags_from_imap_message(message)
