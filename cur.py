#!/usr/bin/env python

"""
Lyle Scott, III
lyle@digitalfoo.net

A simple demo that uses curses to scroll the terminal.
TODO:
    not reset when switch to artist view
    if have never played song before, then tracks wont appear...
    not exception when resize in tmux?
    o -> goto current playing
    wrap around
"""
import curses
import sys
import subprocess
import re
import logging
import os
from mpd import MPDClient
from collections import OrderedDict


fname = '/home/kstock/workspace/mu/foo.log'
logging.basicConfig(filename=fname,level=logging.DEBUG)
logger = logging.getLogger(fname)
# Configure logger to write to a file...

def my_handler(typ, value, tb):
    '''force all uncaught exceptions go to logger'''
    logger.exception("Uncaught exception: {0}".format(str(value)))

# Install exception handler
sys.excepthook = my_handler


def extract(regex,line,default=''):
    ''' extract first match of regex in line, else give default value'''
    txt = regex.findall(line)
    if txt:#found
        return txt[0]
    else:
        return default

def choice_of_options(prompt,choices = ('y','n') ):
    '''abstracts looping until correct user input'''
    choices = map(str,choices)
    guess = raw_input(prompt)
    while guess not in choices:
        print "you must give an answer in %s " % str(choices)
        guess = raw_input(prompt)

    return guess

class LastUpdatedOrderedDict(OrderedDict):
    '''Stores items in the order the keys were last added,used to maintain a changelist'''

    def __setitem__(self, key, value):
        if key in self:
            del self[key]
        OrderedDict.__setitem__(self, key, value)

