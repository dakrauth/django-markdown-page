#!/usr/bin/env python
"""
    Patch utility to apply unified diffs

    Brute-force line-by-line non-recursive parsing 

    Copyright (c) 2008-2016 anatoly techtonik
    Available under the terms of MIT license

"""
__author__ = "anatoly techtonik <techtonik@gmail.com>"
__version__ = "2.0"
__license__ = "MIT"
__url__ = "https://github.com/techtonik/python-patch"
__maintainer__ = "david krauth <dakrauth@gmail.com>"

import re
import sys
import copy
import logging
import difflib
from pathlib import Path as _BasePath
from io import StringIO
from itertools import count
from datetime import datetime, timezone

logger = logging.getLogger(__name__)


class Path(_BasePath):

    def mod_time(self):
        return datetime.fromtimestamp(
           self.stat().st_mtime,
           timezone.utc
        ).astimezone().isoformat()


class NoMatch(Exception):
    pass


class Counter:
    _counter = count()

    def __init__(self):
        self.counter = next(self.__class__._counter)


class Hunk(Counter):
    """ Parsed hunk data container (hunk starts with @@ -R +R @@) """

    def __init__(self, **kwargs):
        super().__init__()
        self.start_src = None #: line count starts with 1
        self.start_tgt = None
        self.invalid = False

        self.lines_src = 1
        self.lines_tgt = 1

        self.desc = ''
        self.text = []
        self.__dict__.update(kwargs)

    def __str__(self):
        return f'<Hunk {self.counter}>'


class Patch(Counter):
    """ Patch for a single file. If used as an iterable, returns hunks."""

    PLAIN = "plain"
    GIT = "git"

    def __init__(self, source, target, header):
        super().__init__()
        self.source = source
        self.target = target
        self.header = header
        self.hunks = []
        self.type = None

    def __len__(self):
        return len(self.hunks)

    def __str__(self):
        return f'<Patch {self.counter}:{self.source}>'

    def __iter__(self):
        for h in self.hunks:
            yield h

    def add(self, hunk):
        hunk.index = len(self)
        hunk.patch = self
        self.hunks.append(hunk)

    def set_type(self, type):
        self.type = type
        return type

    def detect_type(self):
        """detect and return type for the specified Patch object analyzes header and file_names info"""
        # NOTE: must be run before file_names are normalized
        # common checks for git and plain
        if not (
            (self.source.startswith('a/') or self.source == '/dev/null') and
            (self.target.startswith('b/') or self.target == '/dev/null')
        ):
            return self.set_type(self.PLAIN)

        # GIT type check
        #  - header[-2] is like "diff --git a/oldname b/newname"
        #  - header[-1] is like "index <hash>..<hash> <mode>"
        # Git patch header len is 2 min
        if len(self.header) > 1:
            # detect the start of diff header - there might be some comments before
            for idx in range(len(self.header) - 1, -1, -1):
                if self.header[idx].startswith("diff --git"):
                    break

            if (
                self.header[idx].startswith('diff --git a/') and
                idx + 1 < len(self.header) and
                re.match(r'index \w{7}..\w{7} \d{6}', self.header[idx + 1])
            ):
                return self.set_type(self.GIT)

        return self.set_type(self.PLAIN)


class PatchResult:

    def __init__(self, content=''):
        self.errors = []
        self.content = content

    def error(self, msg):
        self.errors.append(msg)
        logger.error(msg)

    def __bool__(self):
        return not self.errors

    def __str__(self):
        return self.content


class Stream:
    """
    Enumerate wrapper that uses boolean end of stream status instead of
    StopIteration exception, and properties to access line information.
    """

    def __init__(self, content):
        if isinstance(content, bytes):
            content = content.decode()

        assert isinstance(content, str)
        self.content = content
        self.exhausted = False
        self.enum = enumerate(StringIO(self.content))

    def __iter__(self):
        return enumerate(StringIO(self.content), 1)

    def next_line(self):
        """
        Try to read the next line and return True if it is available or False if
        end of stream is reached.
        Used by PatchSet.parse to iterate lines.
        """
        if self.exhausted:
            return False

        try:
            self.lineno, self.line = next(self.enum)
            return True
        except StopIteration:
            self.exhausted = True
            self.line = False
            return False


