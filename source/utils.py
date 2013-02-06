#!/usr/bin/env python
#
# $File: utils.py $
# $LastChangedDate$
# $Rev$
#
# This file is part of variant_tools, a software application to annotate,
# summarize, and filter variants for next-gen sequencing ananlysis.
# Please visit http://varianttools.sourceforge.net for details.
#
# Copyright (C) 2004 - 2011 Bo Peng (bpeng@mdanderson.org)
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program. If not, see <http://www.gnu.org/licenses/>.
#

'''
This module provides utility functions and a database engine that works
for both sqlite3 and mysql.
'''
import os
import sys
import glob
import logging
import subprocess
import urllib
import urlparse
import getpass
import time
import tempfile
import tokenize
import cStringIO
import gzip
import copy
import threading
import re
import stat
import random
import shutil
try:
    # not all platforms/installations of python support bz2
    import bz2
    bz2_support = True
except:
    bz2_support = False

try:
    if sys.version_info.major == 2:
        import vt_sqlite3_py2 as sqlite3
        from cgatools_py2 import CrrFile, Location, Range
    else:
        import vt_sqlite3_py3 as sqlite3
        from cgatools_py3 import CrrFile, Location, Range
except ImportError as e:
    sys.exit('Failed to import module ({})\n'
        'Please verify if you have installed variant tools successfully (using command '
        '"python setup.py install") and you are NOT running command vtools from within '
        'the source directory.'.format(e))


class RuntimeOptions(object):
    # the following make RuntimeOptions a singleton class
    _instance = None
    def __new__(cls, *args, **kwargs):
        if not cls._instance:
            cls._instance = super(RuntimeOptions, cls).__new__(cls, *args, **kwargs)
        return cls._instance

    def __init__(self):
        # these options could be set persistently
        self.persistent_options = {
            'logfile_verbosity': ('2', 'Verbosity level of the log file, can be 0 for warning '
                'and error only, 1 for general information, or 2 for general and debug information.'),
            'verbosity': ('1', 'Default verbosity level (to the standard output) of the project. '
                'This option can be set during vtools init where the verbosity level set by option'
                ' --verbosity will be set as the project default.'),
            'sqlite_pragma': ('synchronous=OFF,default_cache_size=2000', 'If your project uses a '
                'sqlite database engine, you can optimize its performance by setting appropriate '
                'pragma, which will be applied to all opened database connections.'),
            'import_num_of_readers': (2, 'variant tools by default uses two processes to read from '
                'input files during multi-process importing (--jobs > 0). You can want to set it '
                'to zero if a single process provides better performance or reduces disk traffic.'),
            # a temporary directory that is used to store temporary files. Will be
            # cleared after project is closed.
            'temp_dir': (None, 'Use the specified temporary directory to store temporary files '
                'to improve performance (use separate disks for project and temp files), or '
                'avoid problems due to insufficient disk space.'),
            'treat_missing_as_wildtype': ('False', 'Treat missing values as wildtype alleles for '
                'association tests. This option is used when samples are called individuals or '
                'in batch so genotypes for some samples are ignored and treated as missing if '
                'they consist of all wildtype alleles. This option should be used with caution '
                'because it convert real missing genotypes and genotypes removed due to, for '
                'example low quality score, to wildtype genotypes.'),
            'association_timeout': (None, 'Cancel associate test and return special values '
                'when a test lasts more than specified time (in seconds). The default '
                'value of this option is None, which stands for no time limit.'),
            'associate_num_of_readers': (None, 'Use specified number of processes to read '
                'genotype data for association tests. The default value is the minimum of value '
                'of option --jobs and 8. Note that a large number of reading processes might '
                'lead to degraded performance or errors due to disk access limits.'),
            'search_path': ('.;http://vtools.houstonbioinformatics.org/', 'A ;-separated list of '
                'directories and URLs that are used to locate annotation database (.ann, .DB), '
                'file format (.fmt) and other files. Reset this option allows alternative '
                'local or online storage of such files. variant tools will append trailing '
                'directories such as annoDB for certain types of data so only root directories '
                'should be listed in this search path.'),
            'local_resource': ('~/.variant_tools', 'A directory to store variant tools related '
                'resources such as reference genomes and annotation database. Files under this '
                'directory is usually downloaded automatically upon use, but can also be '
                'synchronized directly from http://vtools.houstonbioinformatics.org/.')
        }
        # this will be the raw command that will be saved to log file
        self._command_line = ''
        # path to the project cache
        self._cache_dir = 'cache'
        #
        self._local_resource = self.persistent_options['local_resource'][0]
        #
        self._logfile_verbosity = self.persistent_options['logfile_verbosity'][0]
        self._verbosity = self.persistent_options['verbosity'][0]
        # default sqlite pragma
        self._sqlite_pragma = self.persistent_options['sqlite_pragma'][0]
        # number of processes used for reader under multi-processing mode
        self._import_num_of_readers = self.persistent_options['import_num_of_readers'][0]
        # path to a temporary directory, will be allocated automatically.
        self._temp_dir = self.persistent_options['temp_dir'][0]
        self._proj_temp_dir = self._temp_dir  # per project temp directory
        # how to handle missing data
        self._treat_missing_as_wildtype = self.persistent_options['treat_missing_as_wildtype'][0]
        # association test time out
        self._association_timeout = self.persistent_options['association_timeout'][0]
        # association test number of genotype loaders
        self._associate_num_of_readers = self.persistent_options['associate_num_of_readers'][0]
        # search path
        self._search_path = self.persistent_options['search_path'][0]
    #
    # attribute command line
    #
    #
    # attribute logfile_verbosity
    #
    def _set_logfile_verbosity(self, v):
        if v in ['0', '1', '2']:
            self._logfile_verbosity = v
    #
    logfile_verbosity = property(lambda self: self._logfile_verbosity, _set_logfile_verbosity)
    #
    #
    # attribute verbosity
    #
    def _set_verbosity(self, v):
        self._verbosity = v
    #
    verbosity = property(lambda self: self._verbosity, _set_verbosity)
    #
    # attribute pragma
    #
    def _set_sqlite_pragma(self, pragma):
        # 'None' is for backward compatibility
        if pragma is None or pragma == 'None':
            return
        try:
            p = pragma.split(',')
            #
            for item in p:
                if '=' not in str(item):
                    raise ValueError('Invalid pragma {}'.format(item))
            self._sqlite_pragma = pragma
        except:
            sys.stderr.write('Invalid pragma {}\n'.format(pragma))
    #
    sqlite_pragma = property(lambda self: self._sqlite_pragma.split(','), _set_sqlite_pragma)
    #
    # attribute import_num_of_readers
    #
    def _set_import_num_of_readers(self, n):
        try:
            if n is not None:
                int(n)   # test if n is an integer
                self._import_num_of_readers = str(n)
        except:
            sys.stderr.write('Failed to set number of readers to {}\n'.format(n))
    #
    import_num_of_readers = property(lambda self: int(self._import_num_of_readers), _set_import_num_of_readers)
    #
    # attribute cache_dir, which is not configurable
    #
    def _set_cache_dir(self, path=None):
        if path is not None:
            self._cache_dir = path
        try:
            if not os.path.isdir(self._cache_dir):
                sys.stderr.write('Creating cache directory {}\n'.format(self._cache_dir))
                os.makedirs(self._cache_dir)
        except:
            raise RuntimeError('Failed to create cache directory '.format(self._cache_dir))
    #
    cache_dir = property(lambda self: 'cache', _set_cache_dir)
    #
    # attribute local_resource
    #
    def _set_local_resource(self, path=None):
        if path is not None:
            self._local_resource = path
        try:
            if not os.path.isdir(os.path.expanduser(self._local_resource)):
                sys.stderr.write('Creating local resource directory {}\n'.format(self._local_resource))
                os.makedirs(os.path.expanduser(self._local_resource))
        except:
            raise RuntimeError('Failed to create local resource directory '.format(self._local_resource))
    #
    local_resource = property(lambda self: os.path.expanduser(self._local_resource), _set_local_resource)
    #
    # attribute temp_dir
    #
    def _set_temp_dir(self, path=None):
        # user can explicitly set a path ('None' could be saved by a previous version of vtools)
        if path not in [None, 'None', '']:
            if os.path.isdir(path) and (os.listdir(path) or 
                    (not os.access(path, os.R_OK)) or (not os.access(path, os.W_OK)) or
                    (os.stat(path).st_mode & stat.S_ISVTX == 512)):
                raise ValueError('Cannot set temporary directory to directory {} because '.format(path) + \
                    'it is not empty or is not writable or deletable. Please clear this directory or use '
                    'command "vtools admin --set_runtime_option temp_dir=DIR" to set it to another path, '
                    'or a random path (empty DIR).')
            self._temp_dir = path
            self._proj_temp_dir = path
        # the usual case
        if self._temp_dir is None:
            self._proj_temp_dir = tempfile.mkdtemp() 
        try:
            if not os.path.isdir(os.path.expanduser(self._proj_temp_dir)):
                os.makedirs(os.path.expanduser(self._proj_temp_dir))
        except:
            sys.stderr.write('Failed to create a temporary directory {}.\n'.format(self._proj_temp_dir))
            self._proj_temp_dir = tempfile.mkdtemp()
    #
    temp_dir = property(lambda self: os.path.expanduser(self._proj_temp_dir), _set_temp_dir)
    #
    # attribute treat_missing_as_wildtype
    def _set_treat_missing_as_wildtype(self, val):
        if val in [None, 'None', '0', 'False', 'false', 'FALSE']:
            self._treat_missing_as_wildtype = 'False'
        elif val in ['1', 'True', 'TRUE', 'true']:
            self._treat_missing_as_wildtype = 'True'
        else:
            sys.stderr.write('Invalid input ({}) for runtime option treat_missing_as_wildtype\n'.format(val))
            self._treat_missing_as_wildtype = 'False'
    #
    treat_missing_as_wildtype = property(lambda self: True if self._treat_missing_as_wildtype == 'True' else False,
        _set_treat_missing_as_wildtype)
    #
    # attribute association_timeout
    def _set_association_timeout(self, val):
        try:
            if val in ['None', None]:
                self._association_timeout = None
            else:
                # test if val can be converted to int
                int(val)
                self._association_timeout = val
        except:
            pass
    #
    association_timeout = property(lambda self: 0 if self._association_timeout is None else int(self._association_timeout), _set_association_timeout) 
    #
    # attribute associate_num_of_readers
    def _set_associate_num_of_readers(self, val):
        try:
            if val in ['None', None]:
                self._associate_num_of_readers = None
            else:
                # test if val can be converted to int
                int(val)
                self._associate_num_of_readers = val
        except:
            pass
    #
    associate_num_of_readers = property(lambda self: 0 if self._associate_num_of_readers is None else int(self._associate_num_of_readers), _set_associate_num_of_readers) 
    #
    # attribute search_path
    def _set_search_path(self, val):
        if val not in ['None', None]:
            self._search_path = val
    #
    search_path = property(lambda self: self._search_path, _set_search_path)


