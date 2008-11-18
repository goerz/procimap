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

""" This module contains general functions for processing mail locally
    e.g. for filtering and classification.
"""

import re
import subprocess
import tempfile
import os
from email.generator import Generator
from cStringIO import StringIO

from ProcImap.ImapMessage import ImapMessage

class AddressListFile:
    """ This class wraps around a file containing emailadresses.
        It is intended to help with Whitelisting, Blacklisting, etc.
    """
    def __init__(self, filename, inmemory=False, regexes=False):
        """ Initialize AddressListFile:
            If inmemory is True, the file is loaded into memory.
            If regexes is True, the lines in the file are compiled
            as regexes.
        """
        self._cache = {}
        self._data = []
        self.filename = filename
        self._inmemory = inmemory
        self._use_regexes = regexes
        if self._inmemory:
            if self._use_regexes:
                infile = open(filename)
                for line in infile:
                    self._data.append(re.compile(line.strip()))
                infile.close()
            else:
                infile = open(filename)
                self._data = infile.read().split("\n")
                self._data = [x for x in self._data if x != '']
                infile.close()
    def contains(self, lookupstring):
        """ Return True if there is a line in the represented file that is
            contained in lookupstring. E.g., if you search for
            'someone@gmail.com' and the file contains a line '@gmail.com',
            True is returned.
            If regexes are used, return True if there is a regex in the file
            that matches the lookupstring completely.
        """
        if lookupstring is None:
            return False
        if self._cache.has_key(lookupstring):
            return self._cache[lookupstring]
        if self._use_regexes:
            if self._inmemory:
                for regex in self._data:
                    if regex.match(lookupstring):
                        self._cache[lookupstring] = True
                        return True
            else:
                infile = open(self.filename)
                for line in infile:
                    regex = re.compile(line.strip())
                    if regex.match(lookupstring):
                        self._cache[lookupstring] = True
                        return True
                infile.close()
        else:
            if self._inmemory:
                for in_file_string in self._data:
                    if in_file_string in lookupstring:
                        self._cache[lookupstring] = True
                        return True
            else:
                infile = open(self.filename)
                for line in infile:
                    line = line.strip()
                    if line in lookupstring:
                        self._cache[lookupstring] = True
                        return True
                infile.close()
        self._cache[lookupstring] = False
        return False
    def add(self, line):
        """ Add line to self.filename  """
        outfile = open(self.filename, "a")
        outfile.write(line)
        if not line[-1] == "\n":
            outfile.write("\n")
        outfile.close()



class ReplacementListFile:
    """ This class wraps around a file containing email address
        replacements.
        The text file contains lines such as
        noreply@couchsurfing.com :: Couchsurfing <noreply@couchsurfing.com>
        The intention is to to replace 'noreply@couchsurfing.com'
        with 'Couchsurfing <noreply@couchsurfing.com>'.
        You can use this to make the from-line look nice in your email
        reader, if people send you crippled from-lines.
    """
    def __init__(self, filename, inmemory=False, regexes=False, partial=False):
        self._cache = {}
        self._data = None
        if regexes:
            self._data = []
        else:
            self._data = {} # dicts will only work for non-regexes
        self.filename = filename
        self._inmemory = inmemory
        self._use_regexes = regexes
        self._partial = partial
        if self._inmemory:
            if self._use_regexes:
                infile = open(filename)
                for line in infile:
                    (original, replacement) = line.split("::", 1)
                    original = re.compile(original.strip())
                    replacement = replacement.strip()
                    self._data.append((original, replacement))
                infile.close()
            else:
                infile = open(filename)
                for line in infile:
                    (original, replacement) = line.split("::", 1)
                    original = original.strip()
                    replacement = replacement.strip()
                    self._data[original] = replacement
                infile.close()
    def lookup(self, searchstring):
        """ Return a replacement. If no replacement is found, return
            the searchstring.
        """
        if searchstring is None:
            return None
        if self._cache.has_key(searchstring):
            return self._cache[searchstring]
        if self._use_regexes:
            if self._inmemory:
                for (regex, replacement) in self._data:
                    if regex.match(searchstring):
                        self._cache[searchstring] = replacement
                        return replacement
            else:
                infile = open(self.filename)
                for line in infile:
                    (original, replacement) = line.split("::", 1)
                    original = re.compile(original.strip())
                    replacement = replacement.strip()
                    regex = re.compile(line[:-1])
                    if regex.match(searchstring):
                        self._cache[searchstring] = replacement
                        return replacement
                infile.close()
        else:
            if self._inmemory:
                if self._data.has_key(searchstring):
                    replacement = self._data[searchstring]
                    self._cache[searchstring] = replacement
                    return replacement
                else:
                    if self._partial:
                        for (original, replacement) in self._data.items():
                            if  original in searchstring:
                                self._cache[searchstring] = replacement
                                return replacement
                    else:
                        return searchstring
            else:
                infile = open(self.filename)
                for line in infile:
                    (original, replacement) = line.split("::", 1)
                    original = original.strip()
                    replacement = replacement.strip()
                    if  original in searchstring:
                        self._cache[searchstring] = replacement
                        return replacement
                infile.close()
        self._cache[searchstring] = searchstring
        return searchstring
    def add(self, line):
        """ Add line to self.filename  """
        outfile = open(self.filename, "a")
        outfile.write(line)
        if not line[-1] == "\n":
            outfile.write("\n")
        outfile.close()



