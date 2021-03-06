'''
Base class for various music playing services.
'''

from   dexter.core.log          import LOG
from   dexter.core.media_index  import MusicIndex, AudioEntry
from   dexter.core.player       import SimpleMP3Player
from   dexter.core.util         import to_letters
from   dexter.service           import Service, Handler, Result

from   fuzzywuzzy      import fuzz
from   threading       import Thread

# ------------------------------------------------------------------------------

class MusicService(Service):
    '''
    The base class for playing music on various platforms.
    '''
    def __init__(self, name, state, platform):
        '''
        @see Service.__init__()

        @type  platform: str
        @param platform:
            The name of the platform that this service streams music from, like
            C{Spotify}, C{Pandora}, C{Edna}, C{}, etc.
        '''
        super(MusicService, self).__init__(name, state)

        self._platform = platform


    def evaluate(self, tokens):
        '''
        @see Service.evaluate()
        '''
        # Get stripped text, for matching
        words = [to_letters(w).lower() for w in self._words(tokens)]

        # Look for specific control words, doing a fuzzy match
        threshold = 80
        if len(words) == 1:
            if self._matches(words[0], "stop"):
                return self._get_stop_handler(tokens)
            elif self._matches(words[0], "play"):
                return self._get_play_handler(tokens)

        # We expect to have something along the lines of:
        #  Play <song or album> on <platform>
        #  Play <genre> music
        #  Play <song or album> by <artist>
        if len(words) < 3:
            # We can't match on this
            return None

        # See if the first word is "play"
        if not self._matches(words[0], "play"):
            # Nope, probably not ours then
            return None

        # Okay, strip off "play"
        words = words[1:]

        # See if it ends with "on <platform>", if so then we can see if it's for
        # us specificaly.
        platform_match = False
        if self._matches(words[-2], "on"):
            if words[-1] == self._platform.lower():
                # This is definitely for us
                platform_match = True

                # Strip off the platfrom now so that we can match other things
                words = words[:-2]
            else:
                # Looks like it's for a different platform
                return None

        # See if we have an artist
        artist = None
        if "by" in words and len(words) >= 3:
            # We see if this matches a know artist. It could by something like
            # "Bye Bye Baby" fooling us.

            # Find the last occurance of "by"; hey Python, why no rindex?!
            by_index = len(words) - list(reversed(words)).index("by") - 1
            artist = words[by_index+1:]
            if self._match_artist(artist):
                # Okay, strip off the artist
                words = words[:by_index]
            else:
                # No match
                artist = None

        # See if it ends with a genre indicator. Don't do this is we matched an
        # artist (since it could be "Sexy Music" by "Meat Puppets", for example.
        if artist is None and len(words) > 1 and self._matches(words[-1], "music"):
            genre = tuple(words[:-1])
            words = []
        else:
            genre = None

        # Anything left should be the song-or-album name now
        if len(words) > 0:
            song_or_album = tuple(words)
            words = []

        # Okay, ready to make the hand-off call to the subclass
        return self._get_handler_for(tokens,
                                     platform_match,
                                     genre,
                                     artist,
                                     song_or_album)


    def set_volume(self, volume):
        '''
        Set the volume to a value between zero and eleven.

        @type  value: float
        @param value:
            The volume level to set. This should be between 0 and 11 inclusive.
        '''
        # To be implemented by subclasses
        raise NotImplementedError("Abstract method called")


    def get_volume():
        '''
        Get the current volume, as a value between zero and eleven.

        @rtype: float
        @return:
            The volume level; between 0 and 11 inclusive.
        '''
        # To be implemented by subclasses
        raise NotImplementedError("Abstract method called")


    def _matches(self, words, target):
        '''
        Use fuzz.ratio  to match word tuples.
        '''
        return fuzz.ratio(words, target) > 80


    def _match_artist(self, artist):
        '''
        See if the given artist name tuple matches something we know about.

        @type  artist: tuple(str)
        @param artist:
            The artist name, as a tuple of strings.
        '''
        # To be implemented by subclasses
        raise NotImplementedError("Abstract method called")


    def _get_stop_handler(self, tokens):
        '''
        Get the handler to stop playing whatever is playing. If nothing is playing
        then return C{None}.

        @type  tokens: tuple(L{Token})
        @param tokens:
            The tokens for which this handler was generated.
        '''
        # To be implemented by subclasses
        raise NotImplementedError("Abstract method called")


    def _get_play_handler(self, tokens):
        '''
        Get the handler to resume playing whatever was playing (and was previously
        stopped). If nothing was playing then return C{None}.

        @type  tokens: tuple(L{Token})
        @param tokens:
            The tokens for which this handler was generated.
        '''
        # To be implemented by subclasses
        raise NotImplementedError("Abstract method called")


    def _get_handler_for(self,
                         tokens,
                         platform_match,
                         genre,
                         artist,
                         song_or_album):
        '''
        Get the handler for the given arguments, if any.

        @type  tokens: tuple(L{Token})
        @param tokens:
            The tokens for which this handler was generated.
        @type  platform_match: bool
        @param platform_match:
            Whether the platform was specified.
        @type  genre: tuple(str)
        @param genre:
            The music genre type, as a tuple of strings.
        @type  artist: tuple(str)
        @param artist:
            The artist name, as a tuple of strings.
        @type  song_or_album: tuple(str)
        @param song_or_album:
            The name of the song or album to play, as a tuple of strings.
        '''
        # To be implemented by subclasses
        raise NotImplementedError("Abstract method called")

# ------------------------------------------------------------------------------

