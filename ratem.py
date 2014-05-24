from __future__ import division
import urwid
import subprocess
import re
import logging,sys

urwid.Widget._command_map['k'] = urwid.CURSOR_UP
urwid.Widget._command_map['j'] = urwid.CURSOR_DOWN

r_title       = re.compile(r'Last_Played.*? (.*)')
r_album_title = re.compile(r'Rating:[0-9]+ (.*)')
r_title_unplayed = re.compile(r'Karma:[0-9]+ (.*)')

r_rating      = re.compile(r'Rating:([0-9]+)')
r_play_count  = re.compile(r'Play_Count:([0-9]+)')

fname = '/home/kstock/workspace/mu/foo.log'
logging.basicConfig(filename=fname,level=logging.DEBUG)
logger = logging.getLogger(fname)
# Configure logger to write to a file...

def my_handler(_, value, __):
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

def get_title(text):
    title = extract(r_title,text,'') or extract(r_album_title,text,'')
    if r_title_unplayed.match(title):
        title = extract(r_title_unplayed,title,'')
    return title

def get_current_song():
    query = "eugene listinfo"
    line  = subprocess.check_output(query,shell=True)
    return get_title(line)

def process_line(line,i,r_title=None):

    if r_title is None:
        #r_title = self.r_title
        r_title       = re.compile(r'Last_Played.*? (.*)')

    proc = ''
    try:
        rating =  re.compile(r'Rating:([0-9]+)')
        #if rating and rating[0] != '0':
            #self.original[i] = rating[0]
            #self.mark_dict[i] = rating[0]

        play_count = extract(r_play_count,line,'')
        proc += 'plays:' + play_count.zfill(2) + '|'

        #if track not played wont have last played, will look like album line
        title = extract(r_title,line,'') or extract(r_album_title,line,'')
        if r_title_unplayed.match(title):
            title = extract(r_title_unplayed,title,'')

        #title = re.sub("'",r"\'",title)

        #self.filename_id[i]     = title
        #self.filename_id[title] = i
        proc += title

    except Exception as ex:
        #print ex
        proc += str(ex)

    return proc

def clean_quotes(text):
    ''' deal with titles that include quotes '''
    if "'" not in text:
        return text



def getOutputLines(rate_album=True):

    '''Get the list of songs to potentially edit. if rate_album then get album song, else get all artists songs  '''
    outputLines = []
    if rate_album:#TODO if album is mapped to 2 different artists.
        #query = subprocess.check_output('''mpc -f 'artist="%artist%" and album="%album%"' current''',shell=True)
        query = subprocess.check_output('''mpc -f 'album="%album%"' current''',shell=True)
    else:
        query = subprocess.check_output('''mpc -f 'artist="%artist%"' current''',shell=True)

    outputLines.extend( subprocess.check_output("eugene listinfo '" + query.strip() + "'", shell=True).split('\n') )

    #add 2 for offset from album name, separator line
    outputLines = [ l for l  in outputLines if l]



    #outputLines = [ process_line(l,i+2) for i,l in enumerate(outputLines)]
    outputLines = [ Song(l) for i,l in enumerate(outputLines)]
    #outputLines = [ Song(str(i)) for i,l in enumerate(outputLines)]
    #outputLines = [ urwid.Text(l) for i,l in enumerate(outputLines)]

    outputLines.insert(0, Album(subprocess.check_output('eugene listinfo -A',shell=True).strip()) )
    #outputLines.insert(0, l)

    return outputLines


class Score(urwid.IntEdit):

    def __init__(self,text,default='00'):
        self.dirty = False

        self.original_rating = default
        self.rating          = default
        display = self.get_display(default)
        super(Score,self).__init__(text,display)

    def commit(self):
        self.original_rating = self.rating
        self.clean()
        return int(self.rating)


    def clean(self):
        self.set_edit_text(self.get_display(self.original_rating))
        self.rating = self.original_rating
        self.dirty = False

    def alter_score(self,original,new):
        if original == '0' and not new:
            return self.original_rating
        return str( int( original+new) ).zfill(2)

    def get_display(self,rating):
        if int(rating) == 0:
            return '__'

        return rating.zfill(2)

    def keypress(self,size,key):
        '''A rating is between 0-10, and is either dirty (changed from database
        since program start) or clean (unchanged)'''

        new_rating = self.rating
        if key.isdigit():

            if int(self.rating + key) <= 10:
                new_rating = self.alter_score(self.rating,key)
            else:
                new_rating = self.alter_score('',key)

        elif key == 'backspace':
            new_rating = self.alter_score(self.rating[:-1],'')

        self.rating = new_rating
        self.dirty = self.original_rating != self.rating
        self.set_edit_text(self.get_display(new_rating))

        return key


