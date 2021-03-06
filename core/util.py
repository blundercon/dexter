'''
Various utility methods.
'''

import numpy
import re

from   dexter.core.log import LOG

# ------------------------------------------------------------------------------

class _WordsToNumbers():
    """
    A class that can translate strings of common English words that describe a
    number into the number described.

    From:
      http://code.activestate.com/recipes/550818-words-to-numbers-english/
    with some minor tweaking.
    """
    # a mapping of digits to their names when they appear in the
    # relative "ones" place (this list includes the 'teens' because
    # they are an odd case where numbers that might otherwise be called
    # 'ten one', 'ten two', etc. actually have their own names as single
    # digits do)
    __ones__ = { 'one':   1, 'eleven':     11,
                 'two':   2, 'twelve':     12,
                 'three': 3, 'thirteen':   13,
                 'four':  4, 'fourteen':   14,
                 'five':  5, 'fifteen':    15,
                 'six':   6, 'sixteen':    16,
                 'seven': 7, 'seventeen':  17,
                 'eight': 8, 'eighteen':   18,
                 'nine':  9, 'nineteen':   19 }

    # a mapping of digits to their names when they appear in the 'tens'
    # place within a number group
    __tens__ = { 'ten':     10,
                 'twenty':  20,
                 'thirty':  30,
                 'forty':   40,
                 'fifty':   50,
                 'sixty':   60,
                 'seventy': 70,
                 'eighty':  80,
                 'ninety':  90 }

    # an ordered list of the names assigned to number groups
    __groups__ = { 'thousand':    1000,
                   'million':     1000000,
                   'billion':     1000000000,
                   'trillion':    1000000000000,
                   'brazillion':  2**63 }

    # a regular expression that looks for number group names and captures:
    #     1-the string that preceeds the group name, and
    #     2-the group name (or an empty string if the
    #       captured value is simply the end of the string
    #       indicating the 'ones' group, which is typically
    #       not expressed)
    __groups_re__ = re.compile(
        r'\s?([\w\s]+?)(?:\s((?:%s))|$)' %
        ('|'.join(__groups__))
    )

    # a regular expression that looks within a single number group for
    # 'n hundred' and captures:
    #    1-the string that preceeds the 'hundred', and
    #    2-the string that follows the 'hundred' which can
    #      be considered to be the number indicating the
    #      group's tens- and ones-place value
    __hundreds_re__ = re.compile(r'([\w\s]+)\shundred(?:\s(.*)|$)')

    # a regular expression that looks within a single number
    # group that has already had its 'hundreds' value extracted
    # for a 'tens ones' pattern (ie. 'forty two') and captures:
    #    1-the tens
    #    2-the ones
    __tens_and_ones_re__ =  re.compile(
        r'((?:%s))(?:\s(.*)|$)' %
        ('|'.join(__tens__.keys()))
    )

    def parse(self, words):
        """
        Parses words to the number they describe.
        """
        # to avoid case mismatch, everything is reduced to the lower
        # case
        words = words.lower()
        # create a list to hold the number groups as we find them within
        # the word string
        groups = {}
        # create the variable to hold the number that shall eventually
        # return to the caller
        num = None
        # using the 'groups' expression, find all of the number group
        # an loop through them
        for group in _WordsToNumbers.__groups_re__.findall(words):
            ## determine the position of this number group
            ## within the entire number
            # assume that the group index is the first/ones group
            # until it is determined that it's a higher group
            group_multiplier = 1
            if group[1] in _WordsToNumbers.__groups__:
                group_multiplier = _WordsToNumbers.__groups__[group[1]]
            ## determine the value of this number group
            # create the variable to hold this number group's value
            group_num = 0
            # get the hundreds for this group
            hundreds_match = _WordsToNumbers.__hundreds_re__.match(group[0])
            # and create a variable to hold what's left when the
            # "hundreds" are removed (ie. the tens- and ones-place values)
            tens_and_ones = None
            # if there is a string in this group matching the 'n hundred'
            # pattern
            if hundreds_match is not None and hundreds_match.group(1) is not None:
                # multiply the 'n' value by 100 and increment this group's
                # running tally
                group_num = group_num + \
                            (_WordsToNumbers.__ones__[hundreds_match.group(1)] * 100)
                # the tens- and ones-place value is whatever is left
                tens_and_ones = hundreds_match.group(2)
            else:
                # if there was no string matching the 'n hundred' pattern,
                # assume that the entire string contains only tens- and ones-
                # place values
                tens_and_ones = group[0]

            # if the 'tens and ones' string is empty, it is time to
            # move along to the next group
            if tens_and_ones is None:
                # increment the total number by the current group number, times
                # its multiplier
                if num is None:
                    num = 0
                num = num + (group_num * group_multiplier)
                continue
            # look for the tens and ones ('tn1' to shorten the code a bit)
            tn1_match = _WordsToNumbers.__tens_and_ones_re__.match(tens_and_ones)
            # if the pattern is matched, there is a 'tens' place value
            if tn1_match is not None:
                # add the tens
                group_num = group_num + _WordsToNumbers.__tens__[tn1_match.group(1)]
                # add the ones
                if tn1_match.group(2) is not None:
                    group_num = group_num + _WordsToNumbers.__ones__[tn1_match.group(2)]
            else:
                # assume that the 'tens and ones' actually contained only the ones-
                # place values
                group_num = group_num + _WordsToNumbers.__ones__[tens_and_ones]
            # increment the total number by the current group number, times
            # its multiplier
            if num is None:
                num = 0
            num = num + (group_num * group_multiplier)
        # the loop is complete, return the result
        return num

