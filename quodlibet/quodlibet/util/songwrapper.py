# Copyright 2005 Michael Urman
#           2016 Nick Boultbee
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

from quodlibet import _
from quodlibet.util.dprint import print_d
from quodlibet.formats import AudioFileError
from quodlibet import util
from quodlibet import qltk
from quodlibet.qltk.wlw import WritingWindow
from quodlibet.util.misc import total_ordering, hashable


@hashable
@total_ordering
class SongWrapper(object):
    __slots__ = ['_song', '_updated', '_needs_write']

    def __init__(self, song):
        self._song = song
        self._updated = False
        self._needs_write = False

    def _was_updated(self):
        return self._updated

    def __setitem__(self, key, value):
        if key in self and self[key] == value:
            return
        self._updated = True
        self._needs_write = (self._needs_write or not key.startswith("~"))
        return self._song.__setitem__(key, value)

    def __delitem__(self, key):
        retval = self._song.__delitem__(key)
        self._updated = True
        self._needs_write = (self._needs_write or not key.startswith("~"))
        return retval

    def __getattr__(self, attr):
        return getattr(self._song, attr)

    def __setattr__(self, attr, value):
        # Don't set our attributes on the song. However, we only want to
        # set attributes the song already has. So, if the attribute
        # isn't one of ours, and isn't one of the song's, hand it off
        # to our parent's attribute handler for error handling.
        if attr in self.__slots__:
            return super(SongWrapper, self).__setattr__(attr, value)
        elif hasattr(self._song, attr):
            return setattr(self._song, attr, value)
        else:
            return super(SongWrapper, self).__setattr__(attr, value)

    def __hash__(self):
        return hash(self._song)

    def __eq__(self, other):
        if hasattr(other, '_song'):
            other = other._song
        return self._song == other

    def __lt__(self, other):
        if hasattr(other, '_song'):
            other = other._song
        return self._song < other

    def __getitem__(self, *args):
        return self._song.__getitem__(*args)

    def __contains__(self, key):
        return key in self._song

    def __call__(self, *args):
        return self._song(*args)

    def pop(self, *args):
        self._updated = True
        self._needs_write = True
        return self._song.pop(*args)

    def update(self, other):
        self._updated = True
        self._needs_write = True
        return self._song.update(other)

    def rename(self, newname):
        self._updated = True
        return self._song.rename(newname)


def ListWrapper(songs):
    def wrap(song):
        if song is None:
            return None
        else:
            return SongWrapper(song)
    return [wrap(s) for s in songs]


def check_wrapper_changed(library, parent, songs):
    need_write = [s for s in songs if s._needs_write]

    if need_write:
        win = WritingWindow(parent, len(need_write))
        win.show()
        for song in need_write:
            try:
                song._song.write()
            except AudioFileError as e:
                qltk.ErrorMessage(
                    None, _("Unable to edit song"),
                    _("Saving <b>%s</b> failed. The file "
                      "may be read-only, corrupted, or you "
                      "do not have permission to edit it.") %
                    util.escape(song('~basename'))).run()
                print_d("Couldn't save song %s (%s)" % (song("~filename"), e))

            if win.step():
                break
        win.destroy()

    changed = []
    for song in songs:
        if song._was_updated():
            changed.append(song._song)
        elif not song.valid() and song.exists():
            library.reload(song._song)
    library.changed(changed)
