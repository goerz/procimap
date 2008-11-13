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

""" This module contains functions that work directly on an online
    ImapServer/ImapMailbox.
"""
import email
from ProcImap.Utils.Processing import put_through_pager

DEFAULT_PAGER = 'less'


def display(mailbox, uid, pager=DEFAULT_PAGER, headerfields=None):
    """ Display a stripped down version of the message with UID in
        a pager. The displayed message will contain the the header
        fields set in 'headerfields', and the first BODY section
        (which is usually the human-readable part)

        headerfields defaults to ['Date', 'From', 'To', 'Subject']
        contrary to the declaration.
    """
    header = mailbox.get_header(uid)
    result = ''
    # get body
    body = ''
    (code, data) = mailbox._server.uid('fetch', uid, '(BODY[1])')
    if code == 'OK':
        body = data[0][1]
    # build result
    if headerfields is None:
        headerfields = ['Date', 'From', 'To', 'Subject']
    for field in headerfields:
        if header.has_key(field):
            result += "%s: %s\n" % (field, header[field])
    result += "\n"
    result += body
    put_through_pager(result, pager)


def summary(mailbox, uids, printout=True, printuid=True):
    """ generates lines showing some basic information about the messages
        with the supplied uids. Non-existing UIDs in the list are
        silently ignored.

        If printout is True, the lines are printed out as they
        are generated, and the function returns nothing, otherwise,
        nothing is printed out and the function returns a list of
        generated lines.

        The summary contains
        1) an index (the uid if printuid=True)
        2) the from name (or from address), truncated
        3) the date of the message
        4) the subject, truncated

        Each line has the indicated fields truncated so that it is at
        most 79 characters wide.
    """
    counter = 0
    result = [] # array of lines
    if isinstance(uids, (str, int)):
        uids = [uids]
    for uid in uids:
        try:
            header = mailbox.get_header(uid)
        except: # unspecified on purpose, might be ProcImap.imaplib2.error
            continue
        counter += 1
        index = counter
        if printuid:
            index = str(uid)
        index = "%2s" % index
        (from_name, address) = email.utils.parseaddr(header['From'])
        if from_name == '':
            from_name = address
        date = str(header['Date'])
        datetuple = email.utils.parsedate_tz(date)
        date = date[:16].ljust(16, " ")
        if datetuple is not None:
            date = "%02i/%02i/%04i %02i:%02i" \
                    % tuple([datetuple[i] for i in (1,2,0,3,4)])
        subject = str(header['Subject'])
        subject = ' '.join([s for (s, c) in \
                            email.header.decode_header(subject)])
        length_from = 25-len(index) # width of ...
        length_subject = 35         # ... truncated strings
        generated_line = "%s %s %s %s" \
            % (index,
            from_name[:length_from].ljust(length_from, " "),
            date,
            subject[:length_subject].ljust(length_subject, " "))
        if printout:
            print generated_line
        else:
            result.append(generated_line)
    if not printout:
        return result

