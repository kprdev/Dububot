"""
    Twitch client library
"""

import requests
import json
import logging
import time
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
        self.retry_delay_init = .5
        self.retry_max = 5


    def current_live_data(self, usernames):
        """Get dict of live streams + extra data."""

        self.userCache.cleanup()
        self.gameCache.cleanup()

        streams = self.get_streams(usernames)

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
                        users = self.get_users(userids)
                        users = self._rekey_list(users,'id')
                        self.userCache.addDict(users)
                    if len(gameids) > 0:
                        games = self.get_games(gameids)
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

    def update_live_list(self, usernames):
        streams = self.current_live_data(usernames)
        started = {}
        stopped = {}

        if streams is not None:
            if len(streams) > 0:
                started = {k:v for (k,v) in streams.items() if k not in list(self.live.keys())}
                stopped = {k:v for (k,v) in self.live.items() if k not in list(streams.keys())}
            self.live = streams
        else:
            streams = {}

        return { 'started': started, 'stopped': stopped, 'streams': streams }

    def get_streams(self, usernames):
        """API request for stream information."""

        # https://api.twitch.tv/helix/streams?user_id=USER1&user_id=USER2
        api_url = '{}streams'.format(self.twitch_api_url_base)
        params = {'user_login': usernames}
        return self._make_request(api_url, params)

    def get_users(self, userids):
        """Get profile/data on users by ids."""

        # https://api.twitch.tv/helix/users?id=USER1&id=USER2
        api_url = '{}users'.format(self.twitch_api_url_base)
        params = {'id': userids}
        return self._make_request(api_url, params)

    def get_games(self, gameids):
        """Get game information by ids."""

        # https://api.twitch.tv/helix/games?id=GAME1&id=GAME2
        api_url = '{}games'.format(self.twitch_api_url_base)
        params = {'id': gameids}
        return self._make_request(api_url, params)

    def get_followers(self, userid):
        """Get follower count for one user."""

        # https://api.twitch.tv/helix/users/follows?to_id=userid
        api_url = '{}users/followers'.format(self.twitch_api_url_base)
        params = {'to_id': userid}
        return self._make_request(api_url,params)

    def _make_request(self, url, params):
        delay = self.retry_delay_init
        response = None

        for _ in range(self.retry_max):
            try:
                r = requests.get(url, params=params, headers=self.twitch_request_headers)
            except requests.exceptions.RequestException as e:
                log.error(e)
                response = None
            else:
                if r.status_code >= 500:
                    log.warning('API status code {} returned!'.format(r.status_code))
                    time.sleep(delay)
                    delay = 2 * delay
                    continue

                if r.status_code != 200:
                    log.warning('API status code {} returned!'.format(r.status_code))
                    response = None
                    break
                
                rr = int(r.headers['Ratelimit-Remaining'])
                if rr < 5:
                    log.warning('API rate limit remaining is {}!'.format(rr))

                response = r.json()['data']
                break

        return response

    def _get_slice(self, adict, key):
        """Return a slice of a dict indicated by key."""
        a = []
        for d in adict:
            a.append(d[key])
        return a
    
    def _rekey_list(self, alist, key):
        """Rekey a list into a dict indexed by given key."""
        newdict = {}
        for d in alist:
            newdict[d[key]] = d
        return newdict
