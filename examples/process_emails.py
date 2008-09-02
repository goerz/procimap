#!/usr/bin/env python
# -*- coding: utf-8 -*-
from ProcImap.ProcImap import AbstractProcImap
from ProcImap.ImapMailbox import ImapMailbox
from ProcImap.ImapServer import ImapServer
from ProcImap.Utils import ReplacementListFile, AddressListFile, \
                           pipe_message, log, unknown_to_ascii
from ProcImap.MailboxFactory import MailboxFactory

import time
import os
import sys
from os import system
from mailbox import mbox
from email.Utils import make_msgid
import email.header


############################### Data ###########################################

mailboxes = MailboxFactory('/home/goerz/.procimap/mailboxes.cfg')
mailbox = mailboxes.get("Physik")
mailbox.trash = mailboxes.get("Backup")

logfile = "/home/goerz/.procimap/procimap.log"


spambox = 'Mail/Spam'

whitelist    = AddressListFile("/home/goerz/.procmail/white.lst")
prioritylist = AddressListFile("/home/goerz/.procmail/priority.lst", inmemory=True)
notifylist   = AddressListFile("/home/goerz/.procmail/notify.lst", inmemory=True)
blacklist    = AddressListFile("/home/goerz/.procmail/black.lst")
ownlist = AddressListFile("/home/goerz/.procmail/own.lst", inmemory=True)

replacements = ReplacementListFile("/home/goerz/.procimap/replacements.txt")
replyreplacements = ReplacementListFile("/home/goerz/.procimap/replacements.txt")

decryptprogram="/home/goerz/bin/eml_decrypt.pl -mbox -w"

#########################  Process Singleton   #################################
def run_as_singelton():
    try:
        pid = os.getpid()
        log("Running process %s" % pid)
        f = os.popen("ps -A -F | grep -P goerz.*python.*filter_physik.py$ | grep -v %s" % pid, "r")
        pidline = f.read()
        f.close()
        pid = pidline[pidline.find(" "):].strip() # remove username
        pid = int(pid[:pid.find(" ")].strip())
        log("Killing pid %s" % pid)
        os.system("kill %s" % pid)
    except:
        pass

#########################    Notification  #####################################


def notify(header, priority=False):
    unsafe_subject = header["Subject"]
    unsafe_from = header["From"]
    allowed = "abcdefghijklmnopqrstuvwxyz -._;@!#()<>1234567890"
    safe_subject = []
    safe_from = []
    for character in unsafe_subject:
        if character.lower() in allowed:
            safe_subject.append(character)
    safe_subject = ''.join(safe_subject)
    for character in unsafe_from:
        if character in allowed:
            safe_from.append(character)
    safe_from = ''.join(safe_from)
    msgstring = "%s:%s:%s: You've got new mail from %s\n%s" \
                 % (time.localtime()[3], time.localtime()[4],
                    time.localtime()[5], safe_from,
                    safe_subject)
    log("Notification: %s" % msgstring)
    if priority:
        system(\
            '/opt/kde3/bin/kdialog --title "(PRIORITY) New Mail" --msgbox "%s" &' \
            % msgstring)
        system("play /home/goerz/.sounds/buzzthru.wav &");
    else:
        system('/opt/kde3/bin/kdialog --title "New Mail" --msgbox "%s" &' \
                                                                    % msgstring)



############################ ProcImap Class ####################################

