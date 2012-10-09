#!usr/bin/env python

#kristen widman
#Oct 8, 2012

import sys
import bencode
import hashlib
import random
import string
import requests
import urllib

local_port = 59696
peer_id_start = '-KB1000-'

def length_of_file(metainfo):
    '''Input: metainfo file (.torrent file)
       Output: total length of the file(s) to be transferred
       Determines the total length of files to be transferred using the length key 
	in the files dictionary within the info dictionary.  Adds up lengths for all files 
        to get total length.
    '''
    info = metainfo['info'] 
    length = 0
    if 'length' in info:
	length = info['length']            #single file, return overall length
    else:
	files = info['files']              #files is a list of dictionaries
	for fileDict in files:
	    length += fileDict['length']
	return length

def generate_peer_id():
    '''Input: none
       Output: a 20 byte string used as a unique ID for this client instance.
       The structure of the peer_id here is taken from the peer_id_start variable
       plus random characters (letters and digits) to make up the rest of the 20 bytes.
       The peer_id_start follows the convention for peer_id outlined in the wiki.theory.
       ort/BitTorrentSpecification doc.
    '''
    N = 20 - len(peer_id_start) 
    end = ''.join(random.choice(string.ascii_lowercase + string.digits) for x in range(N))
    peer_id = peer_id_start + end
    return peer_id

def get_parameters(metainfo):
    '''Input: metainfo file (.torrent file)
       Output: a dictionary containing all parameters for our http request to the tracker
       The request to the tracker for peer info has several needed and optional parameters.
       This method calculates the parameters and sets up the dictionary containing them.
    '''
#note to self: consider making this info a separate object class
    info = metainfo['info']                
    sha_info=hashlib.sha1(bencode.bencode(info))  
    info_hash = sha_info.digest()
    peer_id=generate_peer_id()
    uploaded=0 #update later
    downloaded=0 # update later
    left=length_of_file(metainfo) #udpate later to calculate as changes
    compact=1
    no_peer_id=0
    event="started"
    param_dict = {'info_hash':info_hash, 'peer_id':peer_id, 'port':local_port, 'uploaded':uploaded, 
	    'downloaded':downloaded, 'left':left, 'compact':compact, 'no_peer_id':no_peer_id, 'event':event}
    return param_dict

def parse_response_from_tracker(r):
    '''Input: http response from our request to the tracker
       Output: a list of peer_ids
       Takes the http response from the tracker and parses the peer ids from the 
       response. This involves changing the peer string from unicode (binary model)
       to a network(?) model(x.x.x.x:y). From the spec: 'First 4 bytes are the IP address and
       last 2 bytes are the port number'
    '''
    #print r.url
    #print r.text
    response = bencode.bdecode(r.text)
    #print response
    peers = response['peers']
    i=1
    peer_address = ''
    peer_list = []
    for c in peers:
	if i%6 == 5:
	    port_large = ord(c)*256
	elif i%6 == 0:
	    port_small = ord(c)
	    port = port_large+port_small
	    peer_address += ':'+str(port)
	    peer_list.append(peer_address)
	    peer_address = ''
	elif i%6 == 4:
	    peer_address += str(ord(c))
	else:
	    peer_address += str(ord(c))+'.'
	i += 1
    print str(peer_list)
    return peer_list

def get_peers(metainfo):
    '''Input: metainfo file (.torrent file)
       Output: a list of peer_ids (strings) returned from the tracker
       Calls methods to send an http request to the tracker, parse the returned
       result message and return a list of peer_ids
    '''
    announce_url = metainfo['announce']
    parameter_list = get_parameters(metainfo)
    r = requests.get(announce_url, params=parameter_list)
    peers = parse_response_from_tracker(r)

def main(torrentFile):
    f = open(torrentFile, 'r')
    metainfo = bencode.bdecode(f.read())
    f.close()
    #f2 = open('/Users/kristenwidman/Documents/Programs/Bittorrenter/metainfo.txt','w')
    #f2.write(str(metainfo))
    peers = get_peers(metainfo)
    #f2.close()

if __name__ == "__main__":
    main(sys.argv[1])


