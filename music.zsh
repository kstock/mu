#aliases and functions to manage mpd+mpdcron+beets
#
#
#
#aliases{{{
alias bran='beet random -a -n 100 L'
alias currSong='qdbus org.mpris.clementine /Player org.freedesktop.MediaPlayer.GetMetadata'
alias lsong="sqlite3 -line ~/.mpdcron/stats.db 'select artist,title from song order by last_played desc limit 5'"
#aliases}}}
#
#
#functions{{{
#

#list info from mpdcron db, stripping info I don't care about.
function eli(){
    awk '{gsub("(^[0-9]+|Love:|Kill|Karma.)..","",$0 );print $0}' <(eugene listinfo) }


function elia_part(){
    awk '{gsub("(^[0-9]+|Love:|Kill|Karma.)..","",$0 );print $0}'  <(eugene listinfo -A)
    query=$(mpc -f 'artist="%artist%" and album="%album%"' current)
    awk '{gsub("(^[0-9]+|Love:|Kill|Karma.)..","",$0 ); if (NF >0) {print($0)};}'  <(eugene listinfo $query)

}

#list info from mpdcron db for current album,colors the currently playing track red!!
function elia(){
    #awk '{if (NF > 1) {print $0}}' <(elia_part | ack-grep -i --color --color-match=red ".*$(mpc -f "%title%" current).*|$")
    awk '{if (NF > 1) {print $0}}' <(elia_part | ack-grep -i --color ".*$(mpc -f "%title%" current).*|$")
    }


#rate in mpdcron stats db
#no args uses my ncurses interface, one arg rates the currently playing song
function er(){
    if [[ $# == 1 ]];
    then 
        eugene rateabs $1
        eli
    else
        python ~/workspace/mu/cur.py
    fi

}

#beets git:(master) ✗ beet ls -a -f '$genre - $albumartist -$album' "$(echo $(python -c 'import ran; ran.build_query("electronic")'))"  | shuf | head -1

#Discogs GENre
#uses python to query discogs for genres/styles of the current track playing in mpd
#DEPENDS: mpd,mpc,python,discogs_client
function dgen() {
    echo 'attempting to get genre for ' $(mpc -f '%artist% - %album% - %title%' current)
    python ~/workspace/mu/cli.py "$(mpc -f '%artist%\|%album%' current)"
}

#Beet GENre
#uses beets display the genre metadata for currently playing track
function bgen() {
    beet info "~/Music/""$(mpc -f '%file%' current)" | ack-grep 'genre| artist:'
}

function binfo(){
    beet info "~/Music/""$(mpc -f '%file%' current)"
}

#Beet Genre Frequency
function bgf() {

    if [[ $1 = top ]];
    then
        awk '{a[$0]++}END{for(x in a) printf("%20s|%s\n", x, a[x])}' <(beet ls -a -f '$genre') | sort -n -t '|' -k2 | tail -10
    else
        print no
        awk '{a[$0]++}END{for(x in a) printf("%20s|%s\n", x, a[x])}' <(beet ls -a -f '$genre') | sort 
    fi
}


function cdm(){
    SONG_DIR=$(python -c 'from cli import cur_song_dir;cur_song_dir()')
    #echo $SONG_DIR
    cd $SONG_DIR
}