class MyProcImap(AbstractProcImap):

    ###########################################
    def preprocess(self, header):
    ###########################################

        # Leave big messages alone
        if header.size > 10000000:
            log("Big Email Message. Ignoring.")
            return header

        # Find Messages without Message ID
        if header['Message-Id'] is None:
            header.myflags['needs_id'] = True
            log("Email without ID")
            header.fullprocess = True

        # catch encrypted emails
        if header['Content-Type'] is not None \
        and 'multipart/encrypted' in header['Content-Type']:
            header.myflags['encrypted'] = True
            log("Recognized encrypted email")
            header.fullprocess = True

        # put emails sent by me in the Sent folder
        if ownlist.contains(header['From']) \
        and not (   ownlist.contains(header['To']) \
                 or ownlist.contains(header['CC'])):
            log("Recognized as Sent Mail. Putting in Sent mailbox")
            header.mailbox = 'Sent'
            return header # no further processing

        # identify and fix "broken" subject lines
        subject = header['Subject']
        if subject is None:
            log("No Subject Line")
            subject = ''
            header.myflags['no_subject'] = True
            header.fullprocess = True
        if subject == '':
            log("Empty Subject Line")
            subject = '(no subject)'
        if subject.lower().startswith('[spam'):
            # remove the '[Spam ...]' from the subject line
            subject = subject[subject.find(']') + 2 : ]
            log("[Spam] in subject")
        subject = unknown_to_ascii(subject)
        if subject != header['Subject']:
            header.fullprocess = True
            header.myflags['new_subject'] = subject

        # replace 'From', 'Sender' Header
        header_from = header['From']
        if header_from is not None:
            replacement = replacements.lookup(header_from)
            if replacement != header_from:
                log("Replacing FROM line (%s => %s)" \
                                            % (header_from, replacement))
                header.myflags['new_from'] = replacement

                header.fullprocess = True
        header_sender = header['Sender']
        if header_sender is not None:
            replacement = replacements.lookup(header_sender)
            if replacement != header_sender:
                log("Replacing SENDER line (%s => %s)" \
                                            % (header_sender, replacement))
                header.myflags['new_sender'] = replacement

                header.fullprocess = True


        # replace 'Reply-To' Header
        header_reply = header['Reply-To']
        if header_reply is not None:
            replacement = replyreplacements.lookup(header_reply)
            if replacement != header_reply:
                log("Replacing REPLY-TO line (%s => %s)" \
                                            % (header_reply, replacement))
                header.myflags['new_reply'] = replacement

                header.fullprocess = True


        # Mailing Lists
        # Physik
        if header['sender'] is not None \
        and (header['sender'] == "all-bounces@physik.fu-berlin.de" \
        or header['sender'] == "studies-bounces@physik.fu-berlin.de"):
            log("Message in Physik mailing list")
            header.mailbox = "Mail/Physik"
            return header
        # Couchsurfing
        if header['subject'] is not None\
        and (header['subject'].startswith('[CS group digest]')
        or header['subject'].startswith('[CS meet')):
            log("Message in Couchsurfing mailing list")
            header.mailbox = 'Mail/Couchsurfing'
            return header
        # WoV
        if header['From'] is not None\
        and header['From'].startswith('World of Video Newsletter'):
            log("Message in WoV mailing list")
            header.mailbox = 'Mail/WoV'
            return header

        # run through my address lists:
        if prioritylist.contains(header['From']):
            log("FROM is in priority list")
            notify(header, priority=True)
            return header # no further processing
        if notifylist.contains(header['From']):
            log("FROM is in notify list")
            notify(header)
            return header # no further processing
        if whitelist.contains(header['From']) \
        or whitelist.contains(header['Sender']):
            log("FROM or SENDER is in white list")
            return header # no further processing
        if blacklist.contains(header['From']) \
        or blacklist.contains(header['Sender']):
            log("FROM or SENDER is in black list")
            header.delete = True
            return header # no further processing


        # spam filtering
        if header['X-ZEDV-Spam-Status'] is not None \
        and header['X-ZEDV-Spam-Status'].startswith('Yes'):
            log("Recognized ZEDV Spam. Putting in %s" % spambox)
            header.mailbox = spambox
            header.fullprocess = False


        return header

    ############################################
    def fullprocess(self, message):
    ############################################

        # add message ID
        if 'needs_id' in message.myflags.keys():
            message.add_header("Message-Id", make_msgid('procimap') )

        # decrypt
        if 'encrypted' in message.myflags.keys():
            message = pipe_message(message, decryptprogram)

        # replace subject
        if 'no_subject' in message.myflags.keys():
            message.add_header('Subject', message.myflags['new_subject'])
        if 'new_subject' in message.myflags.keys():
            message.replace_header('Subject', message.myflags['new_subject'])

        # replace from/sender
        if 'new_from' in message.myflags.keys():
            message.replace_header('From', message.myflags['new_from'])
        if 'new_sender' in message.myflags.keys():
            message.replace_header('Sender', message.myflags['new_sender'])

        # replace reply-to
        if 'new_reply' in message.myflags.keys():
            message.replace_header('Reply-To', message.myflags['new_reply'])

        return message


################################## Run #########################################

processor = MyProcImap(mailbox)
processor.set_logfile(logfile)
run_as_singelton()
try:
    log("Running")
    processor.run()
except Exception, data:
    msgstring = "Exception occured: %s" % str(data)
    system( '/opt/kde3/bin/kdialog --title "ProcImap Exception" --error "%s" &' \
            % msgstring)
    log(msgstring)
    os.system("rm /home/goerz/Mail/backup.mbox.lock")
sys.exit(0)
#if something goes wrong, remove the try-except that hides the
#exception to see what's going on in detail