class PatchSet:
    """ PatchSet is a patch parser and container. When used as an iterable, returns patches."""

    @classmethod
    def fromfile(cls, filename):
        """ Parse patch file. If successful, returns PatchSet() object. Otherwise returns False."""
        logger.debug("reading %s" % filename)
        with open(filename) as fp:
            return cls.fromstring(fp.read())

    @classmethod
    def fromstring(cls, s):
        """ Parse text string and return PatchSet() object (or False if parsing fails)"""
        ps = cls()
        ps.parse(Stream(s))
        return ps

    def __init__(self):
        # name of the PatchSet (filename or ...)
        self.name = None

        # patch set type - one of constants
        self.type = None

        # list of Patch objects
        self.patches = []

        self.errors = 0    # fatal parsing errors
        self.warnings = 0  # non-critical warnings

    def __bool__(self):
        return self.errors == 0

    @property
    def items(self):
        logger.warning('Deprecated "items" requested.')
        return self.patches

    def __len__(self):
        return len(self.patches)

    def __iter__(self):
        for i in self.patches:
            yield i

    def parse(self, stream):
        """parse unified diff return True on success"""
        self.errors = 0
        if isinstance(stream, str):
            stream = Stream(stream)

        next_hunk_no = 0    #: even if index starts with 0 user messages number hunks from 1
        patch = None
        hunk = None

        # hunk_actual variable is used to calculate hunk lines for comparison
        hunk_actual = dict(lines_src=None, lines_tgt=None)

        # define states (possible file regions) that direct parse flow
        head_scan = True  # start with scanning header
        file_names = False # lines starting with --- and +++
        hunk_head = False  # @@ -R +R @@ sequence
        hunk_body = False  #
        hunk_skip = False  # skipping invalid hunk mode
        hunk_parsed = False # state after successfully parsed hunk

        # regexp to match start of hunk, used groups - 1,3,4,6
        re_hunk_start = re.compile("^@@ -(\d+)(,(\d+))? \+(\d+)(,(\d+))? @@")
        
        # temp buffers for header and file_names info
        header = []
        src_name = None
        tgt_name = None

        # start of main cycle
        # each parsing block already has line available in stream.line
        while stream.next_line():
            # deciders: these only switch state to decide who should process
            # line fetched at the start of this cycle
            if hunk_parsed:
                hunk_parsed = False
                if re_hunk_start.match(stream.line):
                    hunk_head = True
                elif stream.line.startswith("--- "):
                    file_names = True
                else:
                    head_scan = True

            # read out header
            if head_scan:
                while not stream.exhausted and not stream.line.startswith("--- "):
                    header.append(stream.line)
                    stream.next_line()
                if stream.exhausted:
                    if patch == None:
                        logger.debug("no patch data found")  # error is shown later
                        self.errors += 1
                    else:
                        logger.info("{} unparsed bytes at end of stream".format(len(''.join(header))))
                        self.warnings += 1
                    # this is actually a loop exit
                    continue

                head_scan = False
                # switch to file_names state
                file_names = True

            line = stream.line
            lineno = stream.lineno

            # hunk_skip and hunk_body code skipped until definition of hunk_head is parsed
            if hunk_body:
                # [x] treat empty lines inside hunks as containing single space
                #     (this happens when diff is saved by copy/pasting to editor
                #      that strips trailing whitespace)
                if line.strip("\n") == "":
                        logger.debug("expanding empty line in a middle of hunk body")
                        self.warnings += 1
                        line = ' ' + line

                # process line first
                if re.match("^[- \\+\\\\]", line):
                    if line.startswith("-"):
                        hunk_actual["lines_src"] += 1
                    elif line.startswith("+"):
                        hunk_actual["lines_tgt"] += 1
                    elif not line.startswith("\\"):
                        hunk_actual["lines_src"] += 1
                        hunk_actual["lines_tgt"] += 1
                    hunk.text.append(line)
                else:
                    logger.warning(f"invalid hunk {next_hunk_no} at {lineno+1} for target {patch.target}")

                    # add hunk status node
                    hunk.invalid = True
                    patch.add(hunk)
                    self.errors += 1

                    # switch to hunk_skip state
                    hunk_body = False
                    hunk_skip = True

                # check exit conditions
                if hunk_actual["lines_src"] > hunk.lines_src or hunk_actual["lines_tgt"] > hunk.lines_tgt:
                    logger.warning(f"extra lines for hunk {next_hunk_no} at {lineno+1} for target {patch.target}")

                    # add hunk status node
                    hunk.invalid = True
                    patch.add(hunk)
                    self.errors += 1

                    # switch to hunk_skip state
                    hunk_body = False
                    hunk_skip = True
                elif hunk.lines_src == hunk_actual["lines_src"] and hunk.lines_tgt == hunk_actual["lines_tgt"]:
                    # hunk parsed successfully
                    patch.add(hunk)

                    # switch to hunk_parsed state
                    hunk_body = False
                    hunk_parsed = True
                    continue

            if hunk_skip:
                if re_hunk_start.match(line):
                    # switch to hunk_head state
                    hunk_skip = False
                    hunk_head = True
                elif line.startswith("--- "):
                    # switch to file_names state
                    hunk_skip = False
                    file_names = True
                    if len(self.patches) > 0:
                        logger.debug(f"{len(patch)} hunks for {patch}")

            if file_names:
                if line.startswith("--- "):
                    if src_name != None:
                        logger.warning("skipping false patch for %s" % src_name)
                        src_name = None
                        # double source filename line is encountered
                        # attempt to restart from this second line

                    match = re.match(r"^--- ([^\t]+)", line)
                    if match:
                        src_name = match.group(1).strip()
                    else:
                        logger.warning(f"skipping invalid filename at line {lineno+1}")
                        self.errors += 1
                        # XXX patch.header += line
                        # switch back to head_scan state
                        file_names = False
                        head_scan = True
                elif not line.startswith("+++ "):
                    if src_name != None:
                        logger.warning("skipping invalid patch with no target for %s" % src_name)
                        self.errors += 1
                        src_name = None
                    else:
                        # this should be unreachable
                        logger.warning("skipping invalid target patch")
                    file_names = False
                    head_scan = True
                else:
                    if tgt_name != None:
                        # XXX seems to be a dead branch  
                        logger.warning("skipping invalid patch - double target at line %d" % (lineno+1))
                        self.errors += 1
                        src_name = tgt_name = None
                        file_names = False
                        head_scan = True
                    else:
                        match = re.match(r"^\+\+\+ ([^\t]+)", line)
                        if not match:
                            logger.warning("skipping invalid patch - no target filename at line %d" % (lineno+1))
                            self.errors += 1
                            src_name = None

                            # switch back to head_scan state
                            file_names = False
                            head_scan = True
                        else:
                            if patch: # for the first run patch is None
                                self.patches.append(patch)

                            patch = Patch(src_name, match.group(1).strip(), header)
                            src_name = None
                            header = []

                            # switch to hunk_head state
                            file_names = False
                            hunk_head = True
                            next_hunk_no = 0
                            continue

            if hunk_head:
                match = re.match(r"^@@ -(\d+)(,(\d+))? \+(\d+)(,(\d+))? @@(.*)", line)
                if not match:
                    if not patch.hunks:
                        logger.warning(f"skipping invalid patch with no hunks for file {patch}")
                        self.errors += 1

                        # switch to head_scan state
                        hunk_head = False
                        head_scan = True
                        continue
                    else:
                        # switch to head_scan state
                        hunk_head = False
                        head_scan = True
                else:
                    hunk = Hunk(
                        start_src=int(match.group(1)),
                        start_tgt=int(match.group(4)),
                        desc=match.group(7)[1:].rstrip(),
                        lines_src=int(match.group(3)) if match.group(3) else None,
                        lines_tgt=int(match.group(6)) if match.group(6) else None,
                    )

                    hunk_actual["lines_src"] = hunk_actual["lines_tgt"] = 0

                    # switch to hunk_body state
                    hunk_head = False
                    hunk_body = True
                    next_hunk_no += 1
                    continue
        # /while stream.next_line()

        if patch:
            self.patches.append(patch)

        if not hunk_parsed:
            if hunk_skip:
                logger.warning("warning: finished with errors, some hunks may be invalid")
            elif head_scan:
                if len(self.patches) == 0:
                    logger.warning("error: no patch data found!")
                    return False
                else: # extra data at the end of file
                    pass 
            else:
                logger.warning("error: patch stream is incomplete!")
                self.errors += 1
                if len(self.patches) == 0:
                    return False

        if len(self.patches) > 0:
            logger.debug(f"- {len(patch)} hunks for {patch}")

        # XXX fix total hunks calculation
        logger.debug("files: {},  hunks: {}".format(
            len(self.patches),
            sum(len(p) for p in self.patches))
        )

        # ---- detect patch and patchset types ----
        for item in self.patches:
            item.detect_type()

        types = set(p.type for p in self.patches)
        self.type = self.PLAIN if len(types) > 1 else types.pop()
        return self.errors == 0

    def diffstat(self):
        """calculate diffstat and return as a string
            Notes: - original diffstat ouputs target filename
                   - single + or - shouldn't escape histogram
        """
        names = []
        insert = []
        delete = []
        delta = 0    # size change in bytes
        namelen = 0
        maxdiff = 0  # max number of changes for single file
                                  # (for histogram width calculation)
        for patch in self.patches:
            i = d = 0
            for hunk in patch:
                for line in hunk.text:
                    if line.startswith('+'):
                        i += 1
                        delta += len(line) - 1
                    elif line.startswith('-'):
                        d += 1
                        delta -= len(line) - 1
            names.append(patch.target)
            insert.append(i)
            delete.append(d)
            namelen = max(namelen, len(patch.target))
            maxdiff = max(maxdiff, i + d)

        output = ''
        statlen = len(str(maxdiff))  # stats column width
        for i,n in enumerate(names):
            # %-19s | %-4d %s
            fmt = " %-" + str(namelen) + "s | %" + str(statlen) + "s %s\n"

            hist = ''
            # -- calculating histogram --
            width = len(fmt % ('', '', ''))
            histwidth = max(2, 80 - width)
            if maxdiff < histwidth:
                hist = "+" * insert[i] + "-" * delete[i]
            else:
                iratio = (float(insert[i]) / maxdiff) * histwidth
                dratio = (float(delete[i]) / maxdiff) * histwidth

                # make sure every entry gets at least one + or -
                iwidth = 1 if 0 < iratio < 1 else int(iratio)
                dwidth = 1 if 0 < dratio < 1 else int(dratio)
                #print(iratio, dratio, iwidth, dwidth, histwidth)
                hist = "+" * iwidth + "-" * dwidth

            # -- /calculating +- histogram --
            output += (fmt % (names[i], str(insert[i] + delete[i]), hist))
  
        return  (
            f"{output} {len(names)} files changed, {sum(insert)} insertions(+), "
            f"{sum(delete)} deletions(-), {delta:+d} bytes"
        )

    def apply_file(self, filename, patch=None):
        with open(filename) as fp:
            return self.apply(fp.read(), patch)

    def apply(self, stream, patch=None):
        patch = patch or self.patches[0]
        logger.debug(f"processing {patch}")

        if isinstance(stream, str):
            stream = Stream(stream)

        hunk_no = 0
        hunk_find = []
        hunk_repl = []
        valid_hunks = 0

        self.can_patch = False
        hunk = patch.hunks[hunk_no]

        result = PatchResult()
        for lineno, line in stream:
            if lineno < hunk.start_src:
                continue
            elif lineno == hunk.start_src:
                hunk_find = [x[1:-1] for x in hunk.text if x[0] in " -"]
                hunk_repl = [x[1:-1] for x in hunk.text if x[0] in " +"]
                hunk_lineno = 0

            # check hunks in source file
            if lineno < hunk.start_src + len(hunk_find) - 1:
                if line.rstrip("\n") == hunk_find[hunk_lineno]:
                    hunk_lineno += 1
                else:
                    logger.info(f"file {patch.source} hunk #{hunk_no+1} doesn't match source at line {lineno}")
                    logger.info("expected: {}".format(hunk_find[hunk_lineno]))
                    logger.info("actual  : {}".format(line.rstrip("\n")))
                    # not counting this as error, because file may already be patched.
                    # check if file is already patched is done after the number of
                    # invalid hunks if found

                    # continue to check other hunks for completeness
                    hunk_no += 1
                    if hunk_no < len(patch):
                        hunk = patch.hunks[hunk_no]
                        continue
                    else:
                        break

            # check if processed line is the last line
            if lineno == hunk.start_src + len(hunk_find) - 1:
                logger.debug(f"hunk #{hunk_no+1} for {patch} ready to be patched")
                hunk_no += 1
                valid_hunks += 1
                if hunk_no < len(patch):
                    hunk = patch.hunks[hunk_no]
                else:
                    if valid_hunks == len(patch):
                        self.can_patch = True
                        break
        else:
            if hunk_no < len(patch):
                result.error(f"premature end of source file {patch} at {hunk_no+1}")

        if valid_hunks < len(patch):
            if self._match_file_hunks(StringIO(stream.content), patch.hunks):
                logger.warning(f"already patched {patch}")
            else:
                result.error(f"source file is different {patch}")

        if self.can_patch:
            content = self.write_hunks(StringIO(stream.content), patch.hunks)
            if content:
                result.content = content
                logger.info(f"successfully patched {patch}")
            else:
                result.error(f"error patching file {patch}")

        return result

    def _reverse(self):
        """ reverse patch direction (this doesn't touch file_names) """
        for p in self.patches:
            for h in p.hunks:
                h.start_src, h.start_tgt = h.start_tgt, h.start_src
                h.lines_src, h.lines_tgt = h.lines_tgt, h.lines_src
                for i, line in enumerate(h.text):
                    if line[0] == '+':
                        h.text[i] = '-' + line[1:]
                    elif line[0] == '-':
                        h.text[i] = '+' +line[1:]

    def revert(self):
        """ apply patch in reverse order """
        reverted = copy.deepcopy(self)
        reverted._reverse()
        return reverted.apply()

    def _match_file_hunks(self, stream, hunks):
        matched = True
        lineno = 1
        line = stream.readline()
        hno = None
        try:
            for hno, h in enumerate(hunks):
                # skip to first line of the hunk
                while lineno < h.start_tgt:
                    if not len(line): # eof
                        logger.debug("check failed - premature eof before hunk: %d" % (hno + 1))
                        raise NoMatch
                    line = stream.readline()
                    lineno += 1
                for hline in h.text:
                    if hline.startswith("-"):
                        continue
                    if not len(line):
                        logger.debug("check failed - premature eof on hunk: %d" % (hno + 1))
                        # todo: \ No newline at the end of file
                        raise NoMatch
                    if line.rstrip("\r\n") != hline[1:].rstrip("\r\n"):
                        logger.debug("file is not patched - failed hunk: %d" % (hno + 1))
                        raise NoMatch
                    line = stream.readline()
                    lineno += 1

        except NoMatch:
            matched = False
            # todo: display failed hunk, i.e. expected/found

        return matched

    def write_hunks(self, stream, hunks):
        """Return a patched string"""
        hunks = iter(hunks)
        srclineno = 1
        lines = []
        for i, h in enumerate(hunks):
            logger.debug(f"hunk {i}")
            # skip to line just before hunk starts
            while srclineno < h.start_src:
                lines.append(stream.readline())
                srclineno += 1

            for hline in h.text:
                # todo: check \ No newline at the end of file
                if hline.startswith("-") or hline.startswith("\\"):
                    stream.readline()
                    srclineno += 1
                    continue
                else:
                    if not hline.startswith("+"):
                        stream.readline()
                        srclineno += 1
                    lines.append(hline[1:])
          
        for line in stream:
            lines.append(line)

        return ''.join(lines)

    def dump(self):
        for patch in self.patches:
            for headline in patch.header:
                print(headline, end='')

            print(f'--- {patch.source}\n+++ {patch.target}')
            for h in patch.hunks:
                print(f'@@ -{h.start_src},{h.lines_src} +{h.start_tgt},{h.lines_tgt} @@')
                for line in h.text:
                    print(line, end='')

    def can_patch(self, filename, content):
        """ Check if specified filename can be patched. Returns None if file can
        not be found among source filenames. False if patch can not be applied
        clearly. True otherwise.
        :returns: True, False or None
        """
        for p in self:
            if filename == p.source:
                return self._match_file_hunks(StringIO(content), p.hunks)
        return False


