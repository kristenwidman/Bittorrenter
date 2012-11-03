#!usr/bin/env python
#kristen widman
#Oct 10, 2012

import bencode
import hashlib
import random
import string

PEER_ID_START = '-KB1000-'
LOCAL_PORT = 59696

class Torrent(object):

    def __init__(self, metainfo):
        self.metainfo = metainfo
        self.announce_url = self.metainfo['announce']
        self.info = self.metainfo['info']
        sha_info = hashlib.sha1(bencode.bencode(self.info))
        self.info_hash = sha_info.digest()
        self.peer_id = self.generate_peer_id()
        self.uploaded = 0 #update later
        self.downloaded = 0 # update later
        self.overall_length = self.length_of_file()
        self.left = self.overall_length #udpate later to calculate as changes
        self.compact = 1
        self.no_peer_id = 0
        self.event = "started"
        self.port = LOCAL_PORT
        self.param_dict = {'info_hash':self.info_hash, 'peer_id':self.peer_id, 'port':self.port,
                    'uploaded':self.uploaded,'downloaded':self.downloaded, 'left':self.left, 
                'compact':self.compact, 'no_peer_id':self.no_peer_id, 'event':self.event}
        if 'name' in self.info:
            self.folder_name = self.info['name']
        else:
            self.folder_name = 'torrent'
        self.piece_length = self.info['piece length']
        pieces_hash = self.info['pieces']
        self.pieces_array = []    
        while len(pieces_hash) > 0:
            self.pieces_array.append(pieces_hash[0:20])
            pieces_hash = pieces_hash[20:]


    def length_of_file(self):
        '''Input: metainfo file (.torrent file)
	   Output: total length of the file(s) to be transferred
	    Determines the total length of files to be transferred using the length key 
	    in the files dictionary within the info dictionary.  Adds up lengths for all files
	    to get total length.
	'''
        info = self.metainfo['info']
        length = 0
        if 'length' in info:
            length = info['length']            #single file, return overall length
        else:
            files = info['files']              #files is a list of dictionaries
            for fileDict in files:
                length += fileDict['length']
        return length

    def generate_peer_id(self):
        '''Input: none
	    Output: a 20 byte string used as a unique ID for this client instance.
	    The structure of the peer_id here is taken from the PEER_ID_START variable
	    plus random characters (letters and digits) to make up the rest of the 20 bytes.
	    The PEER_ID_START follows the convention for peer_id outlined in the wiki.theory.
	    ort/BitTorrentSpecification doc.
	'''
        N = 20 - len(PEER_ID_START)
        end = ''.join(random.choice(string.ascii_lowercase + string.digits) for x in range(N))
        peer_id = PEER_ID_START + end
        return peer_id

