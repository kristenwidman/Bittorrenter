#!/usr/bin/env python

from pieces import *
from messages import *
from bitstring import BitArray

max_requests = 15

class ActiveTorrent(object):
    def __init__(self, torrent_info):
        self.torrent_info = torrent_info
        self.message_buffer = bytearray()
        self.interested = False
        self.peer_interested = False
        self.choked = True
        self.peer_choked = True
        self.peer_bitarray = BitArray(len(torrent_info.pieces_array)) 
        self.pending_requests = 0
        self.piece_downloading = MyPiece(self.torrent_info.piece_length)  #clear and restart when creating a new piece
        self.piece_number = 0   #increment this when creating a new piece?
        print 'number of blocks for this piece: ' + str(self.piece_downloading.block_number)
        self.requested_blocks = BitArray(self.piece_downloading.block_number)
        self.have_blocks = BitArray(self.piece_downloading.block_number)

    def deal_with_message(self,data):
        messages_to_send_list = []
        if self.message_buffer:
            self.message_buffer.extend(bytearray(data))
            #print "message buffer had info. it is now: " + repr(self.message_buffer)
        else:
            self.message_buffer = bytearray(data)
            #print "message buffer was empty.  it is now: " + repr(self.message_buffer)
        if self.message_buffer[1:20].lower() == "BitTorrent Protocol".lower():
            print "handshake received"
            self.message_buffer = self.decode_handshake(self.message_buffer, self.torrent_info)
            messages_to_send_list.append(repr(Interested()))
            self.interested = True
            #perhaps have error handling for if handshake is cut short
        if len(self.message_buffer) >= 4:
            message_length = bytes_to_number(self.message_buffer[0:4]) + 4
            #print "length of message expected: " + repr(message_length)
            #print "length of message in buffer: " + repr(len(self.message_buffer))
            if len(self.message_buffer) < message_length:    #debugging line
                print "message shorter than expected"        #debugging line
            while len(self.message_buffer) >= message_length:
                self.message_buffer, messages_to_send_list = self.parse_messages(messages_to_send_list)
                #print "message_buffer is now: " + repr(self.message_buffer) 
        return messages_to_send_list

    def get_next_request(self):
        #get next request
        pass  #use self.peer_bitarray and self.torrent_info

    def parse_messages(self, messages_to_send_list):
        message_obj, message = parse_message_from_response(self.message_buffer)
        print 'message type: ' + repr(type(message_obj))
        if isinstance(message_obj, Choke):
            self.choked = True
        if isinstance(message_obj, Unchoke):
            self.choked = False
            if self.interested:
                #messages_to_send_list.append(self.get_next_request()
                pass
        if isinstance(message_obj, Interested):
            self.peer_interested = True
        if isinstance(message_obj, NotInterested):
            self.peer_interested = False
        if isinstance(message_obj, Have):
            piece_index = message_obj.index
            print 'piece index: ' + repr(piece_index)
            piece_index = bytes_to_number(piece_index)
            self.peer_bitarray[piece_index] = 1
            print 'bitarray after have: ' + repr(self.peer_bitarray.bin)
            #request = self.get_next_request() #will need bitarray and torrent_info
        if isinstance(message_obj, Bitfield):
            bitarray = BitArray(bytes=message_obj.bitfield)
            self.peer_bitarray = bitarray[:len(self.peer_bitarray)]
            print 'self.peer_bitarray: ' + repr(self.peer_bitarray)
#send request
        if isinstance(message_obj, Request):
            #if !self.peer_choked && self.peer_interested:
                #send piece
            pass
        if isinstance(message_obj, Piece):
            print 'piece'    # do something with this
#send request
        if isinstance(message_obj, Cancel):
            print 'cancel'
        if isinstance(message_obj, Port):
            print 'port'
            #parse port and switch connection to that port
        return message, messages_to_send_list


    def decode_handshake(self, response, torrentObj):
        handshake = Handshake(response)
        other = response[68:]
        expected_peer_id = torrentObj.peer_id
        expected_info_hash = torrentObj.info_hash
        if (expected_info_hash != handshake.info_hash):
            #instead of throwing exception, we should send a cancel message
            raise Exception('info_hash does not match expected. Info hash expected: ' +
                            repr(expected_info_hash) + '. Info hash found: ' + repr(handshake.info_hash))
        return other
