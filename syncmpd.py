'''

CREATE TABLE album(
        id              INTEGER PRIMARY KEY,
        play_count      INTEGER,
        tags            TEXT NOT NULL,
        artist          TEXT,
        name            TEXT UNIQUE NOT NULL,
        love            INTEGER,
        kill            INTEGER,
        rating          INTEGER);
CREATE TABLE artist(
        id              INTEGER PRIMARY KEY,
        play_count      INTEGER,
        tags            TEXT NOT NULL,
        name            TEXT UNIQUE NOT NULL,
        love            INTEGER,
        kill            INTEGER,
        rating          INTEGER);
CREATE TABLE genre(
        id              INTEGER PRIMARY KEY,
        play_count      INTEGER,
        tags            TEXT NOT NULL,
        name            TEXT UNIQUE NOT NULL,
        love            INTEGER,
        kill            INTEGER,
        rating          INTEGER);
CREATE TABLE song(
        id              INTEGER PRIMARY KEY,
        play_count      INTEGER,
        love            INTEGER,
        kill            INTEGER,
        rating          INTEGER,
        tags            TEXT NOT NULL,
        uri             TEXT UNIQUE NOT NULL,
        duration        INTEGER,
        last_modified   INTEGER,
        artist          TEXT,
        album           TEXT,
        title           TEXT,
        track           TEXT,
        name            TEXT,
        genre           TEXT,
        date            TEXT,
        composer        TEXT,
        performer       TEXT,
        disc            TEXT,
        mb_artistid     TEXT,
        mb_albumid      TEXT,
        mb_trackid      TEXT, last_played     INTEGER, karma           INTEGER
                NOT NULL
                CONSTRAINT karma_percent CHECK (karma >= 0 AND karma <= 100)
                DEFAULT 50);

'''
import lastfmapi
import sqlite3
api = lastfmapi.LastFmApi("bb3e1dbcdf537a2451884f1e251e5976")
rec = api.user_getRecentTracks(user="ykb")
lf = [ (a['date']['uts'],a['name']) for a in rec['recenttracks']['track'] if 'date' in a]

yest= = datetime.datetime.now() - datetime.timedelta(days = 1)
yest= calendar.timegm(future.utctimetuple())

conn = sqlite3.connect('./info.db')
c=conn.cursor()
c.execute('select last_played from song order by last_played desc limit 10')
mp = c.fetchall()
mp = set(str(d[0]) for d in mp)
ans = []
for s in lf:
    if s[0] not in mp:
        print s[1]
        ans.append(s)
