#!/usr/bin/env python
"""
Backup all the mails in a gmail account to a local mbox
"""
import sys

from ProcImap.Utils.CLI import ProcImapOptParser
from ProcImap.Utils.Gmail import GmailCache

usage = "usage: %prog [options] SOURCE CACHE TARGET"
opt = ProcImapOptParser(usage=usage)
opt.description = """SOURCE is the name of a gmail-mailbox in the config file
CACHE is the filename of a stored cache for the gmail account SOURCE is on.
TARGET is the filename of the mbox file that is to be used as the backup 
target.

%prog  makes a full backup of the gmail account that 
SOURCE is on, using the information found in CACHE, and putting the backup
in the local mbox file found at TARGET.

The backup is incremental: emails already in the TARGET mbox will not be
added again, but emails that were deleted from the server will not be
deleted from the mbox."""

opt.add_option('--silent', dest='silent', action='store_true', 
               help="Don't print any status messages.")
opt.add_option('--skip-update', dest='skip_update', action='store_true', 
               help="Don't update the CACHE before doing the backup.")
(options, args) = opt.parse_args(args=sys.argv)

if len(args) != 4:
    opt.error("incorrect number of arguments")

source = args.pop(1)
cachefile = args.pop(1)
target = args.pop(1)

cache = GmailCache(options.profile.get_server(source))
cache.load(cachefile)
cache.autosave = cachefile
update = True
if options.skip_update:
    update = False
try:
    uids = cache.backup(target, update=update, silent=options.silent)
    if uids is not None:
        if len(uids) > 0:
            print "The following UIDs were not backed up:"
            for uid in uids:
                print uid
except Exception, data:
    print "Exception: %s" % data

sys.exit(0)