class Song(urwid.WidgetWrap):
    def __init__(self,text):
        #self.rating = re.search(r'Rating(?P<rating>\d+)',text).group('rating')

        self.play_count      = extract(r_play_count,text,'')
        self.original_rating = extract(r_rating,text,'').zfill(2)
        self.rating          = self.original_rating
        self.playing         = False

        self.title = get_title(text)

        listbox = self.get_pieces()
        w = urwid.Columns(listbox)
        super(Song,self).__init__(w)

    def get_pieces(self):
        self.txt = ''.join(['|',self.play_count,'|',self.title])
        listbox = [ (3,urwid.AttrMap(Score("",default=self.rating),None,None)), #Score
                    (len(self.txt),urwid.Text(self.txt)),                       #song name
                    (9,urwid.AttrMap(urwid.Text(''),None,focus_map={None:'reversed'})),                #dirt
                    ]
        return listbox

    @property
    def score(self):
        return self._w.contents[0][0]

    @property
    def dirt(self):
        return self._w.contents[-1][0]

    def commit(self):
        if self.score.original_widget.dirty:

            new_rating = self.score.original_widget.commit()
            change_rating = self.get_query(new_rating)
            logging.critical(change_rating)
            out = subprocess.check_output( change_rating )#, shell=True)

    def get_query(self, new_rating):
        query = (new_rating, r''' 'uri="%s"' '''% (self.title) )


        safe_title = 'uri="' + re.sub("'",'''\'''', self.title) + '"'
        change_rating =  ["eugene","rateabs", str(new_rating) , safe_title]
        #change_rating = r"eugene rateabs %s %s " % query
        return change_rating

    def keypress(self,size,key):

        key = super(Song,self).keypress(size,key)
        if key == 'd':
            #self.score.rating = self.score.original_rating
            self.score.original_widget.clean()
        elif key == 'c':
            self.commit()

        if self.score.original_widget.dirty:
            self.score.set_attr_map({None:'dirty'})
            self.dirt.set_attr_map({None:'dirty'})
            self.dirt.original_widget.set_text("Dirty(%s)" % self.score.original_widget.original_rating)
        else:
            self.score.set_attr_map({None:''})
            self.dirt.set_attr_map({None:''})
            self.dirt.original_widget.set_text("")

        return key


