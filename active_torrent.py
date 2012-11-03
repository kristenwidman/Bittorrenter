#!/usr/bin/env python

import sys
import os
import bencode
import requests
from time import time
from twisted.internet import reactor, task
from torrent import Torrent
from messages import *
from pieces import *
from bitstring import BitArray
from bittorrenter import *

NUMBER_PEERS = 7
REQUEST_LENGTH = 2**14  #duplicate of what's in bittorrent.py; move to constants file
PENDING_TIMEOUT = 20    #number seconds til pending request is considered too old and a new request is made

class ActiveTorrent(object):
    def __init__(self, torrent_file, writing_dir):
        self.torrent_info = self.get_torrent(torrent_file)
        self.peers = self.get_peers() #k['10.242.11.108:8000']#self.get_peers()       
        self.file_downloading = TorrentFile(self.torrent_info.overall_length, self.torrent_info.piece_length)
        self.requested_blocks = self.determine_block_number()
        self.have_blocks = self.determine_block_number() #BitArray(self.torrent_info.length_of_file() / REQUEST_LENGTH)  #might be one extra?
        self.writing_dir = writing_dir 
        self.pending_timeout = dict()
        self.factory = BittorrentFactory(self)

    def connect(self, NUMBER_PEERS):
        number_connections = 0
        for peer in self.peers:
            if number_connections < NUMBER_PEERS:
                hostandport = peer.split(':')
                print hostandport[0] + ':' + hostandport[1]
                reactor.connectTCP(hostandport[0], int(hostandport[1]), self.factory)
                number_connections += 1

    def determine_block_number(self):
        block_number = 0
        for piece in self.file_downloading.piece_list:
            block_number += piece.block_number
        return BitArray(block_number)

    def parse_response_from_tracker(self,r):
        '''Input: http response from our request to the tracker
           Output: a list of peer_ids
           Takes the http response from the tracker and parses the peer ids from the 
           response. This involves changing the peer string from unicode (binary model)
           to a network(?) model(x.x.x.x:y). From the spec: 'First 4 bytes are the IP address and
           last 2 bytes are the port number'
        '''
        response = bencode.bdecode(r.content)
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
                i = 0
            elif i%6 == 4:
                peer_address += str(ord(c))
            else:
                peer_address += str(ord(c))+'.'
            i += 1
        return peer_list

    def get_torrent(self,torrent_file):
        f = open(torrent_file, 'r')
        metainfo = bencode.bdecode(f.read())
        f.close()
        torrent_info = Torrent(metainfo)
        return torrent_info

    def get_peers(self):
        '''Input: metainfo file (.torrent file)
           Output: a list of peer_ids (strings) returned from the tracker
           Calls methods to send an http request to the tracker, parse the returned
           result message and return a list of peer_ids
        '''
        r = requests.get(self.torrent_info.announce_url, params=self.torrent_info.param_dict)
        peers = self.parse_response_from_tracker(r)
        return peers

    def handshake(self, torrent_obj):
        '''Input: ip:port of a peer with the torrent files of interest
           Output: <fill this in>
           <fill this in>
        '''
        info_hash = torrent_obj.info_hash
        peer_id = torrent_obj.peer_id
        handshake = Handshake(info_hash, peer_id)
        return handshake

    def check_for_expired_requests(self):
        print "\nChecking for expired requests"
        now = time()
        pairs = [(k,v) for (k,v) in self.pending_timeout.iteritems()]
        for item in pairs:             
            #if value more than x seconds before now, remove key and set pending_requests to 0 for key
            v = item[1]
            k = item[0]
            if (now - v) > PENDING_TIMEOUT:
                print 'pending request for block ' +str(k) +'is too old'
                del self.pending_timeout[k]
                self.requested_blocks[k] = 0
                for protocol in self.factory.protocols:
                    piece_num, block_bytes_in_piece = protocol.determine_piece_and_block_nums(k) #Duplicate computation!
                    request = protocol.format_request(piece_num, block_bytes_in_piece) #Ditto above!
                    protocol.transport.write(str(request))
                    print 'request sent for expired piece'
