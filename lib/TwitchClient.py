"""
    Twitch client library
"""

import json
import logging
import time
import aiohttp
from lib import DubuCache

log = logging.getLogger("twitch-client")

class TwitchClient:

    def __init__(self, authid):
        """Setup basic request structures."""
        self.twitch_api_url_base = "https://api.twitch.tv/helix/"
        self.twitch_request_headers = {'Client-Id': authid}
        self.live = {}
        self.userCache = DubuCache.DubuCache("user", 1)
        self.gameCache = DubuCache.DubuCache("game", 24)
        self.gameCache.set_default({'name': 'Unlisted Game'})
        self.retry_delay_init = .5
        self.retry_max = 5


    async def current_live_data(self, usernames):
        """Get dict of live streams + extra data."""

        self.userCache.cleanup()
        self.gameCache.cleanup()

        streams = await self.get_streams(usernames)

        if streams is not None:
            if len(streams) > 0:
                streams = self._rekey_list(streams, 'id')

                # check ids against caches
                userids = []
                gameids = []
                for k,v in streams.items():
                    if v['user_id'] not in self.userCache:
                        userids.append(v['user_id'])
                    if v['game_id'] not in self.gameCache:
                        gameids.append(v['game_id'])

                # make data requests only if necessary
                try:
                    if len(userids) > 0:
                        users = await self.get_users(userids)
                        users = self._rekey_list(users,'id')
                        self.userCache.addDict(users)
                    if len(gameids) > 0:
                        games = await self.get_games(gameids)
                        games = self._rekey_list(games,'id')
                        self.gameCache.addDict(games)
                except TypeError as e:
                    log.warning(e)
                    streams = {}
                else:
                    # add the game/user data to the return
                    for k,v in streams.items():
                        streams[k]['user'] = self.userCache.value(v['user_id'])
                        streams[k]['game'] = self.gameCache.value(v['game_id'])
            else:
                # streams is a list by default, make sure it's a dict
                streams = {}

        return streams

    async def update_live_list(self, usernames):
        streams = await self.current_live_data(usernames)
        started = {}
        stopped = {}
        updated = {}

        if streams is not None:
            if len(streams) > 0:
                started = {k:v for (k,v) in streams.items() if k not in list(self.live.keys())}
                stopped = {k:v for (k,v) in self.live.items() if k not in list(streams.keys())}

            # Find streams with updated games/titles. The id doesn't change.
            for k in set(streams.keys()).intersection(self.live.keys()):
                if streams[k]['game_id'] != self.live[k]['game_id'] or \
                   streams[k]['title'] != self.live[k]['title']:
                    updated[k] = streams[k]

            # Current live list is the new base.
            self.live = streams
        else:
            streams = {}

        return { 'started': started, 'stopped': stopped, 'updated': updated, 'streams': streams }

    def get_streams(self, usernames):
        """API request for stream information."""

        # https://api.twitch.tv/helix/streams?user_id=USER1&user_id=USER2
        api_url = '{}streams'.format(self.twitch_api_url_base)
        params = self._mdict('user_login', usernames)
        return self._make_request(api_url, params)

    def get_users(self, userids):
        """Get profile/data on users by ids."""

        # https://api.twitch.tv/helix/users?id=USER1&id=USER2
        api_url = '{}users'.format(self.twitch_api_url_base)
        params = self._mdict('id', userids)
        return self._make_request(api_url, params)

    def get_games(self, gameids):
        """Get game information by ids."""

        # https://api.twitch.tv/helix/games?id=GAME1&id=GAME2
        api_url = '{}games'.format(self.twitch_api_url_base)
        params = self._mdict('id', gameids)
        return self._make_request(api_url, params)

    def get_followers(self, userid):
        """Get follower count for one user."""

        # https://api.twitch.tv/helix/users/follows?to_id=userid
        api_url = '{}users/followers'.format(self.twitch_api_url_base)
        params = {'to_id': userid}
        return self._make_request(api_url,params)

    async def _make_request(self, url, params):
        try:
            async with aiohttp.request('GET', url, params=params, 
                    headers=self.twitch_request_headers) as r:
                json = await r.json()

                if r.status >= 500:
                    log.warning('API status code {} returned!'.format(r.status))
                    response = None
                elif r.status != 200:
                    log.warning('API status code {} returned!'.format(r.status))
                    response = None
                    print(r)
                else:
                    response = json['data']

                rr = int(r.headers.get('Ratelimit-Remaining'))
                if rr < 5:
                    log.warning('API rate limit remaining is {}!'.format(rr))
        except Exception as e:
            log.error(e)
            response = None
        finally:
            return response

    def _mdict(self, key, values):
        """Return a MultiDict with the same 'key' for all 'values'."""
        mdict = []
        for v in values:
            mdict.append((key, v))
        return mdict

    def _get_slice(self, adict, key):
        """Return a slice of a dict indicated by key."""
        a = []
        for d in adict:
            a.append(d[key])
        return a
    
    def _rekey_list(self, alist, key):
        """Rekey a list into a dict indexed by given key."""
        newdict = {}
        if alist is not None:
            for d in alist:
                newdict[d[key]] = d
        return newdict