# ------------------------------------------------------------------------------

_WORDS_TO_NUMBERS = _WordsToNumbers()

_LOWER   = ''.join(chr(i) for i in range(ord('a'), ord('z') + 1))
_UPPER   = _LOWER.upper()
_NUMBERS = ''.join(str(i) for i in range(0, 10))

# ------------------------------------------------------------------------------

def _strip_to(string, alphabet):
    '''
    Remove non-alphabet contents from a word.

    @type   string: str
    @parses string:
       The string to strip the chars from.

    @rtype: str
    @return:
        The stripped string.
    '''
    return ''.join(char
                   for char in string
                   if  char in alphabet)


def to_letters(string):
    '''
    Remove non-letters from a string.

    >>> to_letters('1a2b3c4d')
    'abcd'
    >>> to_letters(' a b c d ')
    'abcd'

    @type   string: str
    @parses string:
       The string to strip the chars from.

    @rtype: str
    @return:
        The stripped string.
    '''
    return _strip_to(string, _UPPER + _LOWER)


def to_alphanumeric(string):
    '''
    Remove non-letters and non-numbers from a string.

    >>> to_alphanumeric(' 1a2b3c4d ')
    '1a2b3c4d'
    >>> to_alphanumeric(' a b c d ')
    'abcd'

    @type   string: str
    @parses string:
       The string to strip the chars from.

    @rtype: str
    @return:
        The stripped string.
    '''
    return _strip_to(string, _UPPER + _LOWER + _NUMBERS)


def parse_number(words):
    '''
    Turn a set of words into a number. These might be complex ("One thousand
    four hundred and eleven") or simple ("Seven").

    >>> parse_number('one')
    1
    >>> parse_number('one point eight')
    1.8
    >>> parse_number('minus six')
    -6
    >>> parse_number('minus four point seven eight nine')
    -4.789

    @type  words: str
    @parse words:
        The string words to parse. E.g. C{'twenty seven'}.
    '''
    # Sanity
    if words is None:
        return None

    # Make sure it's a string
    words = str(words)

    # Trim surrounding whitespace
    words = words.strip()

    # Not a lot we can do if we have no words
    if len(words) == 0:
        return None

    # First try to parse the string as an integer or a float directly
    if not re.search(r'\s', words):
        try:
            return int(words)
        except:
            pass
        try:
            return float(words)
        except:
            pass

    # Sanitise it since we're now going to attempt to parse it. Collapse
    # multiple spaces to one and strip out non-letters
    words = ' '.join(to_letters(s) for s in re.split(r'\s+', words))
    LOG.debug("Parsing '%s'" % (words,))

    # Recheck for empty
    if words == '':
        return None


    # See if we have to negate the result
    mult = 1
    for neg in ("minus ", "negative "):
        if words.startswith(neg):
            words = words[len(neg):]
            mult = -1
            break

    # Look for "point" in the words since it might be "six point two" or
    # something
    if ' point ' in words:
        # Determine the integer and decimal portions
        (integer, decimal) = words.split(' point ', 1)
        LOG.debug("'%s' becomes '%s' and '%s'" %
                  (words, integer, decimal))

        # Parsing the whole number is easy enough
        whole = parse_number(integer)
        if whole is None:
            return None

        # S;plit up the digits to parse them.
        digits = numpy.array([parse_number(digit)
                              for digit in decimal.split(' ')])
        if None in digits        or \
           numpy.any(digits < 0) or \
           numpy.any(digits > 9):
            LOG.error("'%s' was not a valid decimal" % (words,))
            return None

        # Okay, use some cheese to parse into a float
        return mult * float('%d.%s' % (whole, ''.join(str(d) for d in digits)))

    else:
        # No ' point ' in it, parse directly
        try:
            return mult * _WORDS_TO_NUMBERS.parse(words)
        except Exception as e:
            LOG.error("Failed to parse '%s': %s" % (words, e))
            return None