# the singleton object of RuntimeOptions
runOptions = RuntimeOptions()

SQL_KEYWORDS = set([
    'ADD', 'ALL', 'ALTER', 'ANALYZE', 'AND', 'AS', 'ASC', 'ASENSITIVE', 'BEFORE',
    'BETWEEN', 'BIGINT', 'BINARY', 'BLOB', 'BOTH', 'BY', 'CALL', 'CASCADE', 'CASE',
    'CHANGE', 'CHAR', 'CHARACTER', 'CHECK', 'COLLATE', 'COLUMN', 'CONDITION',
    'CONSTRAINT', 'CONTINUE', 'CONVERT', 'CREATE', 'CROSS', 'CURRENT_DATE',
    'CURRENT_TIME', 'CURRENT_TIMESTAMP', 'CURRENT_USER', 'CURSOR', 'DATABASE',
    'DATABASES', 'DAY_HOUR', 'DAY_MICROSECOND', 'DAY_MINUTE', 'DAY_SECOND', 'DEC',
    'DECIMAL', 'DECLARE', 'DEFAULT', 'DELAYED', 'DELETE', 'DESC',
    'DESCRIBE', 'DETERMINISTIC', 'DISTINCT', 'DISTINCTROW', 'DIV', 'DOUBLE',
    'DROP', 'DUAL', 'EACH', 'ELSE', 'ELSEIF', 'ENCLOSED', 'ESCAPED', 'EXISTS',
    'EXIT', 'EXPLAIN', 'FALSE', 'FETCH', 'FLOAT', 'FLOAT4', 'FLOAT8', 'FOR',
    'FORCE', 'FOREIGN', 'FROM', 'FULLTEXT', 'GRANT', 'GROUP', 'HAVING', 'HIGH_PRIORITY',
    'HOUR_MICROSECOND', 'HOUR_MINUTE', 'HOUR_SECOND', 'IF', 'IGNORE', 'IN',
    'INDEX', 'INFILE', 'INNER', 'INOUT', 'INSENSITIVE', 'INSERT',
    'INT', 'INT1', 'INT2', 'INT3', 'INT4', 'INT8', 'INTEGER', 'INTERVAL', 'INTO',
    'IS', 'ITERATE', 'JOIN', 'KEY', 'KEYS', 'KILL', 'LEADING', 'LEAVE', 'LEFT',
    'LIKE', 'LIMIT', 'LINES', 'LOAD', 'LOCALTIME', 'LOCALTIMESTAMP',
    'LOCK', 'LONG', 'LONGBLOB', 'LONGTEXT', 'LOOP', 'LOW_PRIORITY', 'MATCH',
    'MEDIUMBLOB', 'MEDIUMINT', 'MEDIUMTEXT', 'MIDDLEINT', 'MINUTE_MICROSECOND',
    'MINUTE_SECOND', 'MOD', 'MODIFIES', 'NATURAL', 'NOT', 'NO_WRITE_TO_BINLOG',
    'NULL', 'NUMERIC', 'ON', 'OPTIMIZE', 'OPTION', 'OPTIONALLY', 'OR',
    'ORDER', 'OUT', 'OUTER', 'OUTFILE', 'PRECISION', 'PRIMARY', 'PROCEDURE',
    'PURGE', 'READ', 'READS', 'REAL', 'REFERENCES', 'REGEXP', 'RELEASE',
    'RENAME', 'REPEAT', 'REPLACE', 'REQUIRE', 'RESTRICT', 'RETURN',
    'REVOKE', 'RIGHT', 'RLIKE', 'SCHEMA', 'SCHEMAS', 'SECOND_MICROSECOND',
    'SELECT', 'SENSITIVE', 'SEPARATOR', 'SET', 'SHOW', 'SMALLINT',
    'SONAME', 'SPATIAL', 'SPECIFIC', 'SQL', 'SQLEXCEPTION', 'SQLSTATE',
    'SQLWARNING', 'SQL_BIG_RESULT', 'SQL_CALC_FOUND_ROWS', 'SQL_SMALL_RESULT',
    'SSL', 'STARTING', 'STRAIGHT_JOIN', 'TABLE', 'TERMINATED',
    'THEN', 'TINYBLOB', 'TINYINT', 'TINYTEXT', 'TO', 'TRAILING',
    'TRIGGER', 'TRUE', 'UNDO', 'UNION', 'UNIQUE', 'UNLOCK', 'UNSIGNED',
    'UPDATE', 'USAGE', 'USE', 'USING', 'UTC_DATE', 'UTC_TIME', 'UTC_TIMESTAMP', 'VALUES',
    'VARBINARY', 'VARCHAR', 'VARCHARACTER', 'VARYING', 'WHEN', 'WHERE', 'WHILE',
    'WITH', 'WRITE', 'XOR', 'YEAR_MONTH', 'ZEROFILL', 'ASENSITIVE', 'CALL', 'CONDITION',
    'CONNECTION', 'CONTINUE', 'CURSOR', 'DECLARE', 'DETERMINISTIC', 'EACH',
    'ELSEIF', 'EXIT', 'FETCH', 'GOTO', 'INOUT', 'INSENSITIVE', 'ITERATE', 'LABEL', 'LEAVE',
    'LOOP', 'MODIFIES', 'OUT', 'READS', 'RELEASE', 'REPEAT', 'RETURN', 'SCHEMA', 'SCHEMAS',
    'SENSITIVE', 'SPECIFIC', 'SQL', 'SQLEXCEPTION', 'SQLSTATE', 'SQLWARNING', 'TRIGGER',
    'UNDO', 'UPGRADE', 'WHILE', 'ABS', 'ACOS', 'ADDDATE', 'ADDTIME', 'ASCII', 'ASIN',
    'ATAN', 'AVG', 'BETWEEN', 'AND', 'BINARY', 'BIN', 'BIT_AND',
    'BIT_OR', 'CASE', 'CAST', 'CEIL', 'CHAR', 'CHARSET', 'CONCAT', 'CONV', 'COS', 'COT',
    'COUNT', 'DATE', 'DAY', 'DIV', 'EXP', 'IS', 'LIKE', 'MAX', 'MIN', 'MOD', 'MONTH',
    'LOG', 'POW', 'SIN', 'SLEEP', 'SORT', 'STD', 'VALUES', 'SUM'
])

