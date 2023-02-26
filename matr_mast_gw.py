#!/usr/bin/env python3

"""
Simple Matrix to Mastodon gateway:
Drop something into a Matrix room and within 24 hours it will
be posted on Mastodon (cron job etc. permitting) assuming
it meets certain contraints (max. # of chars, etc).
"""

import mastodon
import matrix_client.client
import sys
import re
import pathlib
import os
import datetime
import pytz
import urlextract
import logging

def sys_exit(msg, exit=True):
    logging.error(msg)
    if exit:
        sys.exit(-1)

class ReadToken:
    def __init__(self, token_file):
        token = pathlib.Path(token_file)
        token_file = re.sub('^\.\/', '', token_file)
        if token.name == token_file:
            token = pathlib.Path.home() / token_file
            if not (token.exists() and os.access(str(token), os.R_OK)):
                sys_exit(f'{token_file} does not exist or is not readable, aborting')

        with open(token) as f:
            self.token = f.read().strip()

    def get_token(self):
        return self.token
    
# Extract Matrix messages from room and delete if required
class Matrix_Handler(ReadToken):
    def __init__(self, url, token_file='.matr_access.txt'):
        super().__init__(token_file)
        self.url = url
        
    # Login into matrix and return room in question
    def get_room(self, room='mastodon'):
        client = matrix_client.client.MatrixClient(self.url, token=self.get_token())
        self.rooms = client.rooms
        for r_id, r_obj in self.rooms.items():
            if r_obj.display_name == room:
                return r_id

        sys_exit(f'Could not find room {room}, exiting')

    # Get all events within the last # of hours and delete if requested
    def get_texts(self, r_id, no_hours=48, delete=False):
        start_sec = int(datetime.datetime.now().timestamp()) - no_hours * 3600
        events = []
        # For deletion
        room = self.rooms[r_id]
        for event in room.get_events():
            if event['type'] == 'm.room.message':
                content = event['content']
                if 'msgtype' in content.keys() and content['msgtype'] == 'm.text' and \
                    'm.relates_to' not in content.keys() and event['origin_server_ts']//1000 >= start_sec:
                    events.append(event)

        texts = []
        for event in events:
            texts.append(event['content']['body'])
            if delete:
                room.redact_message(event['event_id'])

        return texts

class MastodonPost(ReadToken):
    def __init__(self, url, token_file='.mast_access.txt'):
        super().__init__(token_file)
        self.url = url
        self.mast = None
        self.time = None
        
    def login(self):
        self.mast = mastodon.Mastodon(api_base_url=self.url, access_token=self.get_token())

    # Post single toot
    # Parms:
    # TEXT: toot
    # STAGGERED: release toot immediately or later
    # INTERVAL: # of hours between toots
    def post(self, text, staggered=False, interval=12):
        if self.count_chars(text) > 500:
            sys_exit(f'Not posting "{text[:20]}"... as toot violates Mastodon\'s char limit', False)
        elif self.mast != None:
            if staggered:
                # First toot
                if self.time:
                    self.time += datetime.timedelta(hours=interval)
                else:
                    tz = pytz.timezone('Europe/Berlin')
                    # Mastodon rquirement - if scheduled time is given, it should be five minnutes in the future min.
                    self.time = datetime.datetime.now(tz) + datetime.timedelta(minutes=5, seconds=5)
                    
            self.mast.status_post(text, scheduled_at=self.time)
        else:
            sys_exit('Not logged into Mastodon, ignoring post')

    # Return URLs in text
    def get_urls(self, text):
        extract = urlextract.URLExtract()
        return extract.find_urls(text)

    # Count valid Mastodon addresses and return sum of chars *not* being counted
    def check_addresses(self, text):
        reg = re.compile('@\S+@\S+')
        res = 0
        for adr in reg.findall(text):
            res += len(''.join(adr.split('@')[2:]))
        
        return res

    # Count overall chars in  text according to Mastodon rules
    def count_chars(self, text):
        ctext = text
        url_list = self.get_urls(text)
        for url in url_list:
            ctext = ctext.replace(url, '')

        return len(ctext) + 23 * len(url_list) - self.check_addresses(text)
            
def main():    
    HOME = pathlib.Path.home()
    LOG_DIR = pathlib.Path(HOME, 'log')
    logging.basicConfig(filename=str(LOG_DIR/pathlib.Path(__file__).stem)+'.log', filemode='a', level=logging.DEBUG, format='%(asctime)s %(name)-12s %(levelname)-8s %(message)s')

    matrix = Matrix_Handler(MATRIX_SERVER_URL)
    room = matrix.get_room()
    mastodon = MastodonPost(MASTODON_SERVER_URL)
    mastodon.login()
    # If more than one toot stagger them
    texts = matrix.get_texts(room)
    staggered = len(texts) > 1
    for text in texts:
        mastodon.post(text, staggered)

if __name__ == '__main__':
    main()