class DiffPatch:

    @classmethod
    def fromfiles(cls, their_filename, our_filename):
        their_filename = Path(their_filename)
        our_filename = Path(our_filename)

        their_content = their_filename.read_text()
        return cls.patch(cls.diff(
            their_content, our_filename.read_text(),
            their_filename, our_filename,
            their_filename.mod_time(), our_filename.mod_time()
        ), their_content)

    @classmethod
    def fromstrings(cls, their_content, our_content):
        return cls.patch(cls.diff(their_content, our_content), their_content)

    @staticmethod
    def diff(
        their_content, our_content,
        their_filename='theirfile', our_filename='ourfile',
        their_ts=None, our_ts=None,
        context=3
    ):
        ts = datetime.now(timezone.utc).astimezone().isoformat()
        their_ts = str(their_ts or ts)
        our_ts = str(our_ts or ts)

        if isinstance(their_content, str):
            their_content = their_content.splitlines()

        if isinstance(our_content, str):
            our_content = our_content.splitlines()

        diff = difflib.unified_diff(
            their_content, our_content,
            str(their_filename), str(our_filename),
            their_ts, our_ts,
            n=3
        )
        lines = list(line.rstrip('\n') for line in diff)
        return '\n'.join(lines)

    @staticmethod
    def patch(patch, their_content):
        if patch:
            ps = PatchSet.fromstring(patch)
            return ps.apply(their_content)

        return PatchResult(their_content)