#
# Utility functions
#
class ColoredFormatter(logging.Formatter):
    # A variant of code found at http://stackoverflow.com/questions/384076/how-can-i-make-the-python-logging-output-to-be-colored
    def __init__(self, msg):
        logging.Formatter.__init__(self, msg)
        self.LEVEL_COLOR = {
            'DEBUG': 'BLUE',
            'INFO': 'BLACK',
            'WARNING': 'PURPLE',
            'ERROR': 'RED',
            'CRITICAL': 'RED_BG',
            }
        self.COLOR_CODE={
            'ENDC':0,  # RESET COLOR
            'BOLD':1,
            'UNDERLINE':4,
            'BLINK':5,
            'INVERT':7,
            'CONCEALD':8,
            'STRIKE':9,
            'GREY30':90,
            'GREY40':2,
            'GREY65':37,
            'GREY70':97,
            'GREY20_BG':40,
            'GREY33_BG':100,
            'GREY80_BG':47,
            'GREY93_BG':107,
            'DARK_RED':31,
            'RED':91,
            'RED_BG':41,
            'LIGHT_RED_BG':101,
            'DARK_YELLOW':33,
            'YELLOW':93,
            'YELLOW_BG':43,
            'LIGHT_YELLOW_BG':103,
            'DARK_BLUE':34,
            'BLUE':94,
            'BLUE_BG':44,
            'LIGHT_BLUE_BG':104,
            'DARK_MAGENTA':35,
            'PURPLE':95,
            'MAGENTA_BG':45,
            'LIGHT_PURPLE_BG':105,
            'DARK_CYAN':36,
            'AUQA':96,
            'CYAN_BG':46,
            'LIGHT_AUQA_BG':106,
            'DARK_GREEN':32,
            'GREEN':92,
            'GREEN_BG':42,
            'LIGHT_GREEN_BG':102,
            'BLACK':30,
        }

    def colorstr(self, astr, color):
        return '\033[{}m{}\033[{}m'.format(self.COLOR_CODE[color], astr, self.COLOR_CODE['ENDC'])

    def format(self, record):
        record = copy.copy(record)
        levelname = record.levelname
        if levelname in self.LEVEL_COLOR:
            record.levelname = self.colorstr(levelname, self.LEVEL_COLOR[levelname])
            record.name = self.colorstr(record.name, 'BOLD')
            record.msg = self.colorstr(record.msg, self.LEVEL_COLOR[levelname])
        return logging.Formatter.format(self, record)


def createLogger(logfile, mode):
    # create a logger
    logger = logging.getLogger()
    logger.setLevel(logging.DEBUG)
    # output to standard output
    cout = logging.StreamHandler()
    levels = {
        '0': logging.WARNING,
        '1': logging.INFO,
        '2': logging.DEBUG,
        None: logging.INFO
    }
    #
    cout.setLevel(levels[runOptions.verbosity])
    cout.setFormatter(ColoredFormatter('%(levelname)s: %(message)s'))
    logger.addHandler(cout)
    # output to a log file
    ch = logging.FileHandler(logfile, mode)
    # NOTE: debug informaiton is always written to the log file
    ch.setLevel(levels[runOptions.logfile_verbosity])
    ch.setFormatter(logging.Formatter('%(asctime)s: %(levelname)s: %(message)s'))
    logger.addHandler(ch)
    return logger

def lineCount(filename, encoding='UTF-8'):
    '''Estimate the number of lines using file size and line size. This
    function does not attemp to calculate line count exactly because files
    handled by variant tools can be huge. '''
    totalSize = os.path.getsize(filename)
    if totalSize < 500000:
        # small file, read the number of lines directly
        if filename.endswith('.gz'):
            return len(gzip.open(filename, 'rb').readlines())
        elif filename.endswith('.bz2'):
            if not bz2_support:
                raise ValueError('Direct reading of bz2 files is not supported. Please update your python installation or uncompress the file before processing')
            return len(bz2.BZ2File(filename).readlines())
        else:
            return len(open(filename, 'rb').readlines())
    elif filename.endswith('.gz'):
        input = gzip.open(filename, 'rb')
        input.seek(50000, 0)
        content = input.read(500000).decode(encoding)
        input.close()
        lineCount = len(content.split('\n'))
        input.close()
        # assuming an arbitrary compression ratio of 5. :-)
        return int(lineCount * (5 * totalSize / 500000.))
    elif filename.endswith('.bz2'):
        if not bz2_support:
            raise ValueError('Direct reading of bz2 files is not supported. Please update your python installation or uncompress the file before processing')
        input = bz2.BZ2File(filename, 'rb')
        input.seek(50000, 0)
        content = input.read(500000).decode(encoding)
        input.close()
        lineCount = len(content.split('\n'))
        input.close()
        # assuming an arbitrary compression ratio of 5. :-)
        return int(lineCount * (5 * totalSize / 500000.))
    else:
        # only binary mode can accomendate end-relative seeks in python 3.
        input = open(filename, 'rb')
        # count from the back because they tend to be records
        # with consistent size
        input.seek(-99000, 2)
        content = input.read()
        input.close()
        lineCount = content.decode(encoding).count('\n')
        input.close()
        return int(lineCount * (totalSize / 99000.))


def hasCommand(cmd):
    try:
        fnull = open(os.devnull, 'w')
        result = subprocess.Popen(cmd, shell=True, stdout=fnull, stderr=fnull)
        result.terminate()
        fnull.close()
    except OSError:
        # command not found
        return False
    except Exception:
        # other error is OK
        return True
    return True

def openFile(filename):
    if filename.lower().endswith('.gz'):
        return gzip.open(filename, 'rb')
    elif filename.lower().endswith('.bz2'):
        return bz2.BZ2File(filename, 'rb')
    else:
        # text file
        # because readline() from gzip.open will be byte, not string, we should return
        # binary here in order to process them equally in order for things to work
        # correctly under python 3 
        return open(filename, 'rb')


def typeOfValues(vals):
    '''Figure out type of values and return INT, FLOAT or VARCHAR(maxLength)'''
    vals = [x for x in vals if x.lower() not in ('na', 'null', 'none', '')]
    if len(vals) == 0:
        # a good default value?
        return 'VARCHAR(10)'
    try:
        map(int, vals)
        return 'INT'
    except:
        try:
            map(float, vals)
            return 'FLOAT'
        except:
            return 'VARCHAR({})'.format(max([len(x) for x in vals]))

