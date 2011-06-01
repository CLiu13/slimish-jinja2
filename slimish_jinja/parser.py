import sys, re
from tokens import *

class Parser(object):
    """
    Parses and translates slim syntax to jinja2 syntax.
    """
    def __init__(self, lexer, debug=False):
        self.__dict__.update(lexer=lexer, callback=sys.stdout.write, debug=debug,
                             indents=[], lookahead=None)
        self.it = lexer()

    def parse(self):
        """
        Entry point for parsing the template.
        The template consists of html and jinja tags.
        Grammar::
            doc -> doctype? (html_tag | jinja_tag)+
            text_tag -> {print}
            html_tag -> (HTML_NC_TAG {print}
                        |HTML_TAG {print}
                        |HTML_OPEN_TAG {print} INDENT (doc)* UNINDENT HTML_CLOSE_TAG {print}
                        )+
            jinja_tag -> (JINJA_NC_TAG {print}
                         |JINJA_TAG {print}
                         |jinja_open_tag {print} INDENT (doc)* UNINDENT jinja_close_tag {print}
                         )+
        """
        it = self.it
        try:
            self.lookahead = it.next()
            if isinstance(self.lookahead, DoctypeToken):
                self.callback(self.format_output(self.lookahead))
                self.match(self.lookahead)
            # Check for empty file.
            if self.lookahead:
                self.doc()
        except StopIteration, ex:
            pass

    def doc(self):
        """
        Jinja template non-terminal.
        Contains 0 or more html/jinja tags.
        Production::
            doc -> (html_tag | jinja_tag)*
        """
        while True:
            if isinstance(self.lookahead, HtmlToken):
                self.html_tag()
            elif isinstance(self.lookahead, JinjaToken):
                self.jinja_tag()
            elif isinstance(self.lookahead, TextToken) or isinstance(self.lookahead, JinjaOutputToken):
                self.output_tag(self.lookahead)
            else:
                return

    def html_tag(self):
        """
        Production::
            html_tag -> (HTML_NC_TAG {print}
                        |HTML_TAG {print}
                        |HTML_OPEN_TAG {print} INDENT (doc)* UNINDENT HTML_CLOSE_TAG {print}
                        )+
        """
        callback = self.callback
        while True:
            if self.lookahead.token_type in (HTML_TAG, HTML_NC_TAG):
                # No content tags are simple. Output them and
                # look for next token.
                callback(self.format_output(self.lookahead))
                self.match(self.lookahead)
            elif self.lookahead.token_type == HTML_TAG_OPEN:
                # Output the tag and save the corresponding closing tag.
                callback(self.format_output(self.lookahead))
                last_tag = self.lookahead
                last_tag.token_type = HTML_TAG_CLOSE
                self.match(self.lookahead)
                # Indent, more content, unindent.
                self.indent()
                self.doc()
                self.unindent()
                callback(self.format_output(last_tag))
            else:
                return

    def jinja_tag(self):
        """
        Production::
            jinja_tag -> (JINJA_NC_TAG {print}
                         |JINJA_TAG {print}
                         |jinja_open_tag {print} INDENT (doc)* UNINDENT jinja_close_tag {print}
                         )+
        """
        callback = self.callback
        while True:
            if self.lookahead.token_type in (JINJA_OUTPUT_TAG, JINJA_NC_TAG):
                # Output contents and look for next tag.
                callback(self.format_output(self.lookahead))
                self.match(self.lookahead)
            elif self.lookahead.token_type == JINJA_OPEN_TAG:
                # Output the tag and save the corresponding closing tag.
                callback(self.format_output(self.lookahead))
                last_tag = self.lookahead
                last_tag.token_type = JINJA_CLOSE_TAG
                self.match(self.lookahead)
                # Indent, more content, unindent.
                self.indent()
                self.doc()
                self.unindent()
                callback(self.format_output(last_tag))
            else:
                return

    def output_tag(self, lookahead):
        """
        Sends output to `self.callback` and reads next token.
        """
        self.callback(self.format_output(self.lookahead))
        self.match(self.lookahead)

    def indent(self):
        """
        Checks for indent. Verifies indent isn't a mix and match of tabs and
        spaces.
        """
        if self.lookahead.token_type != INDENT:
            raise SyntaxError("Parser error. Expected indent at line %d: %s" %
                              (self.lookahead.lineno, self.lookahead))
        else:
            spacer = self.lookahead.spacer
            if ' ' in spacer and '\t' in spacer:
                raise SyntaxError("Mixed tabs and spaces at line %d" % self.lookahead.lineno)
            self.indents.append(spacer)
            self.match(self.lookahead)

    def unindent(self):
        """
        Checks for unindent.
        """
        if self.lookahead.token_type != UNINDENT:
            raise SyntaxError("Parser error. Expected unindent %d" % self.lookahead.lineno)
        else:
            self.indents.pop()
            self.match(self.lookahead)

    def match(self, lookahead):
        # Check the current `lookahead` token and read the next
        # `lookahead`.
        if self.lookahead == lookahead:
            self.lookahead = self.it.next()
        else:
            raise SyntaxError("Parser error: expected %s at line %d" (self.lookahead, self.lookahead.lineno))

    def format_output(self, input):
        if self.debug:
            indent = self.indents and self.indents[-1] or ''
            return ('%s%s\n' % (indent, input))
        else:
            return ('%s' % input).strip()