fromstring = PatchSet.fromstring
fromfile = PatchSet.fromfile


def main():
    import argparse

    parser = argparse.ArgumentParser(description='python-patch %s' % __version__)
    parser.add_argument('files', nargs='+')
    parser.add_argument('-q', action='store_true')
    parser.add_argument('-v', type=int, dest='verbosity', default=0, help='be verbose')
    parser.add_argument('--diffstat', action='store_true', dest='diffstat',
        help='print diffstat and exit')
    parser.add_argument('--revert', action='store_true',
        help='apply patch in reverse order (unpatch)')
    parser.add_argument('-d', '--diffpatch', action='store_true')
    parser.add_argument('--pdb', action='store_true')

    args = parser.parse_args()

    if not args:
        args.print_help()
        sys.exit(0)

    if args.q:
        logger.addHandler(logging.NullHandler())
    else:
        logger.setLevel(logging.DEBUG)
        streamhandler = logging.StreamHandler()
        streamhandler.setFormatter(logging.Formatter('>>> %(levelname)-8s %(message)s'))
        streamhandler.setLevel(
            {0: logging.WARNING, 1: logging.INFO, 2: logging.DEBUG}[args.verbosity]
        )
        logger.addHandler(streamhandler)

    if args.pdb:
        import ipdb; ipdb.set_trace()

    try:
        if args.diffpatch:
            res = DiffPatch.fromfiles(Path(args.files[0]), Path(args.files[1]))
        else:
            patchfile = Path(args.files.pop(0))
            if not patchfile.exists() or not patchfile.is_file():
                logger.error('patch file does not exist - %s' % patchfile)
                sys.exit(1)

            ps = PatchSet.fromfile(patchfile)

            if args.diffstat:
                fn = ps.diffstat
            elif args.revert:
                fn = ps.revert
            else:
                fn = ps.apply_file

            res = fn(*args.files)

        if bool(res):
            print(res)
        else:
            logger.error('Errors:\n{}'.format('\n'.join(res.errors)))
            sys.exit(1)

    except:
        logger.exception('Something is foobar')
        sys.exit(2)

    sys.exit(0)


if __name__ == '__main__':
    main()