class delayedAction:
    '''Call the passed function with param after a few seconds. It is most often 
    used to display certain message only if an action takes a long time.

        action = delayedAction(self.logger.info, 'This might take a while', 5)
        some_action_that_might_take_a_while
        del action

    if the action finishes very quick, the message will not be displayed.    
    '''
    def __init__(self, func, param, delay=5):
        self.timer = threading.Timer(delay, func, (param,))
        self.timer.start()

    def __del__(self):
        self.timer.cancel()


def filesInURL(URL, ext=''):
    '''directory listing of a URL'''
    fh = urllib.urlopen(URL)
    files = []
    for line in fh.readlines():
        m = re.search('href="(.*){}"'.format(ext), line.decode())
        if m:
            files.append(m.group(1))
    return files

def makeTableName(data, prefix = '__'):
    '''Make data a valid table name'''
    name = '_'.join([str(x) for x in data])
    name = name.replace('+', '_plus_').replace('-', '_minus_')
    return prefix + re.sub('[\W]+', '_', name)

from array import array
try:
    from fcntl import ioctl
    import termios
except ImportError:
    pass

class ProgressBar:
    '''A text-based progress bar, it differs from regular progress bar in that
    1. it can start from the middle with init count
    2. it accept update for successful and failed counts
    '''
    def __init__(self, message, totalCount = None, initCount=0, initFailedCount=0):
        if runOptions.verbosity == '0':
            self.update = self.empty
            self.curlUpdate = self.empty
            self.urllibUpdate = self.empty
            self.sqliteUpdate = self.empty
            self.outputProgress = self.empty
            self.done = self.empty
            return
        self.main = message
        self.main_start_time = time.time()
        self.message = self.main
        try:
            h,w = array('h', ioctl(sys.stderr, termios.TIOCGWINSZ, '\0'*8))[:2]
            self.term_width = w
        except:
            self.term_width = 79
        # total count, including failed ones
        self.count = 0
        self.failed_count = 0
        # total initial count
        self.init_count = initCount
        self.init_failed_count = initFailedCount
        #
        self.finished = 0
        self.reset('', totalCount)

    def reset(self, msg='', totalCount = None):
        if msg:
            self.message = '{} - {}'.format(self.main, msg)
        self.finished += self.count
        self.count = 0
        self.failed_count = 0
        self.totalCount = totalCount
        self.start_time = None
        self.last_time = None
        self.outputProgress()

    def empty(self, *args, **kwargs):
        return

    def update(self, count, failed_count=0):
        '''completed count jobs, with failed_count failed jobs'''
        if failed_count > count:
            raise RuntimeError('Failed count should always less than or equal to completed count.')
        # do not update if the diferent is less than 0.1% of the total count.
        # this is to avoid excess of calling the time() function
        if self.totalCount is not None and (count - self.count) * 1000 < self.totalCount:
            return
        self.count = count
        self.failed_count = failed_count
        self.outputProgress()

    def curlUpdate(self, total, existing, upload_t, upload_d):
        '''Update called from pycurl'''
        self.count = existing
        self.totalCount = total
        self.outputProgress()
        
    def urllibUpdate(self, count, blockSize, totalSize):
        '''Update called from urllib'''
        self.count = count * blockSize
        self.totalCount = totalSize
        self.outputProgress()

    def sqliteUpdate(self):
        self.count += 1
        if self.count % 1000 == 0:
            self.outputProgress()

    def outputProgress(self):
        '''Output progress'''
        if not self.start_time:
            self.start_time = time.time()
            self.last_time = self.start_time
        cur_time = time.time()
        # stop update progress bar more than once per second.
        if self.count > 0 and self.count != self.totalCount and cur_time - self.last_time < 1:
            return
        msg = ['', '', '', '', '', '', '']
        # message
        msg[0] = self.message + ':'
        self.last_time = cur_time
        second_elapsed = cur_time - self.start_time
        if second_elapsed < 0.0001 or self.count == 0:
            msg[4] = ''
        else:
            cps = (self.count - self.init_count) / second_elapsed
            # speed
            if cps > 1000000:
                msg[4] = ' {:.1f}M/s'.format(cps/1000000)
            elif cps > 1000:
                msg[4] = ' {:.1f}K/s'.format(cps/1000)
            elif cps > 0.05:
                msg[4] = ' {:.1f}/s'.format(cps)
            elif cps > 1e-6:
                msg[4] = ' {:.1f}s each'.format(1. / cps)
            else:
                msg[4] = ' 0.0/s'
        # estimated time left
        if self.totalCount:
            perc = min(1, float(self.count) / self.totalCount)
            init_perc = min(1, float(self.init_count) / self.totalCount)
            time_left = (second_elapsed / (perc - init_perc) * (1 - perc)) if perc > init_perc else 0
            msg[5] += ' in {}{}'.format('' if time_left < 86400 else '{} days '.format(int(time_left/86400)),
                time.strftime('%H:%M:%S', time.gmtime(time_left)))
        # percentage / progress
        if self.count > 0:
            if self.failed_count == 0:
                # no failed count
                msg[3] = ' {:,}'.format(int(self.count))
                m3Len = len(msg[3])
            else:
                # display failed count in red
                msg[3] = ' {:,}/\033[1;31m{:,}\033[1;m'.format(int(self.count), int(self.failed_count))
                m3Len = len(msg[3]) - 12  # the color strings should not be counted as length of message
        else:
            msg[3] = ' '
            m3Len = 1
        if self.totalCount:
            # percentage
            perc = min(1, float(self.count) / self.totalCount)
            failed_perc = min(1, float(self.failed_count) / self.totalCount)
            msg[1] = ' {:5.1f}%'.format(perc * 100)
            width = self.term_width - len(msg[0]) - len(msg[1]) - m3Len - len(msg[4]) - len(msg[5])
            if width > 5:
                front = int((perc - failed_perc) * (width - 5))
                failed_front = int(failed_perc * (width - 5))
                back = width - 5 - front - failed_front
                if failed_front == 0:
                    msg[2] = ' [{}>{}]'.format('=' * front, ' ' * back)
                else:
                    msg[2] = ' [{}\033[1;31m{}\033[1;m>{}]'.format('=' * front, '=' * failed_front, ' ' * back)
        else:
            width = self.term_width - len(msg[0]) - len(msg[1]) - m3Len - len(msg[4])
            msg[6] = ' '*width
        # use stderr to avoid messing up process output
        sys.stderr.write('\r' + ''.join(msg))

    def done(self, completed=None, failed=None):
        '''Finish, output a new line'''
        if completed is not None:
            self.count = completed
        elif self.totalCount:
            self.count = self.totalCount
        #
        if failed is not None:
            self.falied_count = failed
        #
        msg = ['', '', '', '', '', '']
        # message
        msg[0] = self.main + ':'
        second_elapsed = time.time() - self.main_start_time
        cps = 0 if second_elapsed < 0.0001 else (self.finished + self.count) / second_elapsed
        # speed
        if cps > 1000000:
            msg[4] = ' {:.1f}M/s'.format(cps/1000000)
        elif cps > 1000:
            msg[4] = ' {:.1f}K/s'.format(cps/1000)
        elif cps > 0.05:
            msg[4] = ' {:.1f}/s'.format(cps)
        elif cps > 1e-6:
            msg[4] = ' {:.1f}s each'.format(1. / cps)
        else:
            msg[4] = ' 0.0/s'
        #
        if self.failed_count == 0:
            msg[3] = ' {:,}'.format(self.finished + self.count)
            m3Len = len(msg[3])
        else:
            msg[3] = ' {:,}/\033[1;31m{:,}\033[1;m'.format(self.finished + self.count, self.failed_count)
            m3Len = len(msg[3]) - 12
        msg[5] += ' in {}{}'.format('' if second_elapsed < 86400 else '{} days '.format(int(second_elapsed/86400)),
                time.strftime('%H:%M:%S', time.gmtime(second_elapsed)))
        # percentage / progress
        if self.totalCount:
            # percentage
            msg[1] = ' 100%'
            width = self.term_width - len(msg[0]) - len(msg[1]) - m3Len - len(msg[4]) - len(msg[5])
            if width > 4:
                front = int(width - 4)
                if self.count:
                    failed_front = int(float(self.failed_count)/self.count*front)
                else:
                    failed_front = 0
                msg[2] = ' [{}\033[1;31m{}\033[1;m]'.format('=' * (front - failed_front), '=' * failed_front)
        sys.stderr.write('\r' + ''.join(msg) + '\n')
        sys.stderr.flush()