#need to send a new request for this piece, or have a timer that sends requests in loop -- otherwise, can end up with a missing piece that never gets delivered.  Or send a request for this piece to ALL peers - might be more reliable

#should send a cancel to peer that we initially requested this from; (and send another request?)
#how to do this?

    def write_piece(self, piece, piece_num):
        #folder_name = self.torrent_info.folder_name
        folder_name = self.torrent_info.folder_name.rsplit('.',1)[0] #if a single file, this takes off the extension       
        #if directory exists, move to it; if not, create it
        if os.getcwd() != self.writing_dir + folder_name:
            print "Making New Directory"
            os.chdir(self.writing_dir)
            try:
                os.mkdir(folder_name)  #if can't create dir, then already exists and file has been partially downloaded before probably
            except:
                open(folder_name + '/' + folder_name + '.temp', 'w').close() #clears file of all contents if exists
            os.chdir(folder_name)
        file_name = folder_name + '.temp'
        piece_offset = piece_num * self.torrent_info.piece_length
        f = open(file_name, 'ab') #append to file so does not truncate
        for i,block in enumerate(piece.block_list):
            f.seek(piece_offset + i * REQUEST_LENGTH)
            f.write(block.bytestring)
        f.close()
        self.check_if_done()
#send have messages to all peers with piece num; how to do this?

    def check_if_done(self):
        print 'Checking if complete'
        if all(self.have_blocks):
            print '\nTorrent completely downloaded!\n'
            reactor.stop() #download complete, stop the reactor loop
            self.write_all_files()

    def write_all_files(self):
        print 'writing final files'
        folder_name = self.torrent_info.folder_name.rsplit('.',1)[0]
        print 'folder name: ' + folder_name
        #file_name, extension = self.torrent_info.folder_name.rsplit('.',1)        
        directory = self.writing_dir + folder_name
        temp_file = directory + '/' + folder_name + '.temp'
        if os.getcwd() != directory:
            os.chdir(directory)
        info = self.torrent_info.info
        if 'files' in info:
            print 'multiple files. creating files and folders.'
            f_read = open(temp_file,'rb')
            files_list = info['files']
            #seek_length = 0
            for element in files_list:
                path_list = element['path']
                print 'path: ' + repr(path_list)
                length = element['length']
                i = 0
                while i + 1 < len(path_list):  #create directory structure
                    if not os.path.isdir(path_list[i]): #folder does not exist yet
                        print 'creating new directory called: ' + path_list[i]
                        os.mkdir(path_list[i])
                    os.chdir(path_list[i])
                    i += 1
                f_write = open(path_list[-1], 'wb')
                print 'writing file '+ repr(path_list[-1])
                #f_read = open(temp_file,'rb')
                #f_read.seek(seek_length)
                data = f_read.read(length)
                f_write.write(data)
                #seek_length += length  #do I need a +1 here?
                #cleanup:
                f_write.close()
                #f_read.close()  
#what about just keeping the f_read file open throughout - would not need to seek (I think)
                os.chdir(directory) #move back to base dir                       
            f_read.close()
        else:
            print 'single file. renaming'
            extension = self.torrent_info.folder_name.rsplit('.',1)[1]
            print 'temp file name: ' + temp_file
            print 'extension: ' + extension
            print 'current wd: ' + os.getcwd()
            print 'files in dir: '+repr(os.listdir(os.getcwd()))
            os.rename(temp_file, temp_file[:-4]+extension)  #just rename file with correct extension
        
def main():  #torrent list passed in eventually
    writing_dir = '/Users/kristenwidman/Downloads/'
    #t = ActiveTorrent('test.torrent',writing_dir)
    #t = ActiveTorrent('Audiobook - War and Peace Book 02 by Leo tolstoy [mininova].torrent',writing_dir)
    t = ActiveTorrent('Ebook-Alice_In_Wonderland[mininova].torrent',writing_dir)
    print t.peers
    t.connect(NUMBER_PEERS)

    l = task.LoopingCall(t.check_for_expired_requests)
    l.start(16.0) #run every 31 seconds

    reactor.run()

if __name__ == "__main__":
    #main(sys.argv[1])
    main()

