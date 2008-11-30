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

""" This package contains a specialized OptionParser for use with ProcImap.

    All CLI tools developed from the ProcImap package should uniformly 
    provide an option '-p' / '--profile' to read a MailboxFactory profile

    Optionally, the filename for the profile is read from the
    PROC_IMAP_PROFILE environment variable.

    This allows the user to keep account information (passwords) in one
    place for a variety of tools.
"""

from ProcImap.Utils.MailboxFactory import MailboxFactory

from optparse import OptionParser, IndentedHelpFormatter
import os


class ProcImapOptParser(OptionParser):
    """ A special OptionParser for ProcImap. This takes the exact same
        arguments as optparse.OptionParser.

        However, there is a predefined option '-p' or '--profile'. If
        not given explicitely, this option takes the value of the
        environment variable PROC_IMAP_PROFILE. If the option is not
        given, neither explicitely nor implicitely through the envirnoment
        variable, ProcImapOptParser will shoot down the program it's
        running in with an error message.

        You can use ProcImapOptParser in this manner:

        >>> opt = ProcImapOptParser()
        >>> (options, args) = opt.parse_args(args=sys.argv)

        if sys.argv included e.g. '-p mailboxes.cfg', options.profile will
        NOT be the string 'mailboxes.cfg', but instead will be an instance 
        of MailboxFactory, generated from the file mailboxes.cfg.

        ProcImapOptParser also has a modified default formatter that 
        allows explicit linebreaks (for paragraphs) in help-generating
        arguments like 'epilogue'.
    """
    def __init__(self, **args):
        """ See documentation of optparse.OptionParser for arguments. """
        class MyIndentedHelpFormatter(IndentedHelpFormatter):
            """ Slightly modified formatter for help output: 
                allow paragraphs 
            """
            def format_paragraphs(self, text):
                """ wrap text per paragraph """
                result = ""
                for paragraph in text.split("\n"):
                    result += self._format_text(paragraph) + "\n"
                return result
            def format_description(self, description):
                """ format description, honoring paragraphs """
                if description:
                    return self.format_paragraphs(description) + "\n"
                else:
                    return ""
            def format_epilog(self, epilog):
                """ format epilog, honoring paragraphs """
                if epilog:
                    return "\n" + self.format_paragraphs(epilog) + "\n"
                else:
                    return ""
        OptionParser.__init__(self, **args)
        self.add_option("-p", "--profile", dest="profile",
                        help="Use FILE as the MailboxFactory config file "
                        "defining all the mailboxes for this program.", 
                        metavar="FILE")
        if not args.has_key('formatter'):
            self.formatter = MyIndentedHelpFormatter()
        if os.environ.has_key('PROC_IMAP_PROFILE'):
            self.set_defaults(profile=os.environ['PROC_IMAP_PROFILE'])

    def parse_args(self, args=None, values=None):
        """
        parse_args(args : [string] = sys.argv[1:],
                   values : Values = None)
        -> (values : Values, args : [string])

        Parse the command-line options found in 'args' (default:
        sys.argv[1:]).  Any errors result in a call to 'error()', which
        by default prints the usage message to stderr and calls
        sys.exit() with an error message.  On success returns a pair
        (values, args) where 'values' is an Values instance (with all
        your option values) and 'args' is the list of arguments left
        over after parsing options.
        """
        result = OptionParser.parse_args(self, args, values)
        if self.values.profile is None:
            self.exit(status=1, msg="You did not provide a profile, and the "
                      "PROC_IMAP_PROFILE environment variable is not set.\n")
        else:
            try:
                self.values.profile = MailboxFactory(self.values.profile)
            except:
                raise
        return result