def pipe_message(message, command):
    """ Pipe the message through a shell command:
        cat message | commmand > message
        message is assumed to be an instance of ImapMessage
        Returns modified message as instance of ImapMessage
    """
    p = subprocess.Popen([command], shell=True,
            stdin=subprocess.PIPE, stdout=subprocess.PIPE, close_fds=True)
    (child_stdout, child_stdin) = (p.stdout, p.stdin)

    memoryfile = StringIO()
    generator = Generator(memoryfile, mangle_from_=False, maxheaderlen=60)
    generator.flatten(message)
    child_stdin.write(memoryfile.getvalue())
    child_stdin.close()
    modified_message = ImapMessage(child_stdout)
    child_stdout.close()
    modified_message.set_imapflags(message.get_imapflags())
    modified_message.internaldate = message.internaldate
    if hasattr(message, 'myflags'):
        modified_message.myflags = message.myflags
    if hasattr(message, 'mailbox'):
        modified_message.mailbox = message.mailbox
    return modified_message

def unknown_to_ascii(inputstring):
    """ This takes a string or unicode string in unknown encoding, tries to
        guess the encoding and to replace Latin-1 characters with something
        equivalent in 7-bit ASCII. Decoding an unknown string is based on
        heuristics. This function may return complete garbage.
        The function returns a plain ASCII string, making a best effort to
        convert Latin-1 characters into ASCII equivalents. It does not just
        strip out the Latin-1 characters. All characters in the standard 7-bit
        ASCII range are preserved. In the 8th bit range all the Latin-1
        accented letters are converted to unaccented equivalents. Most symbol
        characters are converted to something meaningful. Anything not
        converted is deleted.

        Adapted from
        http://aspn.activestate.com/ASPN/Cookbook/Python/Recipe/251871
    """
    xlate = {
    # unicode string                                  : (replacement, weight)
    u'\N{ACUTE ACCENT}'                               : ( "", 0),
    u'\N{BROKEN BAR}'                                 : ( '|', 0),
    u'\N{CEDILLA}'                                    : ( '', 0),
    u'\N{CENT SIGN}'                                  : ( ' cent', 0),
    u'\N{COPYRIGHT SIGN}'                             : ( '(c)', 1),
    u'\N{CURRENCY SIGN}'                              : ( '', 0),
    u'\N{DEGREE SIGN}'                                : ( '', 1),
    u'\N{DIAERESIS}'                                  : ( '', 0),
    u'\N{DIVISION SIGN}'                              : ( '/', 1),
    u'\N{FEMININE ORDINAL INDICATOR}'                 : ( '', 0),
    u'\N{INVERTED EXCLAMATION MARK}'                  : ( '!', 1),
    u'\N{INVERTED QUESTION MARK}'                     : ( '?', 1),
    u'\N{LATIN CAPITAL LETTER A WITH ACUTE}'          : ( 'A', 1),
    u'\N{LATIN CAPITAL LETTER A WITH CIRCUMFLEX}'     : ( 'A', 1),
    u'\N{LATIN CAPITAL LETTER A WITH DIAERESIS}'      : ( 'Ae', 1),
    u'\N{LATIN CAPITAL LETTER A WITH GRAVE}'          : ( 'A', 1),
    u'\N{LATIN CAPITAL LETTER A WITH RING ABOVE}'     : ( 'A', 1),
    u'\N{LATIN CAPITAL LETTER A WITH TILDE}'          : ( 'A', 1),
    u'\N{LATIN CAPITAL LETTER AE}'                    : ( 'Ae', 2),
    u'\N{LATIN CAPITAL LETTER C WITH CEDILLA}'        : ( 'C', 1),
    u'\N{LATIN CAPITAL LETTER E WITH ACUTE}'          : ( 'E', 1),
    u'\N{LATIN CAPITAL LETTER E WITH CIRCUMFLEX}'     : ( 'E', 1),
    u'\N{LATIN CAPITAL LETTER E WITH DIAERESIS}'      : ( 'E', 1),
    u'\N{LATIN CAPITAL LETTER E WITH GRAVE}'          : ( 'E', 1),
    u'\N{LATIN CAPITAL LETTER ETH}'                   : ( 'Th', 1),
    u'\N{LATIN CAPITAL LETTER I WITH ACUTE}'          : ( 'I', 1),
    u'\N{LATIN CAPITAL LETTER I WITH CIRCUMFLEX}'     : ( 'I', 1),
    u'\N{LATIN CAPITAL LETTER I WITH DIAERESIS}'      : ( 'I', 1),
    u'\N{LATIN CAPITAL LETTER I WITH GRAVE}'          : ( 'I', 1),
    u'\N{LATIN CAPITAL LETTER N WITH TILDE}'          : ( 'N', 1),
    u'\N{LATIN CAPITAL LETTER O WITH ACUTE}'          : ( 'O', 1),
    u'\N{LATIN CAPITAL LETTER O WITH CIRCUMFLEX}'     : ( 'O', 1),
    u'\N{LATIN CAPITAL LETTER O WITH DIAERESIS}'      : ( 'Oe', 2),
    u'\N{LATIN CAPITAL LETTER O WITH GRAVE}'          : ( 'O', 1),
    u'\N{LATIN CAPITAL LETTER O WITH STROKE}'         : ( 'O', 1),
    u'\N{LATIN CAPITAL LETTER O WITH TILDE}'          : ( 'O', 1),
    u'\N{LATIN CAPITAL LETTER THORN}'                 : ( 'th', 1),
    u'\N{LATIN CAPITAL LETTER U WITH ACUTE}'          : ( 'U', 1),
    u'\N{LATIN CAPITAL LETTER U WITH CIRCUMFLEX}'     : ( 'U', 1),
    u'\N{LATIN CAPITAL LETTER U WITH DIAERESIS}'      : ( 'Ue', 2),
    u'\N{LATIN CAPITAL LETTER U WITH GRAVE}'          : ( 'U', 1),
    u'\N{LATIN CAPITAL LETTER Y WITH ACUTE}'          : ( 'Y', 1),
    u'\N{LATIN SMALL LETTER A WITH ACUTE}'            : ( 'a', 1),
    u'\N{LATIN SMALL LETTER A WITH CIRCUMFLEX}'       : ( 'a', 1),
    u'\N{LATIN SMALL LETTER A WITH DIAERESIS}'        : ( 'ae', 2),
    u'\N{LATIN SMALL LETTER A WITH GRAVE}'            : ( 'a', 1),
    u'\N{LATIN SMALL LETTER A WITH RING ABOVE}'       : ( 'a', 1),
    u'\N{LATIN SMALL LETTER A WITH TILDE}'            : ( 'a', 1),
    u'\N{LATIN SMALL LETTER AE}'                      : ( 'ae', 3),
    u'\N{LATIN SMALL LETTER C WITH CEDILLA}'          : ( 'c', 1),
    u'\N{LATIN SMALL LETTER E WITH ACUTE}'            : ( 'e', 1),
    u'\N{LATIN SMALL LETTER E WITH CIRCUMFLEX}'       : ( 'e', 1),
    u'\N{LATIN SMALL LETTER E WITH DIAERESIS}'        : ( 'e', 1),
    u'\N{LATIN SMALL LETTER E WITH GRAVE}'            : ( 'e', 1),
    u'\N{LATIN SMALL LETTER ETH}'                     : ( 'th', 1),
    u'\N{LATIN SMALL LETTER I WITH ACUTE}'            : ( 'i', 1),
    u'\N{LATIN SMALL LETTER I WITH CIRCUMFLEX}'       : ( 'i', 1),
    u'\N{LATIN SMALL LETTER I WITH DIAERESIS}'        : ( 'i', 1),
    u'\N{LATIN SMALL LETTER I WITH GRAVE}'            : ( 'i', 1),
    u'\N{LATIN SMALL LETTER N WITH TILDE}'            : ( 'n', 1),
    u'\N{LATIN SMALL LETTER O WITH ACUTE}'            : ( 'o', 1),
    u'\N{LATIN SMALL LETTER O WITH CIRCUMFLEX}'       : ( 'o', 1),
    u'\N{LATIN SMALL LETTER O WITH DIAERESIS}'        : ( 'oe', 2),
    u'\N{LATIN SMALL LETTER O WITH GRAVE}'            : ( 'o', 1),
    u'\N{LATIN SMALL LETTER O WITH STROKE}'           : ( 'o', 1),
    u'\N{LATIN SMALL LETTER O WITH TILDE}'            : ( 'o', 1),
    u'\N{LATIN SMALL LETTER SHARP S}'                 : ( 'ss', 2),
    u'\N{LATIN SMALL LETTER THORN}'                   : ( 'th', 0),
    u'\N{LATIN SMALL LETTER U WITH ACUTE}'            : ( 'u', 1),
    u'\N{LATIN SMALL LETTER U WITH CIRCUMFLEX}'       : ( 'u', 1),
    u'\N{LATIN SMALL LETTER U WITH DIAERESIS}'        : ( 'ue', 2),
    u'\N{LATIN SMALL LETTER U WITH GRAVE}'            : ( 'u', 1),
    u'\N{LATIN SMALL LETTER Y WITH ACUTE}'            : ( 'y', 1),
    u'\N{LATIN SMALL LETTER Y WITH DIAERESIS}'        : ( 'y', 1),
    u'\N{LEFT-POINTING DOUBLE ANGLE QUOTATION MARK}'  : ( '"', 0),
    u'\N{MACRON}'                                     : ( '', 0),
    u'\N{MASCULINE ORDINAL INDICATOR}'                : ( '', 0),
    u'\N{MICRO SIGN}'                                 : ( 'micro', 0),
    u'\N{MIDDLE DOT}'                                 : ( '*', 0),
    u'\N{MULTIPLICATION SIGN}'                        : ( '*', 0),
    u'\N{NOT SIGN}'                                   : ( 'not', 0),
    u'\N{PILCROW SIGN}'                               : ( '', 0),
    u'\N{PLUS-MINUS SIGN}'                            : ( '+/-', 0),
    u'\N{POUND SIGN}'                                 : ( ' pound', 0),
    u'\N{REGISTERED SIGN}'                            : ( '(R)', 0),
    u'\N{RIGHT-POINTING DOUBLE ANGLE QUOTATION MARK}' : ( '"', 0),
    u'\N{SECTION SIGN}'                               : ( '', 0),
    u'\N{SOFT HYPHEN}'                                : ( '-', 0),
    u'\N{SUPERSCRIPT ONE}'                            : ( '1', 0),
    u'\N{SUPERSCRIPT THREE}'                          : ( '3', 0),
    u'\N{SUPERSCRIPT TWO}'                            : ( '2', 0),
    u'\N{VULGAR FRACTION ONE HALF}'                   : ( '{1/2}', 0),
    u'\N{VULGAR FRACTION ONE QUARTER}'                : ( '{1/4}', 0),
    u'\N{VULGAR FRACTION THREE QUARTERS}'             : ( '{3/4}', 0),
    u'\N{YEN SIGN}'                                   : ('yen', 0)
    }
    try:
        unistring = unicode(inputstring, 'ascii')
        return inputstring # inputstring is ascii, nothing to do
    except UnicodeDecodeError:
        pass
    if isinstance(inputstring, unicode):
        unistring = inputstring
    else:
        # try to make string into unicode
        encodings = ['utf8', 'latin_1', 'cp037', 'cp437' , 'cp850', 'cp852',
                     'cp863', 'cp865', 'cp1140', 'cp1250', 'cp1252',
                     'iso8859_15', 'mac_latin2', 'utf_16']
        found_encoding = 'ascii'
        alphabet = u"abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ :!,"
        max_score = 0.0
        for encoding in encodings:
            # the encoding that reaches the highest score in the translation of
            # characters is assumed correct. The score is a weighted count of
            # successful translations, divided by the number of total characters
            try:
                unistring = unicode(inputstring, encoding)
                successcount = 0
                totalcount = 0
                for character in unistring:
                    totalcount += 1
                    if xlate.has_key(character):
                        # translated characters contribute with their defined
                        # weight
                        weight = xlate[character][1]
                        successcount += weight
                    if character in alphabet:
                        # characters that are in the standard alphabet are good
                        # They contribute with a weight of 2
                        successcount += 2
                score = float(successcount) / float(totalcount)
                if score > max_score:
                    # always take the encoding with the highest score
                    found_encoding = encoding
                    max_score = score
            except UnicodeDecodeError:
                # this encoding doesn't work. Try the next one.
                continue
            unistring = unicode(inputstring, found_encoding, 'replace')
    result = ''
    for character in unistring:
        if xlate.has_key(character):
            result += xlate[character][0]
        elif ord(character) >= 0x80:
            pass
        else:
            result += str(character)
    return result

def put_through_pager(displaystring, pager='less'):
    """ Put displaystring through the 'less' pager """
    (temp_fd, tempname) = tempfile.mkstemp(".mail")
    temp_fh = os.fdopen(temp_fd, "w")
    temp_fh.write(displaystring)
    temp_fh.close()
    os.system("%s %s" % (pager, tempname))
    os.unlink(tempname)

def references_from_header(header):
    """ Extract the message ids from the "References" and "In-Reply-To" 
        Headers.
    """
    id_pattern = re.compile('<\S+@\S+>')
    result = set()
    references = header['References']
    if references is not None:
        for id in id_pattern.findall(references):
            result.add(id)
    reply_to = header['In-Reply-To']
    if reply_to is not None:
        for id in id_pattern.findall(reply_to):
            result.add(id)
    return list(result)
