#!/usr/bin/env python

from distutils.core import setup

setup(name='ProcImap',
      version='1.1',
      description='Python IMAP Library and Mail Processing Utility',
      long_description ='The ProcImap package serves a double purpose. Originally, the idea was to have a framework that allows to write filters for an IMAP email account, similar to  what is done traditionally with the procimap utility on unix system. To realize this, a complete IMAP library was added, implementing ImapServer, ImapMailbox, and ImapMessage classes. These classes fit into the mailbox framework of the standard library.',
      author='Michael Goerz',
      author_email='goerz@physik.fu-berlin.de',
      url='http://code.google.com/p/procimap/',
      license='GPL',
      packages=['ProcImap']
     )