class MenuDemo(object):
    '''Creates a menu where you can alter mpdcron ratings '''

    #constants
    DOWN        = 1
    UP          = -1

    ALBUM_INDEX = 0

    #key constants
    SPACE_KEY   = 32
    ESC_KEY     = 27
    ENTER       = curses.KEY_ENTER

    TO_TOP        = ord('g')
    TO_BOTTOM     = ord('G')
    DEBUG         = ord('d')
    DEBUG_EVERY   = ord('D')
    RESET         = ord('r')
    RESET_AND_QUIT= ord('R')
    UNDO          = ord('u')
    ARTIST_TOGGLE = ord('A')

    DOWN_KEYS     = [curses.KEY_DOWN,ord('j')]
    UP_KEYS       = [curses.KEY_UP,ord('k')]
    QUIT_KEYS     = [ESC_KEY,ord('q')]
    FORCE_QUIT    = ord('Q')#do not prompt user to validate any modifications

    ALLOWED_INPUT = [ord(str(n)) for n in range(0,10)]
    ALLOWED_INPUT.append( curses.KEY_BACKSPACE )

    SEP = '|'
    RATING_PREFIX = 'Rating:'
    DEFAULT_RATING = '__'



    outputLines = []
    screen = None

    r_title       = re.compile(r'Last_Played.*? (.*)')
    r_album_title = re.compile(r'Rating:[0-9]+ (.*)')
    r_title_unplayed = re.compile(r'Karma:[0-9]+ (.*)')

    r_rating      = re.compile(r'Rating:([0-9]+)')
    r_play_count  = re.compile(r'Play_Count:([0-9]+)')

    def __init__(self):

        #the modified (dirty) songs,a dict ordered by modification date so undo will work
        self.dirty              = LastUpdatedOrderedDict()
        self.original           = {}#original ratings,saved so we can know if a file is dirty
        self.filename_id        = {}#bidirectional dict of id -> filename, filename -> id
        self.mark_dict          = {}#current
        self.non_editable_lines = set()
        self.rate_album         = True#False means rate all Artist

        self.screen = curses.initscr()

        curses.start_color()
        curses.use_default_colors()
        #start_color() initializes eight basic colors
        #(black, red, green, yellow, blue, magenta, cyan, and white)
        for i in range(0, curses.COLORS):
            curses.init_pair(i, i, -1)


        self.default_color                = curses.color_pair( curses.COLOR_BLACK )
        self.highlight_color              = curses.color_pair( curses.COLOR_BLUE )
        self.current_song_color           = curses.color_pair( curses.COLOR_GREEN )
        self.dirty_color                  = curses.color_pair( curses.COLOR_RED )
        self.current_song_highlight_color = curses.color_pair( curses.COLOR_YELLOW )

        curses.noecho()
        curses.cbreak()
        self.screen.keypad(1)
        self.screen.border(0)
        self.getOutputLines()
        self.current_song = self.get_current_song()
        #self.topLineNum       = max(self.current_song - curses.LINES+ 3,0)
        #self.highlightLineNum = self.current_song
        self.topLineNum       = 0
        self.highlightLineNum = 0
        self.undo_list = LastUpdatedOrderedDict()

    def run(self):
        ''' interact with menu, in the end it returns the modified indexes w ratings'''
        running = True
        force   = False
        while running:
            self.displayScreen()
            # get user command
            c = self.screen.getch()

            if c == self.FORCE_QUIT:#quit and force all changes without user check
                force   = True
                running = False
                continue
            elif c in self.QUIT_KEYS:
                running = False
                continue

            #edit ratings
            if c == curses.KEY_BACKSPACE:
                self.markLine(c)
            elif c in  self.ALLOWED_INPUT:
                self.markLine(c)
            #motion up down
            elif c in self.UP_KEYS:
                self.updown(self.UP)
            elif c in self.DOWN_KEYS:
                self.updown(self.DOWN)
            #motion long ways
            elif c == self.TO_TOP:
                self.to_index(0)
            elif c == self.TO_BOTTOM:
                self.topLineNum       = self.nOutputLines - curses.LINES
                self.nextLineNum      = curses.LINES
                self.highlightLineNum = curses.LINES - 1
            #misc
            elif c == self.DEBUG:
                self.debug_print()
            elif c == self.DEBUG_EVERY:
                self.debug_print(every=True)
            elif c == self.RESET:
                self.reset()
            elif c == self.RESET_AND_QUIT:
                self.reset()
                running = False
            elif c == self.UNDO:
                self.undo()
            elif c == self.ARTIST_TOGGLE:
                self.rate_album = not self.rate_album
                self.getOutputLines(self.rate_album)

        mods = self.do_modifications()
        return mods,force

    def reset(self):
        ''' undo all changes '''
        #reset everything then get lines, in case we have a new album
        self.dirty              = LastUpdatedOrderedDict()
        self.original           = {}#original ratings,saved so we can know if a file is dirty
        self.filename_id        = {}#bidirectional dict of id -> filename, filename -> id
        self.mark_dict          = {}#current
        self.non_editable_lines = set()
        self.rate_album         = True#False means rate all Artist
        self.getOutputLines()
        self.current_song = self.get_current_song()

    def undo(self):
        ''' undoes last rating modification'''
        if self.dirty:
            linenum,_ = self.dirty.popitem()
            self.mark_dict.pop(linenum,None)
            if linenum in self.original:#keep synced for stats
                self.mark_dict[linenum] = self.original[linenum]


    def debug_print(self,every=False):
        ''' log a bunch of debug info on various vars'''
        logging.debug(' self.non_editable_lines: % s' %  str(self.non_editable_lines )  )
        logging.debug(' self.current_song:              % s' %  str(self.current_song              )  )
        if every:
            logging.debug(' self.filename_id:        % s' %  str(self.filename_id        )  )
        logging.debug(' self.original:           % s' %  str(self.original           )  )
        logging.debug(' self.mark_dict:          % s' %  str(self.mark_dict          )  )
        logging.debug(' self.dirty:              % s' %  str(self.dirty              )  )

    def markLine(self,c):
        linenum = self.topLineNum + self.highlightLineNum

        if linenum in self.non_editable_lines:
            return

        if c in self.ALLOWED_INPUT:# and self.edit_mode:
            mark  = self.mark_dict.get(linenum,'')
            if c == curses.KEY_BACKSPACE:# and not mark:
                self.mark_dict.pop(linenum,None)
                if linenum in self.original:#keep synced for stats
                    self.mark_dict[linenum] = self.original[linenum]
                self.dirty.pop(linenum,None)
            else:
                #cast to strip 0, prevent edge case where "01" -> "010" happens
                mark = int( mark + chr(c) )
                if mark > 10:
                    mark = chr(c)
                mark = str(mark)

                self.mark_dict[linenum] = mark
                if mark != self.original.get(linenum,'doest match'):
                    self.dirty[linenum] = mark
                else:
                    self.dirty.pop(linenum,None)
                logging.debug(self.dirty)


    def getOutputLines(self,rate_album=True):
        '''Get the list of songs to potentially edit. if rate_album then get album song, else get all artists songs  '''
        self.outputLines = []
        if rate_album:
            query = subprocess.check_output('''mpc -f 'artist="%artist%" and album="%album%"' current''',shell=True)
        else:
            query = subprocess.check_output('''mpc -f 'artist="%artist%"' current''',shell=True)
        logging.critical(query)
        self.outputLines.extend( subprocess.check_output("eugene listinfo '" + query.strip() + "'", shell=True).split('\n') )

        #add 2 for offset from album name, separator line
        self.outputLines = [ l for l  in self.outputLines if l]
        self.outputLines = [ self.process_line(l,i+2) for i,l in enumerate(self.outputLines)]

        self.outputLines.insert(0,'--------------------------------')#line 1
        self.non_editable_lines.add(1)

        #album
        l = self.process_line( subprocess.check_output('eugene listinfo -A',shell=True).strip(), self.ALBUM_INDEX,r_title=self.r_album_title)
        self.outputLines.insert(self.ALBUM_INDEX, l)

        self.nOutputLines = len(self.outputLines)
        logging.debug( 'num output lines = %s' % self.nOutputLines)


    def displayScreen(self):
        # clear screen
        self.screen.erase()

        # now paint the rows
        top = self.topLineNum
        bottom = self.topLineNum+curses.LINES
        for (index,line,) in enumerate(self.outputLines[top:bottom]):
            linenum          = self.topLineNum + index
            start_char_index = 0

            if linenum in self.non_editable_lines:
                if index == self.highlightLineNum:
                    self.screen.addstr(index, start_char_index, line, curses.color_pair(curses.COLOR_CYAN) )
                else:
                    self.screen.addstr(index, start_char_index, line)
                continue

            #Decide on colors,first set defaults
            rating_prefix_color = curses.color_pair( curses.COLOR_BLACK )
            rating_color        = self.default_color
            line_color          = self.default_color

            if linenum == self.current_song and index == self.highlightLineNum:
                line_color = rating_color = rating_prefix_color = self.current_song_highlight_color
            elif linenum == self.highlightLineNum:
                line_color = rating_color = rating_prefix_color = self.highlight_color
            elif linenum == self.current_song:
                line_color = rating_color = rating_prefix_color = self.current_song_color

            if linenum in self.dirty:
                rating_color = self.dirty_color


            #add ratings in pieces
            self.screen.addstr(index, start_char_index, self.RATING_PREFIX,rating_prefix_color)
            start_char_index += len(self.RATING_PREFIX)

            rating     = self.get_rating(linenum) or self.DEFAULT_RATING
            self.screen.addstr(index, start_char_index, rating + self.SEP,rating_color)
            start_char_index += len(rating) + len(self.SEP)


            if linenum == self.ALBUM_INDEX:
                line = self.add_stats(line)


            self.screen.addstr(index, start_char_index, line, line_color )

            #logging.debug('index %s, line: %s' % (index, line))
            # highlight current line
            #if index == self.highlightLineNum:
                #self.screen.addstr(index, 0,  self.RATING_PREFIX, highlight_color )
                #self.screen.addstr(index, start_char_index, line, highlight_color )
                #if linenum not in self.dirty:
                    #self.screen.addstr(index, len(self.RATING_PREFIX), rating + self.SEP, highlight_color )
            #elif linenum == self.current_song:#non-dirty numbers get highlighted,dirty ones don't
                #self.screen.addstr(index, start_char_index, line, curses.color_pair(curses.COLOR_GREEN) )
            #else:
                #self.screen.addstr(index, start_char_index, line)

            start_char_index += len(line)
            if linenum in self.dirty:
                dirt = '|dirty(%s)' % self.original.get(linenum,0)
                self.screen.addstr(index, start_char_index, dirt, curses.color_pair(curses.COLOR_RED) )#| curses.A_BOLD)

        self.screen.refresh()

    def to_index(self,i):
        self.topLineNum       = i
        self.highlightLineNum = i

    # move highlight up/down one line
    def updown(self, increment):
        nextLineNum = self.highlightLineNum + increment
        logging.debug( '--nextLineNum %s ,self.highlightLineNum %s ,self.topLineNum %s, curses.LINES %s, numLines %s --'% ( nextLineNum , self.highlightLineNum , self.topLineNum , curses.LINES,self.nOutputLines))

        # paging
        if increment == self.UP and self.highlightLineNum == 0 and self.topLineNum != 0:
            self.topLineNum += self.UP
            #self.topLineNum = self.topLineNum % self.nOutputLines
            return
        elif increment == self.DOWN and nextLineNum == curses.LINES and (self.topLineNum+curses.LINES) != self.nOutputLines:
            self.topLineNum += self.DOWN
            #self.topLineNum = self.topLineNum % self.nOutputLines
            return

        logging.debug( (increment == self.DOWN,(self.topLineNum+self.highlightLineNum+1 )!= self.nOutputLines , self.highlightLineNum != curses.LINES))
        # scroll highlight line
        if increment == self.UP and (self.topLineNum != 0 or self.highlightLineNum != 0):
            self.highlightLineNum = nextLineNum
        elif increment == self.DOWN and (self.topLineNum+self.highlightLineNum+1) != self.nOutputLines and self.highlightLineNum != curses.LINES:
            self.highlightLineNum = nextLineNum

    def restoreScreen(self):
        curses.initscr()
        curses.nocbreak()
        curses.echo()
        curses.endwin()

    # catch any weird termination situations
    def __del__(self):
        self.restoreScreen()

    def get_rating(self,linenum):
        ''' gets formatted rating for song in line'''

        prefix = None
        if linenum in self.mark_dict:
            prefix = self.mark_dict.get(linenum)
            prefix = prefix.zfill(2)
        elif linenum in self.original:
            prefix = self.original[linenum].zfill(2)

        return prefix

    def prefix_rating(self,line,linenum):
        ''' gets formatted rating for song in line'''

        prefix = ''
        if linenum in self.mark_dict:
            prefix = self.mark_dict.get(linenum)
            prefix = 'Rating:' + prefix.zfill(2) + '|'
        elif linenum in self.original:
            prefix = 'Rating:' + self.original[linenum].zfill(2) + '|'
        else:
            prefix = self.RATING_PREFIX
            #prefix = str(linenum) + '|' + str(self.original)
            #prefix = str(linenum in self.original)
            #prefix = str(self.markedLineNums) + str(self.mark_dict)
            #prefix += self.original.get(linenum,'0').zfill(2) + '|'

        return prefix + line


    def add_stats(self,line):
        ''' add average current rating and such'''
        scores = sorted([int(x) for x in self.mark_dict.values() if x])

        #don't want this to pollute calculations!!
        album_rating =  self.mark_dict.get(self.ALBUM_INDEX)
        #logging.debug(album_rating)
        if album_rating:
            scores.remove( int(album_rating))

        #logging.debug(scores)
        if not scores:
            return line
        else:
            avg = str(reduce(lambda x,y:x+y,scores,0)/ float(len(scores)))[:4].zfill(2)
        line += self.SEP + 'avg:' + avg

        line += self.SEP + 'median:' + str( scores[ len(scores) // 2 ] )

        line += self.SEP + 'num>5:' + str( len([s for s in scores if s > 5]) )

        line += self.SEP + 'max:' + str( max(scores))

        return line

    def get_current_song(self):

        query = "eugene listinfo"
        line  = subprocess.check_output(query,shell=True)
        logger.debug(line)

        #if track not played wont have last played, will look like album line
        #TODO put in function
        title = extract(self.r_title,line,'')
        logger.debug(title)
        if not title or self.r_title_unplayed.search(title):
            title = extract(self.r_title_unplayed,line,'')

        logger.debug('cursong')
        logger.debug(title)
        return self.filename_id.get(title,1)

    def process_line(self,line,i,r_title=None):

        if r_title is None:
            r_title = self.r_title

        proc = ''
        try:
            rating =  self.r_rating.findall(line)
            if rating and rating[0] != '0':
                self.original[i] = rating[0]
                self.mark_dict[i] = rating[0]

            play_count = extract(self.r_play_count,line,'')
            proc += 'plays:' + play_count.zfill(2) + '|'

            #if track not played wont have last played, will look like album line
            title = extract(r_title,line,'') or extract(self.r_album_title,line,'')
            if self.r_title_unplayed.match(title):
                title = extract(self.r_title_unplayed,title,'')

            self.filename_id[i]     = title
            self.filename_id[title] = i
            proc += title

        except Exception as ex:
            #print ex
            proc += str(ex)

        return proc


    def modify_ratings(self):
        logging.critical('wtf')
        logging.critical(self.dirty)
        logging.critical(0 in self.dirty)
        logging.critical('wtf')
        ans = []
        if self.ALBUM_INDEX in self.dirty:#album
            new_rating =  self.dirty.pop(self.ALBUM_INDEX)
            #query = '''eugene listinfo -A'''
            query = (" -A ",new_rating)
            logging.critical(query)
            logging.critical('wtf')
            #txt = subprocess.check_output( query , shell=True)
            txt = query
            ans.append( txt)

        for linenum,new_rating in self.dirty.iteritems():
            #query = '''eugene listinfo %s "uri='%s'"'''% (new_rating,self.filename_id[linenum])
            #identifying search, new rating)
            query = (''' "uri='%s'" '''% (self.filename_id[linenum]),new_rating)
            logging.critical(linenum)
            logging.critical(query)

            #txt = subprocess.check_output( query , shell=True)
            txt = query
            ans.append( txt)

        return ans

    def do_modifications(self):
        logging.critical(self.dirty)
        ans = self.modify_ratings()
        return ans



class MPDMangage(object):
    '''encapsulates some playlist alteration behavior,bridge between mpdcron databases and mpd  '''

    def __init__(self):
        self.client = MPDClient()               # create client object
        self.client.timeout = 10                # network timeout in seconds (floats allowed), default: None
        self.client.idletimeout = None          # timeout for fetching the result of the idle command is handled seperately, default: None
        self.host = os.environ.get('MPD_HOST','localhost')
        self.client.connect(self.host, 6600)  # connect to localhost:6600

    def current_album(self):
        album = self.client.currentsong()['album']
        songs = self.client.playlistsearch('album',album)
        return songs

    def sort_rating(self):
        pass


if __name__ == '__main__':
    ih = MenuDemo()
    commands,force = ih.run()
    del ih

    num_modified = 0
    for command in commands:
        query,rating = command

        if query == ' -A ':
            change_rating = "eugene rateabs %s %s " % ( query, rating )
        else:
            change_rating = "eugene rateabs %s %s " % ( rating, query )

        display =  "eugene listinfo %s " % ( query )
        txt = [l for l in subprocess.check_output( display , shell=True).split('\n') if l]
        if len(txt) != 1:
            print 'I dont think this query is unique to this song : ( skipping, sorry'
            continue
        else:
            txt = txt[0]
            print 'before|',txt

        if force:
            subprocess.check_output( change_rating , shell=True)
            print 'after',subprocess.check_output( display , shell=True)
            num_modified += 1
            continue


        print change_rating
        do_this = choice_of_options('want to execute this command?',['y','n','q','f'])
        if do_this in ['y','f']:
            print subprocess.check_output( change_rating , shell=True)
            print 'after',subprocess.check_output( display , shell=True)
            num_modified += 1
        elif do_this == 'q':
            exit()

        if do_this == 'f':
            force = True
