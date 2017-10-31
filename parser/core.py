import re
import nltk.data

from parser.tag import FileTags
from parser.text_tree import TextTree, build_tree


TITLE = re.compile(r'^\ufeff?([\w ]+)[^.]?')
EXHIBIT = re.compile(r'^\ufeff?Exhibit.+$')
EMPTY_LINE = re.compile(r'^\s*$')
SECTION = re.compile(r'^[A-Z][A-z ]+[^.]?$')
LIST = re.compile(r'^\s*(\d+\.?\)?|\w+\.?\)|\(\w+\)|•).*$', re.VERBOSE)


# MAGIC METHOD
def tag_positions(text: str) -> tuple:
    """
    Generate list of tags positions and lines which match these tags.

    :param text: str, which will used for searching tags
    :return: tuple of lists
    """

    def same_types_of_list(first, second):
        f_type, s_type = '', ''

        if re.match(r'\d+\.?\)?', first):
            f_type = r'\d+\.?\)?'
        elif re.match(r'\w+\.?\)', first):
            f_type = r'\w+\.?\)'
        elif re.match(r'\(\w+\)', first):
            f_type = r'\(\w+\)'
        elif re.match(r'•', first):
            f_type = r'•'

        if re.match(r'\d+\.?\)?', second):
            s_type = r'\d+\.?\)?'
        elif re.match(r'\w+\.?\)', second):
            s_type = r'\w+\.?\)'
        elif re.match(r'\(\w+\)', second):
            s_type = r'\(\w+\)'
        elif re.match(r'•', second):
            s_type = r'•'

        return f_type == s_type and f_type != ''

    text_lines = text.splitlines()
    # first - type of tag, second - tag info
    flags = [('', '') for _ in text_lines]
    title_pos = 0

    # check that file has 'Exhibit' line
    if EXHIBIT.match(text_lines[title_pos]):
        title_pos += 1
        while EMPTY_LINE.match(text_lines[title_pos]):
            title_pos += 1
        flags[title_pos] = ('t', '')
        title_pos += 1
    # check that first line of file has title
    elif TITLE.match(text_lines[title_pos]):
        flags[title_pos] = ('t', '')
        title_pos += 1

    # try to search another tags after title position
    for i in range(title_pos, len(text_lines)):
        line = text_lines[i]
        # in case of empty line or line with whitespaces
        if len(line) == 0 or EMPTY_LINE.match(line):
            continue
        elif SECTION.match(line) and line.isupper():
            flags[i] = ('s', '')
        elif LIST.match(line):
            tmp = LIST.match(line).group(1)
            flags[i] = ('l', tmp)

    # remove mismatched sections inside of lists
    for i in range(1, len(flags) - 1):
        flag, item_type = flags[i]

        if flag == 's':
            # checking if marked 'i' as section between one list
            upper, lower = i - 1, i + 1
            while upper > 0:
                _, upper_type = flags[upper]
                while lower < len(flags):
                    _, lower_type = flags[lower]
                    if same_types_of_list(upper_type, lower_type):
                        flags[i] = ('', '')
                    lower += 1
                upper -= 1

    def prettify_tags(tags: list):
        """
        Generate list of tuples where each element has structure:
            (is opened tag on this line, is closed tag on this line, tag (Tag object))

        :param tags: list of preparsed tags.
        :return:
        """

        # list of tuples, which has structure like:
        # (is open tag (true - 1, false - 0), is closed tag (true - 1, false - 0), tag)
        pretty = [(0, 0, '') for _ in tags]
        i, tags_size = 0, len(tags)
        is_opened_section = False
        while i < tags_size:
            tag, modifier = tags[i]
            if tag == 't':
                pretty[i] = (1, 1, FileTags.TITLE)
            elif tag == 'l':
                pretty[i] = (1, 1, FileTags.LIST)
            elif tag == 's':
                if is_opened_section:
                    pretty[i - 1] = (0, 1, FileTags.SECTION)
                pretty[i] = (1, 0, FileTags.SECTION)
                is_opened_section = not is_opened_section
            # case not closed section
            if i + 1 == tags_size and not is_opened_section:
                pretty[i] = (0, 1, FileTags.SECTION)
            i += 1
        return pretty

    return prettify_tags(flags), text_lines


def tokenize_onto_sentences(text: str) -> list:
    """
    Split text (only english) to sentences using nltk.

    :param text: string
    :return: list of strings where each string is one sentence
    """
    # load english dictionary if need
    if not nltk.data.find('tokenizers/punkt/english.pickle'):
        nltk.download('punkt')
    tokenizer = nltk.data.load('tokenizers/punkt/english.pickle')
    # tokenize into sentences
    sentences = tokenizer.tokenize(text)
    return sentences


def generate_tree(text: str) -> TextTree:
    """
    Generate text tree with tags.

    :param text: string which need to be tagged
    :return: TextTree object
    """
    text_tags, lines = tag_positions(text)
    return build_tree(text_tags)


# MAGIC METHOD
def parse_raw_text(text: str) -> str:
    """
    Parse text and add tags to it.

    :param text: string which need to be tagged
    :return: str with tags
    """

    text_tags, lines = tag_positions(text)

    i, lines_size = 0, len(lines)
    while i < lines_size:
        is_opened, is_closed, tag = text_tags[i]
        if tag:
            if is_opened:
                lines[i] = tag.op() + '\n' + lines[i]
            if is_closed:
                lines[i] = lines[i] + '\n' + tag.cl()
        i += 1
    return '\n'.join(lines)