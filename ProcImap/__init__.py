""" 
The ProcImap package provides an API for the IMAP protocol, subclassing from
the "mailbox" and "email" packages provided by the Python standard library.

This allows to handle messages stored in an IMAP mailbox in much the same way
as e.g. messages stored in an mbox or maildir format (with some limitations).
This abstract interface is  much nicer than having to work with the standard
library's imaplib module, which is only a very thin wrapper around the IMAP
protocol itself.

In addition, ProcImap contains a number of "utility" functions and classes,
targeted for automatic processing/filtering of email messages, interactive work
on an an IMAP server from inside ipython, and writing consistent command line
tools operating on IMAP mailboxes.

The original intent of the ProcImap package was to provide a framework inspired
by the traditional procmail (http://www.procmail.org) tool, allowing to filter
and organize incoming email messages (hence the name). However, in the course
of development the focus has shifted to creating an abstract API for working
with IMAP messages, while processing incoming mail has become of secondary
interest. 

Nonetheless, you can easily use ProcImap to assist in writing simple scripts
that process incoming mails on your standard IMAP server. You should be advised
however that many of the techniques that work fine on a standard IMAP mailbox
do not work so well when trying to apply them to a Gmail account. While
technically Gmail fulfills all specifications of the IMAP protocol, the
philosophy behind the system is rather incompatible (look for my "Accessing
Gmail through Python" blog post at michaelgoerz.net). Since Gmail is my primary
email provider, this explains the shift of focus in the direction of
development.

I use ProcImap as the basis for a new-mail-notification-tool, as well as to
perform backups of my Gmail account (see http://github.com/goerz/gmailbkp).
I've also used ProcImap to assist in migrating large amounts of messages
between accounts, and to debug IMAP servers interactively in an ipython
console.
"""
