""" 
The ProcImap package fulfills two purposes: 

a) provide a reasonably simple framework for writing filters on an IMAP
   Mailbox, inspired by procmail recipes

b) provide a nice object oriented interface to IMAP accounts that integrates
   well with the standard library

Traditionally, many people have used procmail (http://www.procmail.org) to
organize their emails. They pull their email in from one or more POP servers
(or receive it directly on their machine) and then filter the incoming mail
through a series of procmail "recipes". The procmail recipes can deliver the
mail to arbitrary mail folders (based on header data), put it through a spam
filter (e.g. spamassassin), modify the message (e.g. fix and empty subject
line), separate attachments, or pretty much anything else imaginable.

More recently, access to email over IMAP servers has become rather common and
convenient. IMAP has the huge benefit of allowing people to keep their email on
a central server and access it from everywhere with multiple clients. However,
in many cases, users don't have the ability to use procmail together with an
IMAP server.  In some cases, there are other means of filtering incoming
messages. For example, Google's popular GMail service allows users to define
some filters. These solutions generally don't have the full power of procmail;
it is usually not possible to modify messages.

To fill this gap, I decided to write a python framework that would make it easy
to have "recipes" for incoming mail messages. The idea is to have an IMAP
client that logs into the server and continuously monitors the INBOX for new
messages. These are then run through a series of recipes, and may be moved to
different mailboxes (on the same server or not), or be changed (i.e. replaced
by a modified version)

This framework is provided by the ProcImap module. In ProcImap.ProcImap you
will find the AbstractProcImap class. To write filters for your IMAP inbox, you
have to subclass from this abstract class and fill it with "recipes". Calling
the 'run'-method of your derived class will then start to monitor and filter
your IMAP account. For details, see the documentation of the ProcImap.ProcImap
package.  

While writing the ProcImap.ProcImap class, I felt that python's IMAP interface
was rather weak, providing only the imaplib module, which is basically just a
low level wrapper around the IMAP protocol. Specifically, IMAP was not integrated
in the 'mailbox' and 'email' packages of the standard library.

[...]

To summarize, the ProcImap package has the following structure:

First, for the part that allows you to write filters:
- The ProcImap module, which provides an abstract class from which you can
  derive to write you own filters
- The Utils module, which contains some classes and functions that I
  thought were helpful in the context of writing filters. For example there
  is a class that makes it easy to have blacklists/whitelists

Second, and independently, there is the object oriented IMAP interface:
- The ImapServer module containing the ImapServer class, which is a thin
  layer over the imaplib module of the standard library or the imaplib2 module
  provided by Piers Lauder.
- The ImapMailbox and ImapMessage modules, which integrate into the standard
  library.
 -The MailboxFactory module, which just makes organizing your IMAP accounts
  easier: You can define the account data (with all the clear-text-passwords) in
  a central configuration file, and then create ImapMailbox objects on the fly
  based on that data.
The ImapMailbox class is the "frontend" class, which you will be dealing
with most of the time.
Lastly, the  imaplib2 module is included, which was written by Piers
Lauder. It is a direct replacement of the imaplib module in the standard
library, and is used as a backend for my ImapServer class by default. Since
the original purpose of the ProcImap package was to create clients that
continuously monitor your INBOX, the IMAP 'idle' command was very useful.
Unfortunately, the idle command is not supported by the imaplib library, but
only by the multi-threaded imaplib2. On some systems, I have seen problems with
the imaplib2 library (lock-ups of the connection). If you experience problems,
you can set a flag in the source code of the ImapServer module to use the
standard imaplib library. See the documentation of the ImapServer module
for details.
"""