def compressFile(infile, outfile):
    '''Compress a file from infile to outfile'''
    with open(infile, 'rb') as input, gzip.open(outfile, 'wb') as output:
            buffer = input.read(100000)
            while buffer:
                output.write(buffer)
                buffer = input.read(100000)
    return outfile

def decompressIfNeeded(filename, inplace=True):
    '''Decompress a file.gz and return file if needed'''
    if filename.lower().endswith('.gz'):
        new_filename = filename[:-3]
        if os.path.isfile(new_filename):
            return new_filename
        with gzip.open(filename, 'rb') as input, open(new_filename, 'wb') as output:
            buffer = input.read(100000)
            while buffer:
                output.write(buffer)
                buffer = input.read(100000)
        #
        if inplace:
            try:
                os.remove(filename)
            except:
                pass
        return new_filename
    else:
        return filename

#
# Well, it is not easy to do reliable download
# 
def downloadURL(URL, dest, quiet):
    # use libcurl? Recommended but not always available
    filename = os.path.split(urlparse.urlsplit(URL).path)[-1]
    try:
        import pycurl
        if not quiet:
            prog = ProgressBar(filename)
        with open(dest, 'wb') as f:
            c = pycurl.Curl()
            c.setopt(pycurl.URL, URL)
            c.setopt(pycurl.WRITEFUNCTION, f.write)
            if not quiet:
                c.setopt(pycurl.NOPROGRESS, False)
                c.setopt(pycurl.PROGRESSFUNCTION, prog.curlUpdate)
            c.perform()
        if not quiet:
            prog.done()
        if c.getinfo(pycurl.HTTP_CODE) == 404:
            try:
                os.remove(dest)
            except OSError:
                pass
            raise RuntimeError('ERROR 404: Not Found.')
        if os.path.isfile(dest):
            return dest
        else:
            raise RuntimeError('Failed to download {} using pycurl'.format(URL))
    except ImportError:
        # no pycurl module
        pass
    # use wget? Almost universally available under linux
    try:
        # for some strange reason, passing wget without shell=True can fail silently.
        p = subprocess.Popen('wget {} -O {} {}'.format('-q' if quiet else '', dest, URL), shell=True)
        ret = p.wait()
        if ret == 0 and os.path.isfile(dest):
            return dest
        else:
            try:
                os.remove(dest)
            except OSError:
                pass
            raise RuntimeError('Failed to download {} using wget'.format(URL))
    except (RuntimeError, ValueError, OSError):
        # no wget command
        pass
    
    # use python urllib?
    if not quiet:
        prog = ProgressBar(filename)
    try:
        urllib.URLopener().open(URL)
    except IOError as error_code:
        if error_code[1] == 404:
            raise RuntimeError('ERROR 404: Not Found.')
        else:
            raise RuntimeError('Unknown error has happend: {}'.format(error_code[1]))
    else:
        urllib.urlretrieve(URL, dest, reporthook=None if quiet else prog.urllibUpdate)
    if not quiet:
        prog.done()
    # all methods tried
    if os.path.isfile(dest):
        return dest
    # if all failed
    raise RuntimeError('Failed to download {}'.format(fileToGet))

def downloadFile(fileToGet, dest_dir = None, quiet = False):
    '''Download file from URL to filename.'''
    if fileToGet.startswith('http://vtools.houstonbioinformatics.org/'):
        fileToGet = fileToGet[len('http://vtools.houstonbioinformatics.org/'):]
    #
    # if a complete URL is given, local file is something like 
    #
    # ~/.variant_tools/ftp.completegenomics.com/refgenome/build36.crr
    # 
    # unless a specific dest_dir is given
    #
    if '://' in fileToGet:
        # get filename from URL
        filename = os.path.split(urlparse.urlsplit(fileToGet).path)[-1]
        local_fileToGet = fileToGet.split('://', 1)[1]
        # use root local_resource directory if dest_dir is None
        if dest_dir is not None:
            dest = os.path.join(dest_dir, filename)
        else:
            dest_dir = os.path.join(runOptions.local_resource, os.path.split(local_fileToGet)[0])
            dest = os.path.join(runOptions.local_resource, local_fileToGet)
    # 
    # otherwise, local file is like
    #
    # ~/.variant_tools/format/vcf.fmt
    #
    else:
        filename = os.path.split(fileToGet)[-1]
        local_fileToGet = fileToGet
        if dest_dir is not None:
            dest = os.path.join(dest_dir, os.path.split(filename)[-1])
        else:
            # use structured local_resource directory if dest_dir is None
            dest = os.path.join(runOptions.local_resource, fileToGet)
            dest_dir = os.path.split(dest)[0]
    #
    if not os.path.isdir(dest_dir):
        os.makedirs(dest_dir)
    # 
    # if dest already exists, return it directly
    if os.path.isfile(dest):
        return dest
    # 
    # if a URL is given, try that URL first
    if '://' in fileToGet:
        try:
            return downloadURL(fileToGet, dest, quiet)
        except:
            pass
    #
    # use a search path
    for path in runOptions.search_path.split(';'):
        if '://' not in path:
            # if path is a local directory
            source_file = '{}/{}'.format(path, local_fileToGet)
            #
            if os.path.isfile(source_file):
                shutil.copyfile(source_file, dest)
                return dest
        else:
            # is path is a URL
            URL = '{}/{}'.format(path, local_fileToGet)
            try:
                return downloadURL(URL, dest, quiet)
            except:
                continue
    # failed to get file
    raise Exception('Failed to download file {}'.format(fileToGet))


#
#
#  reference genome
#
class RefGenome:
    def __init__(self, build):
        if build in ['hg18', 'build36']:
            crrFile = downloadFile('ftp://ftp.completegenomics.com/ReferenceFiles/build36.crr')
            self.crr = CrrFile(crrFile)
        elif build in ['hg19', 'build37']:
            crrFile = downloadFile('ftp://ftp.completegenomics.com/ReferenceFiles/build37.crr')
            self.crr = CrrFile(crrFile)
        else:
            raise ValueError('Cannot find reference genome for build {}'.format(build))
        #
        self.chrIdx = {}

    def getBase(self, chr, pos):
        try:
            return self.crr.getBase(Location(self.chrIdx[chr], pos - 1))
        except KeyError:
            try:
                self.chrIdx[chr] = self.crr.getChromosomeId('chr{}'.format(chr)) 
            except ValueError:
                self.chrIdx[chr] = self.crr.getChromosomeId(str(chr))
            # ok?
            return self.crr.getBase(Location(self.chrIdx[chr], pos - 1))

    def getSequence(self, chr, start, end):
        try:
            return self.crr.getSequence(Range(self.chrIdx[chr], start - 1, end))
        except KeyError:
            try:
                self.chrIdx[chr] = self.crr.getChromosomeId('chr{}'.format(chr)) 
            except ValueError:
                self.chrIdx[chr] = self.crr.getChromosomeId(str(chr))
            # ok?
            return self.crr.getSequence(Location(self.chrIdx[chr], start - 1, end))
   
    def verify(self, chr, pos, ref):   
        try:
            if len(ref) == 1:
                return ref == self.getBase(chr, pos)
            else:
                return ref == self.getSequence(chr, pos, pos + len(ref) - 1)
        except Exception as e:
            return False
            # raise ValueError('Failed to verify variant (chr={},pos={},ref={}): {}'.format(chr, pos, ref, e))
#
#
# Database engine
#

