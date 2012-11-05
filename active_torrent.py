#!/usr/bin/env python

import sys
import os
import bencode
from time import time
from bitstring import BitArray
from hashlib import sha1
import requests
from twisted.internet import reactor, task
from torrent import Torrent
from messages import *
from pieces import *
from bittorrenter import *
from constants import *

class ActiveTorrent(object):
    def __init__(self, torrent_file, writing_dir):
        self.torrent_info = self.get_torrent(torrent_file)
        self.peers = self.get_peers() 
        self.file_downloading = TorrentFile(self.torrent_info.overall_length, self.torrent_info.piece_length)
        self.requested_blocks = self.determine_block_number()
        self.have_blocks = self.determine_block_number()
        self.writing_dir = writing_dir 
        self.pending_timeout = dict()
        self.factory = BittorrentFactory(self)
        self.blocks_per_full_piece = self.torrent_info.piece_length / REQUEST_LENGTH 

    def determine_block_number(self):
        block_number = 0
        for piece in self.file_downloading.piece_list:
            block_number += piece.block_number
        return BitArray(block_number)

    def get_torrent(self,torrent_file):
        f = open(torrent_file, 'r')
        metainfo = bencode.bdecode(f.read())
        f.close()
        torrent_info = Torrent(metainfo)
        return torrent_info

    def connect(self, NUMBER_PEERS):
        number_connections = 0
        for peer in self.peers:
            if number_connections < NUMBER_PEERS:
                hostandport = peer.split(':')
                #print hostandport[0] + ':' + hostandport[1]
                reactor.connectTCP(hostandport[0], int(hostandport[1]), self.factory)
                number_connections += 1

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
                port = port_large + ord(c)
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
            k,v = item
            #v = item[1]
            #k = item[0]
            if (now - v) > PENDING_TIMEOUT:
                print 'pending request for block ' +str(k) +'is too old'
                del self.pending_timeout[k]
                self.requested_blocks[k] = 0
                piece_num, block_bytes_in_piece = self.determine_piece_and_block_nums(k) 
                block_index_in_piece = block_bytes_in_piece / REQUEST_LENGTH
                block_num_overall = self.piece_and_index_to_overall_index(block_index_in_piece, piece_num)
                request = self.format_request(piece_num, block_bytes_in_piece) 
                for protocol in self.factory.protocols:
                    if protocol.interested == True and protocol.choked == False:
                        protocol.transport.write(str(request))
                        self.requested_blocks[block_num_overall] = 1
                        self.pending_timeout[block_num_overall] = time()
                        print 'request sent for expired piece'
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
        piece.written = True
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
        directory = self.writing_dir + folder_name
        temp_file = directory + '/' + folder_name + '.temp'
        if os.getcwd() != directory:
            os.chdir(directory)
        info = self.torrent_info.info
        if 'files' in info:
            print 'multiple files. creating files and folders.'
            f_read = open(temp_file,'rb')
            files_list = info['files']
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
                data = f_read.read(length)
                f_write.write(data)
                #cleanup:
                f_write.close()
                os.chdir(directory) #move back to base dir                       
            f_read.close()
            #os.remove(temp_file)
        else:
            print 'single file. renaming'
            extension = self.torrent_info.folder_name.rsplit('.',1)[1]
            print 'temp file name: ' + temp_file
            print 'extension: ' + extension
            print 'current wd: ' + os.getcwd()
            print 'files in dir: '+repr(os.listdir(os.getcwd()))
            os.rename(temp_file, temp_file[:-4]+extension)  #just rename file with correct extension

    def format_request(self, piece_num, block_byte_offset):
        block_num_in_piece = block_byte_offset / REQUEST_LENGTH 
        piece = self.file_downloading.piece_list[piece_num]
        request_len = piece.block_list[block_num_in_piece].expected_length
        index_pack = pack('!l',piece_num)
        begin_pack = pack('!l', block_byte_offset)
        length_pack = pack('!l',request_len) 
        print 'generating request for piece: ' + str(piece_num)+' and block: ' + str(block_byte_offset / REQUEST_LENGTH)
