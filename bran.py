'''
beat random
queries beets to display a bunch of random albums in ncurses urwid widget,
clicking enter on album title appends it to mpd playlist
'''

from __future__ import division
import urwid
import subprocess
from mpd import MPDClient
import re
import os
import logging,sys


HOME      = os.path.expanduser("~")
MU_PATH   = '/'.join( (HOME, 'workspace/mu') )
MUSIC_DIR = '/'.join( (HOME, "Music") )

urwid.Widget._command_map['k'] = urwid.CURSOR_UP
urwid.Widget._command_map['j'] = urwid.CURSOR_DOWN


fname = '/'.join( (MU_PATH, 'bran.log') )

logging.basicConfig(filename=fname,level=logging.DEBUG)
logger = logging.getLogger(fname)

commit_record_handler = logging.FileHandler( '/'.join( (MU_PATH, "commit_record.log") ) )
commit_record_handler.setLevel(logging.INFO)
logger.addHandler(commit_record_handler)
# Configure logger to write to a file...

def my_handler(_, value, __):
    '''force all uncaught exceptions go to logger'''
    logger.exception("Uncaught exception: {0}".format(str(value)))

# Install exception handler
sys.excepthook = my_handler


def getOutputLines():
    '''Get the list of songs to potentially edit. if rate_album then get album song, else get all artists songs  '''

    outputLines = subprocess.check_output('''beet random -a -p -n 100''',shell=True).split('\n')
    outputLines = [re.sub(MUSIC_DIR +"/","",l) for l in outputLines ]

    return outputLines


choices = getOutputLines()

def menu(title, choices):
    body = []
    for c in choices:
        button = urwid.Button(c)
        #button = urwid.IntEdit(c)
        #button = myIntEdit(c)
        urwid.connect_signal(button, 'click', item_chosen, c)
        body.append(urwid.AttrMap(button, None, focus_map='reversed'))
        #body.append(urwid.AttrMap(c, None, focus_map='reversed'))

    return urwid.ListBox(urwid.SimpleFocusListWalker(body))
    #return SongList(urwid.SimpleFocusListWalker(body))

def item_chosen(button, choice):

    client = MPDClient()               # create client object
    client.timeout = 10                # network timeout in seconds (floats allowed), default: None
    client.idletimeout = None          # timeout for fetching the result of the idle command is handled seperately, default: None
    host = os.environ.get('MPD_HOST','localhost')
    client.connect(host, 6600)  # connect to localhost:6600

    client.add(choice)

def exit_program(button):
    raise urwid.ExitMainLoop()

def unhandled_input( k):
    # update display of focus directory
    if k in ('q','Q'):
        raise urwid.ExitMainLoop()

main = urwid.Padding(menu(u'Ratings', choices), left=2, right=2)
#top = urwid.Overlay(main, urwid.SolidFill(u'\N{MEDIUM SHADE}'),
    #align='center', width=('relative', 60),
    #valign='middle', height=('relative', 60),
    #min_width=20, min_height=9)
top = urwid.Overlay(main, urwid.SolidFill(u'\N{MEDIUM SHADE}'),
    align='center', width=('relative', 100),
    valign='middle', height=('relative', 100),
    min_width=20, min_height=9)

palette = [
    ('reversed','standout',''),
    ('dirty','black','dark red'),
    ('playing','dark magenta',''),
    ]

urwid.MainLoop(top, palette=[('reversed', 'standout', '')],unhandled_input=unhandled_input).run()
#urwid.MainLoop(top, palette=palette,unhandled_input=unhandled_input).run()