class Album(Song):
    def __init__(self,text):
        super(Album,self).__init__(text)

    def get_pieces(self):
        pieces = super(Album,self).get_pieces()

        dirt   = pieces[-1]
        pieces = pieces[:-1]

        higher_than = "|#>5:"
        median      = '|median:'
        average     = '|average:'

        self.avg = urwid.AttrMap(urwid.Edit(average),{None:''},{None:''})
        self.med = urwid.AttrMap(urwid.Edit(median),{None:''},{None:''})
        self.gt  =  urwid.AttrMap(urwid.Edit(higher_than   ),{None:''},{None:''})
        pieces.extend([
         (len(average) + 4,           self.avg),
         (len(median)      + 2,           self.med),
         (len(higher_than)     + 2,           self.gt ),
                    dirt,]
                    )
        return pieces

    def compute_stats(self,songs):
        scores = [int(s.score.original_widget.rating) for s in songs]
        scores = [s for s in scores if s != 0]#only count rated songs
        self.avg.original_widget.set_edit_text( str(sum(scores) / (len(scores) or 1 ) )[:4])#truncate to 4 chars
        self.gt.original_widget.set_edit_text( str( len([s for s in scores if s > 5]) ) )
        if scores:
            self.med.original_widget.set_edit_text(str( scores[ len(scores) // 2 ] ) )


    def get_query(self,new_rating):
        #query = (new_rating, ''' 'uri="%s"' '''% (self.title) )
        change_rating = "eugene rateabs -A %s " % new_rating
        return change_rating.split()

choices = getOutputLines()

def menu(title, choices):
    body = []
    for c in choices:
        #button = urwid.Button(c)
        #button = urwid.IntEdit(c)
        #button = myIntEdit(c)
        #urwid.connect_signal(button, 'click', item_chosen, c)
        #body.append(urwid.AttrMap(button, None, focus_map='reversed'))
        body.append(urwid.AttrMap(c, None, focus_map='reversed'))
    #return urwid.ListBox(urwid.SimpleFocusListWalker(body))
    return SongList(urwid.SimpleFocusListWalker(body))

class SongList(urwid.ListBox):

    def __init__(self,body,kind='album'):

        super(SongList,self).__init__(body)
        self.current_song_i = 0
        self.current_song   = get_current_song()
        self.highlight_current()
        self.kind = kind
        if kind == 'album':#first line should be album,we need stats!
            self.body[0].original_widget.compute_stats(
                    [x.original_widget for x in self.body]
                     )

    def update(self):
        '''update list based on current playing album'''
        body = getOutputLines()
        self.body = urwid.SimpleFocusListWalker([
                        urwid.AttrMap(c, None, focus_map='reversed')
                        for c in body])
        self.current_song_i = 0
        self.current_song   = get_current_song()
        self.highlight_current()

    def rm_highlight(self,pos):
        self.body[pos].set_attr_map({None:''})

    def highlight_current(self):

        for i,b in enumerate(self.body):
            if b.original_widget.title == self.current_song:
                self.current_song_i = i
                b.set_attr_map({None:'playing'})

    def goto(self,pos):
        if pos == 'current':
            pos = self.current_song_i

        self.set_focus(pos)


    def sort(self,func,reverse=True):
        body = sorted(self.body,key = func,reverse=reverse)
        self.body = urwid.SimpleFocusListWalker(body)

    def commit(self):
        print self.get_focus

    def apply_all(self,func):
        for b in self.body:
            func(b)


    def keypress(self,size,key):
        if key in ['D']:
            for b in self.body:
                b.keypress(size,'d')
        elif key == 'g':
            self.goto(0)
        elif key == 'G':
            self.goto(len(self.body) - 1)
        elif key == 's':
            self.sort(lambda x: (int(x.original_widget.original_rating),x.original_widget.play_count),reverse=True)
        elif key == 'p':
            self.sort(lambda x: (x.original_widget.play_count, int(x.original_widget.original_rating)),reverse=True)
        elif key == 'C':
            self.apply_all(lambda x:x.original_widget.keypress(size,'c'))
        elif key == 'U':
            self.update()

        if key in ['o','c'] or key.isdigit():#'o','p','d','D']:
            cursong = get_current_song()
            if cursong != self.current_song:
                self.rm_highlight(self.current_song_i)
                self.current_song = cursong
                self.highlight_current()

            self.body[0].original_widget.compute_stats(
                    [x.original_widget for x in self.body]
                    )
        if key == 'o':

            self.goto('current')

        key = super(SongList,self).keypress(size,key)
        return key


def item_chosen(button, choice):
    response = urwid.Text([u'You chose ', choice, u'\n'])
    done = urwid.Button(u'Ok')
    urwid.connect_signal(done, 'click', exit_program)
    main.original_widget = urwid.Filler(urwid.Pile([response,
        urwid.AttrMap(done, None, focus_map='reversed')]))

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

#urwid.MainLoop(top, palette=[('reversed', 'standout', '')],unhandled_input=unhandled_input).run()
urwid.MainLoop(top, palette=palette,unhandled_input=unhandled_input).run()
'''
import re
import subprocess
res =[]
for s in songs[-45:-41]:
    if re.search(r"'",s):
        res.append('error:'+s)
    else:
        foo = 'eugene listinfo 'uri="%s"' '  % s.strip()
        print foo
        res.append(subprocess.check_output(foo,shell=True))
'''