def number_to_words(value):
    '''
    Turn a number into words.

    >>> number_to_words(1)
    'one'
    >>> number_to_words(1.8)
    'one point eight'
    >>> number_to_words(-6)
    'minus six'
    >>> number_to_words(-4.789)
    'minus four point seven eight nine'
    >>> number_to_words(42.01234)
    'forty two point zero one two three four'
    >>> number_to_words(30)
    'thirty'
    >>> number_to_words(1000000)
    'one million'

    @type  value: number
    @parse value:
        The value to convert to words.
    '''
    # First handle the integer part
    if value < 0:
        result = 'minus '
        value = -value
    else:
        result = ''

    int_value   = int(value)
    float_value = float(value)

    remainder = 0
    if int_value >= 1000000000:
        billions = int_value // 1000000000
        result += number_to_words(billions) + " billion"
        remainder = int_value - billions * 1000000000
    elif int_value >= 1000000:
        millions = int_value // 1000000
        result += number_to_words(millions) + " million"
        remainder = int_value - millions * 1000000
    elif int_value >= 1000:
        thousands = int_value // 1000
        result += number_to_words(thousands) + " thousand"
        remainder = int_value - thousands * 1000
    elif int_value >= 100:
        hundreds = int_value // 100
        result += number_to_words(hundreds) + " thousand"
        remainder = int_value - hundreds * 100
    elif int_value >= 90:
        result += "ninety"
        remainder = int_value - 90
    elif int_value >= 80:
        result += "eighty"
        remainder = int_value - 80
    elif int_value >= 70:
        result += "seventy"
        remainder = int_value - 70
    elif int_value >= 60:
        result += "sixty"
        remainder = int_value - 60
    elif int_value >= 50:
        result += "fifty "
        remainder = int_value - 50
    elif int_value >= 40:
        result += "forty"
        remainder = int_value - 40
    elif int_value >= 30:
        result += "thirty"
        remainder = int_value - 30
    elif int_value >= 20:
        result += "twenty"
        remainder = int_value - 20
    elif int_value == 19:
        result += "nineteen"
    elif int_value == 18:
        result += "eighteen"
    elif int_value == 17:
        result += "seventeen"
    elif int_value == 16:
        result += "sixteen"
    elif int_value == 15:
        result += "fifteen"
    elif int_value == 14:
        result += "fourteen"
    elif int_value == 13:
        result += "thirteen"
    elif int_value == 12:
        result += "twelve"
    elif int_value == 11:
        result += "eleven"
    elif int_value == 10:
        result += "ten"
    elif int_value == 9:
        result += "nine"
    elif int_value == 8:
        result += "eight"
    elif int_value == 7:
        result += "seven"
    elif int_value == 6:
        result += "six"
    elif int_value == 5:
        result += "five"
    elif int_value == 4:
        result += "four"
    elif int_value == 3:
        result += "three"
    elif int_value == 2:
        result += "two"
    elif int_value == 1:
        result += "one"
    elif int_value == 0:
        result += "zero"

    # Any more?
    if remainder > 0:
        result += " " + number_to_words(remainder)

    # Now any decimal
    if int_value != float_value:
        # We're appending a decimal
        result += " point"

        # General significant figures of a double
        for i in range(1, 16):
            shifted = float_value * pow(10.0, i)
            result += ' %s' % number_to_words(int(shifted) % 10)
            if abs(shifted - int(shifted)) < 1e-10:
                break

    # And we're done!
    return result


def list_index(list_, sublist, start=0):
    '''
    Find the index of of a sublist in a list.

    >>> list_index(range(10), range(3, 5))
    3
    >>> list_index('hello', 'he')
    0
    >>> list_index('hello', 'l')
    2
    >>> list_index('hello', 'el')
    1
    >>> list_index('hello', 'lo')
    3
    >>> list_index('what is a fish'.split(' '), 'a fish'.split(' '))
    2
    >>> list_index(['what', 'is', 'a', 'fish'], ('what', 'is'))
    0

    @type  list_: list
    @param list_:
        The list to look in.
    @type  sublist: list
    @param sublist:
        The list to look for.
    @type  start: int
    @param start:
        Where to start looking in the C{list}.
    '''
    # Make sure these are lists
    if list_ is None:
        raise ValueError("list was None")
    if sublist is None:
        raise ValueError("sublist was None")
    if not isinstance(list_, tuple):
        list_ = tuple(list_)
    if not isinstance(sublist, tuple):
        sublist = tuple(sublist)

    # The empty list can't be in anything
    if len(sublist) == 0:
        raise ValueError("Empty sublist not in list")

    # Simple case
    if len(sublist) == 1:
        return list_.index(sublist[0], start)

    # Okay, we have multiple elements in our sublist. Look for the first
    # one, and see that it's adjacent to the rest of the list. We
    offset = start
    while True:
        try:
            first = list_index(list_, sublist[ :1], offset)
            rest  = list_index(list_, sublist[1: ], first + 1)
            if first + 1 == rest:
                return first

        except ValueError:
            raise ValueError('%s not in %s' % (sublist, list_))

        # Move the offset to be after the first instance of sublist[0], so
        # that we may find the next one, if any
        offset = first + 1