class DatabaseEngine:
    '''variant tools can make use of two database engines. One is mysql, the
    other is sqlite3. This class wraps around their DB API and provides an
    unified interface.'''
    def __init__(self, engine='sqlite3', batch=10000, **kwargs):
        '''
        engine
            Database engine, can be mysql or sqlite3 (default)
        batch
            Number of query per transaction. Larger number usually leads to better
            performance but requires more system resource.

        Additional keyword parameters such as 'host', 'user' and 'passwd' are
        passed directly to a MySQL database engine.
        '''
        self.engine = engine
        self.batch = batch
        # saved in case a new connection is needed
        self.connectionParams = kwargs
        # not connected to any database for now
        self.dbName = None
        if self.engine == 'mysql':
            import MySQLdb
            self.PH = '%s'
            self.AI = 'AUTO_INCREMENT'
            self.database = MySQLdb.connect(host=kwargs.get('host', 'localhost'),
                user=kwargs.get('user', getpass.getuser()),
                passwd=kwargs.get('passwd'))
        else:
            self.PH = '?'
            self.AI = 'AUTOINCREMENT'
            self.database = None

    
    def describeEngine(self):
        if self.engine == 'mysql':
            return 'mysql'
        elif runOptions.sqlite_pragma == []:
            return 'sqlite (no pragma)'
        else:
            return 'sqlite (with pragma {})'.format(', '.join(runOptions.sqlite_pragma))
    #
    # Connection
    #
    def newConnection(self):
        '''Create a new connection from existing configuration'''
        return DatabaseEngine(engine=self.engine, batch=self.batch,
            **self.connectionParams)
        
    def connect(self, db, readonly=False, lock=None):
        '''Connect to a database'''
        if self.engine == 'mysql':
            if '.' in db or os.sep in db:
                raise ValueError('Invalid database name: {}'.format(db))
            self.dbName = db
            cur = self.database.cursor()
            if not self.hasDatabase(self.dbName):
                cur.execute('CREATE DATABASE {};'.format(self.dbName))
            cur.execute('USE {};'.format(self.dbName))
        else:
            db = os.path.expanduser(db)
            self.dbName = db if (db.endswith('.proj') or db.endswith('.DB')) else db + '.DB'
            self.database = sqlite3.connect(self.dbName, check_same_thread=not readonly)
            self.database.enable_load_extension(True)
            #
            # We disable PROGAMA for readonly databases because we often use mutliple readers
            # to read from a readonly database, and applying PRAGMA might cause Operationalerror.
            # We may need to reconsider this though because some pragma applies to 
            # readonly databases (e.g. cache_size)
            if readonly:
                return
            if lock is not None:
                lock.acquire()
            cur = self.database.cursor()
            for pragma in runOptions.sqlite_pragma:
                # if a pragma is only applicable to certain database, check its name
                if '.' in pragma.split('=')[0] and pragma.split('.', 1)[0] != self.dbName:
                    continue
                # No error message will be produced for wrong pragma
                # but we may have syntax error.
                try:
                    cur.execute('PRAGMA {}'.format(pragma))
                except Exception as e:
                    # I cannot raise an error because uers need to open the project to reset this value.
                    sys.stderr.write('Failed to set pragma "{}". Use "vtools admin --set_runtime_option sqlite_pragma=PRAGMA1=VAL,PRAGMA2=VAL" to reset pragmas: {}\n'.format(pragma, e))
                #
                self.database.commit()
            # trying to load extension
            for path in sys.path:
                ext = glob.glob(os.path.join(path, '_vt_sqlite3_ext.*'))
                if ext:
                    cur = self.database.cursor()
                    try:
                        cur.execute('SELECT load_extension("{}");'.format(ext[0]))
                    except Exception as e:
                        raise SystemError('Failed to load variant tools sqlite extension from {}: {}'.format(ext[0], e))
                    break
                ext = glob.glob(os.path.join(path, 'variant_tools', '_vt_sqlite3_ext.*'))
                if ext:
                    cur = self.database.cursor()
                    try:
                        cur.execute('SELECT load_extension("{}");'.format(ext[0]))
                    except Exception as e:
                        raise SystemError('Failed to load variant tools sqlite extension from {}: {}'.format(ext[0], e))
                    break
            if lock is not None:
                lock.release()


    def close(self):
        if self.engine == 'mysql':
            # do not know what to do
            pass
        else:
            self.database.close()

    def attach(self, db, name=None, lock=None):
        '''Attach another database to this one. Only needed by sqlite'''
        if self.engine == 'mysql':
            # create the database if needed
            if not self.hasDatabase(db):
                self.execute('CREATE DATABASE {};'.format(db))
            return db
        if db.endswith('.DB') or db.endswith('.proj'):
            db = os.path.expanduser(db)
            dbName = name if name else os.path.split(db)[-1].split('.')[0].split('-')[0]
            if lock is not None:
                lock.acquire()
            self.execute('''ATTACH DATABASE '{0}' as {1};'''.format(
                db, dbName))
            for pragma in runOptions.sqlite_pragma:
                if '.' in pragma and pragma.split('.', 1)[0] != dbName:
                    # if pragma is for a specific table with another name, ignore
                    pass
                #
                try:
                    self.execute('PRAGMA {}.{}'.format(dbName, pragma))
                except:
                    pass
            if lock is not None:
                lock.release()
            return dbName
        else:
            db = os.path.expanduser(db)
            dbName = name if name else os.path.split(db)[-1].split('.')[0].split('-')[0]
            if lock is not None:
                lock.acquire()
            self.execute('''ATTACH DATABASE '{0}' as {1};'''.format(
                db + '.DB' if db != ':memory:' else db, dbName))
            for pragma in runOptions.sqlite_pragma:
                # database specific pragma
                if '.' in pragma.split('=')[0]:
                    # pragma for another database
                    if pragma.split('.', 1)[0] != dbName:
                        # if pragma is for a specific table with another name, ignore
                        continue
                    else:
                        # execute it
                        try:
                            self.execute('PRAGMA {}'.format(pragma))
                        except:
                            pass
                else:
                    # apply general pragma to the attached database
                    try:
                        self.execute('PRAGMA {}.{}'.format(dbName, pragma))
                    except:
                        pass
            if lock is not None:
                lock.release()
            return dbName

    def detach(self, db):
        '''Detach a database'''
        if self.engine == 'mysql':
            return
        else:
            self.execute('''DETACH {}'''.format(db))

    def analyze(self):
        '''Analyze a database for better performance'''
        if self.engine == 'mysql':
            return
        else:
            self.execute('analyze;')

    #
    # query
    #
    def execute(self, *args, **kwargs):
        '''A shortcut to get cursor, execute and commit.'''
        cur = self.database.cursor()
        cur.execute(*args, **kwargs)
        return self.database.commit()

    def cursor(self):
        return self.database.cursor()

    def commit(self):
        return self.database.commit()

    #
    # Database
    #
    def hasDatabase(self, db):
        '''Test if a database exists in the current connection'''
        if self.engine == 'mysql':
            cur = self.database.cursor()
            cur.execute('SHOW DATABASES;')
            return db.lower() in [x[0].lower() for x in cur.fetchall()]
        else:
            db = os.path.expanduser(db)
            return os.path.isfile(db if (db.endswith('.DB') or db.endswith('.proj')) else db + '.DB')

    def removeDatabase(self, db):
        if self.engine == 'mysql':
            cur = self.database.cursor()
            if self.hasDatabase(db):
                cur.execute('DROP DATABASE {};'.format(db))
            self.database.commit()
        else:
            # has to have file extension
            dbFile = db if (db.endswith('.proj') or db.endswith('.DB')) else db + '.DB'
            try:
                os.remove(dbFile)
            except:
                pass
            if os.path.isfile(dbFile):
                sys.exit('Failed to remove database {}'.format(db))

    #
    # Table
    #
    def tables(self, dbName=None):
        '''List all tables in a database'''
        cur = self.database.cursor()
        try:
            if self.engine == 'mysql':
                if dbName is None:
                    cur.execute("SHOW TABLES;")
                    return [x[0] for x in cur.fetchall()]
                else:
                    cur.execute("SHOW TABLES IN {};".format(dbName))
                    return [x[0] for x in cur.fetchall()]
            else:
                if dbName is None:
                    cur.execute("SELECT name FROM sqlite_master WHERE type='table' UNION ALL SELECT name FROM sqlite_temp_master WHERE type='table';")
                    return [x[0] for x in cur.fetchall() if not x[0].startswith('sqlite')]
                else:
                    cur.execute("SELECT name FROM {0}.sqlite_master WHERE type='table' UNION ALL SELECT name FROM sqlite_temp_master WHERE type='table';".format(dbName))
                    return [x[0] for x in cur.fetchall() if not x[0].startswith('sqlite')]
        except:
            return []

    def hasTable(self, table):
        '''Test if a table exists in the current database '''
        if '.' not in table:
            return table.lower() in [x.lower() for x in self.tables()]
        else:
            dbName, tableName = table.split('.', 1)
            return tableName.lower() in [x.lower() for x in self.tables(dbName)]

    def hasIndex(self, index):
        '''Test if an index exists in the current database '''
        cur = self.database.cursor()
        if self.engine == 'mysql':
            cur.execute("SHOW INDEXES;")
            return index.lower() in [x[0].lower() for x in cur.fetchall()]
        elif '.' in index:
            db, idx = index.split('.', 1)
            cur.execute("SELECT count(name) FROM {}.sqlite_master WHERE type='index' AND name={};".format(db, self.PH), (idx,))
            return cur.fetchone()[0] > 0
        else:
            cur.execute("SELECT count(name) FROM sqlite_master WHERE type='index' AND name={0} UNION ALL SELECT name FROM sqlite_temp_master WHERE type='index' AND name={0};".format(self.PH), (index,index))
            return cur.fetchone()[0] > 0

    def dropIndex(self, index, table):
        if self.engine == 'mysql':
            self.execute('DROP INDEX {} ON {};'.format(index, table))
        else:
            self.execute('DROP INDEX {};'.format(index))

    def removeTable(self, table):
        '''Remove specified table'''
        cur = self.database.cursor()
        cur.execute('DROP TABLE {};'.format(table))
        # FIXME: should we automatically do VACUUM, this can be slow when the table is deletec
        # but can help performance for the creation of new tables.
        #if self.engine == 'sqlite3':
        # NOTE: It seems that re-generating a table can be VERY slow without vacuum.
        #    cur.execute('VACUUM;')
        self.database.commit()

    def truncateTable(self, table):
        '''Clear all record in a table'''
        cur = self.database.cursor()
        cur.execute('DELETE FROM {};'.format(table))
        self.database.commit()
    
    def renameTable(self, fromTable, toTable):
        '''Rename a table from fromTable to toTable'''
        cur = self.database.cursor()
        cur.execute('ALTER TABLE {} RENAME TO {};'.format(fromTable, toTable))
        self.database.commit()
        
    def backupTable(self, table):
        '''Backup a table to table_timestamp'''
        while True:
            new_table = '{}_{}'.format(table, time.strftime('%b%d_%H%M%S', time.gmtime()))
            if not self.hasTable(new_table):
                self.renameTable(table, new_table)
                return new_table
            time.sleep(1)

    def fieldsOfTable(self, table):
        '''Get the name and type of fields in a table'''
        cur = self.database.cursor()
        if self.engine == 'mysql':
            # FIXME: not tested
            cur.execute('SHOW COLUMNS FROM {};'.format(table))
            return cur.fetchall()
        else:
            if '.' not in table:
                cur.execute('SELECT sql FROM sqlite_master WHERE UPPER(name) = "{}";'.format(table.upper()))
            else:
                db, tbl = table.rsplit('.', 1)
                cur.execute('SELECT sql FROM {}.sqlite_master WHERE UPPER(name) = "{}";'.format(db, tbl.upper()))
            try:
                schema = cur.fetchone()[0]
            except:
                raise ValueError('Could not get schema of table {}'.format(table))
            fields = [x.strip() for x in schema.split(',')]
            fields[0] = fields[0].split('(')[1].strip()
            fields[-1] = fields[-1].rsplit(')', 1)[0].strip()
            return [x.split(None, 1) for x in fields]

    def removeFields(self, table, cols):
        '''Remove fields from a table'''
        if len(cols) == 0:
            return
        cur = self.database.cursor()
        if self.engine == 'mysql':
            cur.execute('ALTER TABLE {} {};'.format(table,
                ', '.join(['DROP COLUMN {}'.format(x) for x in cols])))
        elif '.' not in table:
            # for my sqlite, we have to create a new table
            fields = self.fieldsOfTable(table)
            new_fields = ['{} {}'.format(x,y) for x,y in fields if x.lower() not in [z.lower() for z in cols]]
            if len(fields) == len(new_fields):
                raise ValueError('No field could be removed from table {}'.format(table))
            # rename existing table
            cur.execute('ALTER TABLE {0} RENAME TO _{0}_tmp_;'.format(table))
            # create a new table
            cur.execute('CREATE TABLE {} ('.format(table) + ',\n'.join(new_fields) + ');')
            # insert data back
            cur.execute('INSERT INTO {0} SELECT {1} FROM _{0}_tmp_;'.format(table, 
                ','.join([x.split()[0] for x in new_fields])))
            # remove old table
            cur.execute('DROP TABLE _{}_tmp_;'.format(table))
        else:
            db, tbl = table.rsplit('.', 1)
            fields = self.fieldsOfTable(table)
            new_fields = ['{} {}'.format(x,y) for x,y in fields if x.lower() not in [z.lower() for z in cols]]
            if len(fields) == len(new_fields):
                raise ValueError('No field could be removed from table {}'.format(table))
            # rename existing table
            cur.execute('ALTER TABLE {1}.{0} RENAME TO _{0}_tmp_;'.format(tbl, db))
            # create a new table
            cur.execute('CREATE TABLE {1}.{0} ('.format(tbl, db) + ',\n'.join(new_fields) + ');')
            # insert data back
            cur.execute('INSERT INTO {2}.{0} SELECT {1} FROM {2}._{0}_tmp_;'.format(tbl, 
                ','.join([x.split()[0] for x in new_fields]), db))
            # remove old table
            cur.execute('DROP TABLE {1}._{0}_tmp_;'.format(tbl, db))

    def typeOfColumn(self, table, col):
        '''Return type of col in table'''
        fields = self.fieldsOfTable(table)
        for n, t in fields:
            if n.lower() == col.lower():
                return t
        raise ValueError('No column called {} in table {}'.format(col, table))


    def numOfRows(self, table, exact=True):
        cur = self.database.cursor()
        if not exact and self.engine == 'sqlite3':
            # this is much faster if we do not need exact count
            if '.' in table:
                db, tbl = table.rsplit('.', 1)
                cur.execute('SELECT seq FROM {}.sqlite_sequence WHERE name = {};'.format(db, self.PH), (tbl,))
            else:
                cur.execute('SELECT seq FROM sqlite_sequence WHERE name = {};'.format(self.PH), (table,))
            res = cur.fetchone()
            if res is not None:
                return res[0]
        cur.execute('SELECT count(*) FROM {};'.format(table))
        return cur.fetchone()[0]

    def startProgress(self, text):
        if self.engine == 'mysql':
            return
        self.prog = ProgressBar(text)
        self.database.set_progress_handler(self.prog.sqliteUpdate, self.batch)

    def stopProgress(self):
        if self.engine == 'mysql':
            return
        self.prog.done()
        self.database.set_progress_handler(None, self.batch)

    def getHeaders(self, table):
        '''Obtain field names of a table'''
        cur = self.database.cursor()
        try:
            if self.engine == 'mysql':
                cur.execute('SELECT column_name FROM information_schema.columns WHERE table_name={};'.format(self.PH),
                    table)
                return [x[0] for x in cur.fetchall()]
            else:
                cur.execute('SELECT * FROM {} LIMIT 1;'.format(table))
                return [x[0] for x in cur.description]
        except:
            return None