#will be smaller than REQUEST_LEN for last block - need to account for that!
        request = Request(index=index_pack, begin=begin_pack, length=length_pack)
        #print 'request object created: ' + repr(request)
        return request 
        
    def clear_data(self, piece, piece_num):
        #write piece's blocks to empty (do a debug if_full check to verify)
        #set have and requested blocks for piect to 0
        print 'clear_data called because hashes did not match'
        for block_num, block in enumerate(piece.block_list):
            piece.write(block_num, '')
            block_num_overall = self.piece_and_index_to_overall_index(block_num, piece_num) 
            self.have_blocks[block_num_overall] = 0
            self.requested_blocks[block_num_overall] = 0
        print 'after clearing, is the piece full? (should be False) ' + piece.check_if_full()

    def check_hash(self, piece, piece_num):
        print 'piece ' + str(piece_num) + ' is full!'
        piece_string = ''
        for block in piece.block_list:
            piece_string += block.bytestring
        hash_calculated = sha1(piece_string)
        if hash_calculated.digest() == self.torrent_info.pieces_array[piece_num]:
            print 'hashes matched, writing piece'
            self.write_piece(piece,piece_num)
        else:
            print 'HASHES DID NOT MATCH'
            print '\thash calulated: ' + repr(hash_calculated.digest())
            print '\thash expected for piece '+str(piece_num) +' : ' + repr(self.torrent_info.pieces_array[piece_num])
            self.clear_data(piece,piece_num)

    def write_block(self,block):
        block_num_in_piece = bytes_to_number(block.begin) / REQUEST_LENGTH
        piece_num = bytes_to_number(block.index)
        piece = self.file_downloading.piece_list[piece_num]
        block_num_overall = self.piece_and_index_to_overall_index(block_num_in_piece, piece_num) 
        if self.have_blocks[block_num_overall] == 0:
            piece.write(block_num_in_piece, block.block)
            self.have_blocks[block_num_overall] = 1  #add block to have list
            print '\npiece ' + str(piece_num) +' and block '+ str(block_num_in_piece) + ' received'
        if block_num_overall in self.pending_timeout: #remove block from timeout pending dict
            del self.pending_timeout[block_num_overall]
        if piece.check_if_full() and not piece.written:
            self.check_hash(piece,piece_num)

    def determine_piece_and_block_nums(self, overall_block_num):
        piece_num, block_num_overall = self.overall_index_to_piece_and_index(overall_block_num)
        block_bytes_overall = self.block_index_to_bytes(block_num_overall)
        block_byte_offset = block_bytes_overall % self.torrent_info.piece_length 
        return piece_num, block_byte_offset

    def piece_and_index_to_overall_index(self, block_piece_index, piece_num):
        return block_piece_index + piece_num * self.blocks_per_full_piece

    def overall_index_to_piece_and_index(self, overall_block_index):
        piece_num = overall_block_index / self.blocks_per_full_piece
        block_index_in_piece = overall_block_index % self.blocks_per_full_piece
        return piece_num, block_index_in_piece

    def block_index_to_bytes(self, block_index):
        return block_index * REQUEST_LENGTH

def main():  #torrent list passed in eventually
    writing_dir = '/Users/kristenwidman/Downloads/'
    #t = ActiveTorrent('test.torrent',writing_dir)
    #t = ActiveTorrent('Audiobook - War and Peace Book 02 by Leo tolstoy [mininova].torrent',writing_dir)
    t = ActiveTorrent('Ebook-Alice_In_Wonderland[mininova].torrent',writing_dir)
    print t.peers
    t.connect(NUMBER_PEERS)

    l = task.LoopingCall(t.check_for_expired_requests)
    l.start(PENDING_TIMEOUT) #run every x seconds

    reactor.run()

if __name__ == "__main__":
    #main(sys.argv[1])
    main()