class _LocalMusicServicePauseHandler(Handler):
    def __init__(self, service, tokens):
        '''
        @see Handler.__init__()
        '''
        super(_LocalMusicServicePauseHandler, self).__init__(
            service,
            tokens,
            1.0 if service.is_playing() else 0.0,
            False
        )


    def handle(self):
        '''
        @see Handler.handle()`
        '''
        was_playing = self.service.is_playing()
        self.service.pause()
        return Result(self, '', False, was_playing)


class _LocalMusicServiceUnpauseHandler(Handler):
    def __init__(self, service, tokens):
        '''
        @see Handler.__init__()
        '''
        super(_LocalMusicServiceUnpauseHandler, self).__init__(
            service,
            tokens,
            1.0  if service.is_paused() else 0.0,
            True if service.is_paused() else False,
        )


    def handle(self):
        '''
        @see Handler.handle()`
        '''
        was_paused = self.service.is_paused()
        self.service.unpause()
        return Result(self, '', False, was_paused)


class _LocalMusicServicePlayHandler(Handler):
    def __init__(self, service, tokens, what, filenames, score):
        '''
        @see Handler.__init__()

        @type  what: str
        @param what:
            What we are playing, like "Blah Blah by Fred"
        @type  filenames: list(str)
        @param filenames:
            The list of filenames to play
        @type  score: float
        @param score:
            The match score out of 1.0.
        '''
        # We deem ourselves exclusive since we had a match
        super(_LocalMusicServicePlayHandler, self).__init__(
            service,
            tokens,
            score,
            True
        )
        self._filenames = filenames
        self._what      = what


    def handle(self):
        '''
        @see Handler.handle()`
        '''
        LOG.info('Playing %s' % (self._what))
        self.service.play(self._filenames)
        return Result(self, '', False, True)


class LocalMusicService(MusicService):
    '''
    Music service for local files.
    '''
    def __init__(self, state, dirname=None):
        '''
        @see Service.__init__()

        @type  dirname: str
        @param dirname:
            The directory where all the music lives.
        '''
        super(LocalMusicService, self).__init__("LocalMusic",
                                                state,
                                                "Local")

        if dirname is None:
            raise ValueError("Not given a directory name")

        self._player = SimpleMP3Player()

        # Spawn a thread to create the media index, since it can take a long
        # time.
        self._media_index = None
        def create_index():
            try:
                self._media_index = MusicIndex(dirname)
            except Exception as e:
                LOG.error("Failed to create music index: %s", e)
        thread = Thread(name='MusicIndexer', target=create_index)
        thread.daemon = True
        thread.start()


    def set_volume(self, volume):
        '''
        @see MusicService.set_volume()
        '''
        self._player.set_volume(volume)


    def get_volume():
        '''
        @see MusicService.get_volume()
        '''
        return self._player.get_volume()


    def play(self, filenames):
        '''
        Play the given list of filenames.

        @type  filenames: tuple(str)
        @param filenames:
            The list of filenames to play.
        '''
        self._player.play_files(filenames)


    def is_playing(self):
        '''
        Whether the player is playing.

        @rtype: bool
        @return:
           Whether the player is playing.
        '''
        return self._player.is_playing()


    def is_paused(self):
        '''
        Whether the player is paused.

        @rtype: bool
        @return:
           Whether the player is paused.
        '''
        return self._player.is_paused()


    def pause(self):
        '''
        Pause any currently playing music.
        '''
        self._player.pause()


    def unpause(self):
        '''
        Resume any currently paused music.
        '''
        self._player.unpause()


    def _match_artist(self, artist):
        '''
        @see MusicService._match_artist()
        '''
        if self._media_index is None:
            return False
        else:
            matches = self._media_index.lookup(artist=' '.join(artist))
            return len(matches) > 0


    def _get_stop_handler(self, tokens):
        '''
        @see MusicService._get_stop_handler()
        '''
        return _LocalMusicServicePauseHandler(self, tokens)


    def _get_play_handler(self, tokens):
        '''
        @see MusicService._get_play_handler()
        '''
        return _LocalMusicServiceUnpauseHandler(self, tokens)


    def _get_handler_for(self,
                         tokens,
                         platform_match,
                         genre,
                         artist,
                         song_or_album):
        '''
        @see MusicService._get_handler_for()
        '''
        if self._media_index is None:
            return None

        # Do nothing if we have no name
        if song_or_album is None or len(song_or_album) == 0:
            return None

        # Normalise to strings
        name = ' '.join(song_or_album)
        if artist is None or len(artist) == 0:
            artist = None
        else:
            artist = ' '.join(artist)

        # Try using the song_or_album as the song name
        entries = self._media_index.lookup(name=name, artist=artist)

        if len(entries) > 0:
            # Just pick the first
            entries = entries[:1]
            entry = entries[0]

            # Score by the song name (this is out of 100)
            score = fuzz.ratio(entry.name, name)

            # What we are playing
            what = entry.name
            if entry.artist is not None:
                what += ' by ' + entry.artist
        else:
            # That failed so fall back to it being the album name
            entries = self._media_index.lookup(name=name, artist=artist)

            # Score by the album name (this is out of 100)
            score = fuzz.ratio(entries[0].album, name)

            # What we are playing
            what = entries[0].album
            if entries[0].artist is not None:
                what += ' by ' + entries[0].artist

        # Strip out any entries which aren't MP3 files
        entries = [entry
                   for entry in entries
                   if (entry.url.startswith('file://') and
                       entry.file_type == AudioEntry.MP3)]

        # See if we got anything
        if len(entries) > 0:
            return _LocalMusicServicePlayHandler(
                self,
                tokens,
                what,
                [entry.url[7:] for entry in entries],
                score / 100.0
            )