import token

def consolidateFieldName(proj, table, clause, alt_build=False):
    '''For input sift_score > 0.5, this function expand it to
    dbNSFP.sift_score > 0.5 and return a list of fields (dbNSFP.sift_score
    in this case). It also change pos to alt_pos if alt_build is true.
    We are using a Python tokenizer here so the result might be wrong.
    '''
    tokens = [x for x in tokenize.generate_tokens(cStringIO.StringIO(clause).readline)]
    res = []
    fields = []
    for i in range(len(tokens)):
        before_dot = (i + 1 != len(tokens)) and tokens[i+1][1] == '.'
        after_dot = i > 1 and tokens[i-1][1] == '.'
        #
        toktype, toval, _, _, _ = tokens[i]
        # replace chr by alt_chr if using an alternative reference genome.
        if alt_build and toval in ['chr', 'pos'] and not before_dot:
            toval = 'alt_' + toval
        #
        if toktype == token.NAME and toval.upper() not in SQL_KEYWORDS:
            if before_dot:
                # A.B, does not try to expand A
                res.append((toktype, toval))
            elif after_dot:
                # A.B, do not expand
                res.append((toktype, toval))
                # try to get fields:
                try:
                    for info in proj.linkFieldToTable('{}.{}'.format(tokens[i-2][1], toval), table):
                        fields.append(info.field)
                except ValueError as e:
                    proj.logger.debug(e)
            else:
                # A: try to expand A and identify fields
                try:
                    for info in proj.linkFieldToTable(toval, table):
                        fields.append(info.field)
                    # use expanded field, ONLY the last one should have the expanded fieldname
                    res.append((toktype, info.field))
                except ValueError as e:
                    proj.logger.debug(e)
                    res.append((toktype, toval))
        else:
            # fasttrack for symbols or function names
            res.append((toktype, toval))
    # a quick fix for a.b parsed to a .b. :-(
    return tokenize.untokenize(res).replace(' .', '.'), fields

