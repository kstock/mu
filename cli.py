'''
Presonal Python command line utilities
'''

MUSIC_DIR = "/home/kstock/Music/"

import discogs_client as discogs
import subprocess
import sys,os

discogs.user_agent = 'quickShellUtilsForMe'

def get_genres(query = 'Black Moth Super Rainbow|Cobra Juicy'):
    '''Find the genres and styles for current playing album in mpd via searching discogs  '''

    query = query.split(r'\|')

    artist, album = query[0],query[1]

    s = discogs.Search(album)
    res = s.results()
    if res:#if we get results
        for r in res:
            if isinstance(r,discogs.Release): #look for releases
                try:
                    if r.artists[0].data['name'] == artist:#that match the artist
                        print 'title',r.title
                        print 'genres',r.data.get('genres','?')
                        print 'styles',r.data.get('styles','?')
                        return
                except:
                    pass

    print 'no results'

def get_genres2(query = 'Black Moth Super Rainbow|Cobra Juicy'):
    '''Find the genres and styles for current playing album in mpd via searching discogs  '''

    import re
    q = query
    q = re.sub(r'\|',' ',q)
    query = query.split(r'\|')

    artist, album = query[0],query[1]

    s = discogs.Search(q)
    res = s.results()
    print res
    if res:#if we get results
        print len(res)
        for r in res:
            if isinstance(r,discogs.Artist):#look for releases
                for rel in r.releases:
                    if rel.title == album:
                        print 'title',rel.title
                        print 'genres',rel.data.get('genres','?')
                        print 'styles',rel.data.get('styles','?')
                        return

    print 'no results'

def cur_song_dir(music_dir=None):
    '''Go to the dir that contains currently playing song in mpd   '''
    if music_dir is None:
        music_dir = MUSIC_DIR

    song = subprocess.check_output('mpc -f "%file%" current',shell=True)
    song_dir = music_dir + os.path.dirname(song)
    print song_dir

    return song_dir


if __name__ == '__main__':
    if len(sys.argv) > 1:
        args = ' '.join(sys.argv[1:])
        print args
        get_genres(args)