def extractField(field):
    '''Extract pos from strings such as pos + 100'''
    if field.isalnum():
        return field
    tokens = [x for x in tokenize.generate_tokens(cStringIO.StringIO(field).readline)]
    for i in range(len(tokens)):
        toktype, toval, _, _, _ = tokens[i]
        if toktype == 1:
            return toval
    raise ValueError('Invalid field name: {}'.format(field))

#
# Utility function to calculate bins.
#
# This function implements a hashing scheme that UCSC uses (developed by Jim Kent) to 
# take in a genomic coordinate range and return a set of genomic "bins" that your range
# intersects.  I found a Java implementation on-line (I need to find the URL) and I
# simply manually converted the Java code into Python code.  
    
# IMPORTANT: Because this is UCSC code the start coordinates are 0-based and the end 
# coordinates are 1-based!!!!!!
        
# BINRANGE_MAXEND_512M = 512 * 1024 * 1024
# binOffsetOldToExtended = 4681; #  (4096 + 512 + 64 + 8 + 1 + 0)

_BINOFFSETS = (
    512+64+8+1,   # = 585, min val for level 0 bins (128kb binsize)    
    64+8+1,       # =  73, min val for level 1 bins (1Mb binsize) 
    8+1,          # =   9, min val for level 2 bins (8Mb binsize)  
    1,            # =   1, min val for level 3 bins (64Mb binsize)  
    0)            # =   0, only val for level 4 bin (512Mb binsize)
     
#    1:   0000 0000 0000 0001    1<<0       
#    8:   0000 0000 0000 1000    1<<3
#   64:   0000 0000 0100 0000    1<<6
#  512:   0000 0010 0000 0000    1<<9
 
_BINFIRSTSHIFT = 17;            # How much to shift to get to finest bin.
_BINNEXTSHIFT = 3;              # How much to shift to get to next larger bin.
_BINLEVELS = len(_BINOFFSETS)
  
#
# IMPORTANT: the start coordinate is 0-based and the end coordinate is 1-based.
#
def getUcscBins(start, end):
    bins = []
    startBin = start >> _BINFIRSTSHIFT
    endBin = (end-1) >> _BINFIRSTSHIFT
    for i in range(_BINLEVELS):
        offset = _BINOFFSETS[i];
        if startBin == endBin:
            bins.append(startBin + offset)
        else:
            for bin in range(startBin + offset, endBin + offset):
                bins.append(bin);
        startBin >>= _BINNEXTSHIFT
        endBin >>= _BINNEXTSHIFT
    return bins

def getMaxUcscBin(start, end):
    bin = 0
    startBin = start >> _BINFIRSTSHIFT
    endBin = (end-1) >> _BINFIRSTSHIFT
    for i in range(_BINLEVELS):
        offset = _BINOFFSETS[i];
        if startBin == endBin:
            if startBin + offset > bin:
                bin = startBin + offset
        else:
            for i in range(startBin + offset, endBin + offset):
                if i > bin:
                    bin = i 
        startBin >>= _BINNEXTSHIFT
        endBin >>= _BINNEXTSHIFT
    return bin


def normalizeVariant(pos, ref, alt):
    '''Normailize variants in different formats into a standard
    format that variant tool accepts. This function returns a tuple
    with UCSC bin, pos, ref, alt
    '''
    # this is usually the case but some badly formatted
    # vcf file use small case for variants
    try:
        ref = ref.upper()
        alt = alt.upper()
    except Exception as e:
        raise ValueError('Invalid reference ({}) or alternative ({}) allele.'.format(ref, alt))
    # different types of variants
    # 1. C -> G  (SNV)  
    #    TC-> TG  
    # 2. TC -> T (deletion)
    #    TCG -> TG
    #    TCG -> T
    #    TCGCG -> TCG
    # 3. TC -> TCA (insertion)
    #    TCG -> TCAG
    #    C -> CTAG
    #    TCGCG -> TCGCGCG
    # 4. Complex:
    #    AA -> ATAAC
    #    TACT -> TCTA
    #    (as shown in 1000g vcf files)
    #
    if len(ref) > 1 or len(alt) > 1:
        # STEP 1: remove leading common string
        # 1. C -> G  (SNV)  
        #    C -> G  
        # 2. C -> '' (deletion)
        #    CG -> G
        #    CG -> ''
        #    CG -> ''
        # 3. '' -> A (insertion)
        #    G -> AG
        #    '' -> TAG
        #    '' -> CG
        common_leading = 0
        for i in range(min(len(ref), len(alt))):
            if ref[i] == alt[i]:
                common_leading += 1
            else:
                break
        if common_leading > 0:
            if pos:
                pos += common_leading
            ref = ref[common_leading:]
            alt = alt[common_leading:]
        #
        # STEP 2: remove ending common string
        # now insertion should have empty ref, deletion should have empty alt
        common_ending = 0
        for i in range(-1, - min(len(ref), len(alt)) - 1, -1):
            if ref[i] == alt[i]:
                common_ending -= 1
            else:
                break
        if common_ending < 0:
            ref = ref[:common_ending]
            alt = alt[:common_ending]
    #
    # ref or alt is something like '', '-', '.' or '*'
    if not alt.isalpha():
        if not ref.isalpha():
            raise ValueError('Invalid reference and alternative alleles: {}, {}'.format(ref, alt))
        alt = '-'
    elif not ref.isalpha():
        ref = '-'
    bin = getMaxUcscBin(pos - 1, pos) if pos else None
    return bin, pos, ref, alt


def executeUntilSucceed(cur, query, logger, attempts, operation_msg, data = None):
    '''try to execute queries a few times before it fails'''
    for attempt in range(attempts):
        try:
            if data:
                cur.execute(query, data)
            else:
                cur.execute(query)
            if attempt != 0:
                logger.debug('Operation "' + operation_msg + '" succeeded after {} attempts'.format(attempt + 1))
            break
        except:
            if attempt == attempts - 1:
                logger.error('Operation "' + operation_msg + '" failed after {} attempts'.format(attempt + 1))
                raise
            else:
                time.sleep(1 + attempt + random.random() * 10)