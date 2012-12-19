#!usr/bin/env python
#kristen widman
#Oct 8, 2012

from time import time
from twisted.internet.protocol import Protocol, ClientFactory
import messages
from bitstring import BitArray
import constants

class BittorrentProtocol(Protocol):
    def __init__(self, factory):
        self.factory = factory
        self.peer_has_pieces = BitArray(len(self.factory.active_torrent.torrent_info.pieces_array))
        self.message_buffer = bytearray()
        self.pending_requests = 0
        self.interested = False
        self.peer_interested = False
        self.choked = True
        self.peer_choked = True
        self.message_timeout = time() #mark for sending KeepAlives

    def handshake(self, torrent_obj):
        '''Input: ip:port of a peer with the torrent files of interest
           Output: <fill this in>
           <fill this in>
        '''
        info_hash = torrent_obj.info_hash
        peer_id = torrent_obj.peer_id
        handshake = messages.Handshake(info_hash, peer_id)
        return handshake

    def connectionMade(self):
        handshake_msg = str(self.handshake(self.factory.active_torrent.torrent_info))
        self.transport.write(handshake_msg)
        self.message_timeout = time()

    def dataReceived(self,data):
        self.message_timeout = time()
        messages_to_send = self.deal_with_message(data)
        for i,message in enumerate(messages_to_send):
            if message is not None:
                self.transport.write(str(message))
                self.message_timeout = time()

    def deal_with_message(self,data):
        messages_to_send_list = []
        if self.message_buffer:
            self.message_buffer.extend(bytearray(data))
        else:
            self.message_buffer = bytearray(data)
        if self.message_buffer[1:20].lower() == "bittorrent protocol":
            print "handshake received"
            self.decode_handshake(self.factory.active_torrent.torrent_info)
            self.message_buffer = self.message_buffer[68:]
            messages_to_send_list.append(messages.Interested())
            self.interested = True
        if len(self.message_buffer) >= 4:
            message_length = messages.bytes_to_number(self.message_buffer[0:4]) + 4
            while len(self.message_buffer) >= message_length:
                messages_to_send_list = self.parse_messages(messages_to_send_list)
                message_length = messages.bytes_to_number(self.message_buffer[0:4])+4
        return messages_to_send_list

    def get_next_request(self):
        total_number_of_blocks = len(self.factory.active_torrent.bitarray_of_block_number())
        for i in range(total_number_of_blocks):
            piece_num, block_byte_offset = self.factory.active_torrent.determine_piece_and_block_nums(i)
            if (self.peer_has_pieces[piece_num] and
                    self.factory.active_torrent.have_blocks[i]==0 and
                    self.factory.active_torrent.requested_blocks[i]==0):
                if self.pending_requests <= constants.MAX_REQUESTS:
                    self.factory.active_torrent.requested_blocks[i] = 1
                    self.factory.active_torrent.pending_timeout[i] = time()
                    request = self.factory.active_torrent.format_request(piece_num, block_byte_offset)
                    self.pending_requests += 1
                    return request

    def parse_messages(self, messages_to_send_list):
        message_obj = self.parse_message_from_response()
        if isinstance(message_obj, messages.Choke):
            print 'messages.Choked'
            self.choked = True
        elif isinstance(message_obj, messages.Unchoke):
            print 'messages.Unchoked!'
            self.choked = False
            if self.interested:
                for i in range(5):
                    messages_to_send_list.append(self.get_next_request())
        elif isinstance(message_obj, messages.Interested):
            self.peer_interested = True
        elif isinstance(message_obj, messages.Interested):
            self.peer_interested = False
        elif isinstance(message_obj, messages.Have):
            piece_index = messages.bytes_to_number(message_obj.index)
            self.peer_has_pieces[piece_index] = 1
            if self.interested and not self.choked:
                messages_to_send_list.append(self.get_next_request())
        elif isinstance(message_obj, messages.Bitfield):
            bitarray = BitArray(bytes=message_obj.bitfield)
            self.peer_has_pieces = bitarray[:len(self.peer_has_pieces)]
            if self.interested and not self.choked:
                messages_to_send_list.append(self.get_next_request())
        elif isinstance(message_obj, messages.Request):
            print 'request'
            pass  #send piece
#TODO: implement sending pieces/serving torrents
        elif isinstance(message_obj, messages.Piece):
            self.pending_requests -= 1
            self.factory.active_torrent.write_block(message_obj)
            if self.interested and not self.choked:
                messages_to_send_list.append(self.get_next_request())
        elif isinstance(message_obj, messages.Cancel):
            print 'cancel'
        elif isinstance(message_obj, messages.Port):
            print 'port'
            #parse port and switch connection to that port
        return messages_to_send_list

    def decode_handshake(self, torrent_obj):
        handshake = messages.Handshake(self.message_buffer)
        expected_info_hash = torrent_obj.info_hash
        if (expected_info_hash != handshake.info_hash):
            #TODO: instead of throwing exception, we should send a cancel message or add deffered and errback
            raise Exception('info_hash does not match expected. Info hash expected: ' +
                            repr(expected_info_hash) + '. Info hash found: ' + repr(handshake.info_hash))

    def parse_message_from_response(self):
        length = messages.bytes_to_number(self.message_buffer[0:4]) + 4  #length indicated by the first 4 bytes + 4 for those first 4 bytes
        bytestring = self.message_buffer[:length]
        if self.message_buffer[0:4] == '\x00\x00\x00\x00':  #no msg_id
            message_obj = KeepAlive(response=bytestring)
        else:
            message_obj  = {
              0: lambda: messages.Choke(response=bytestring),
              1: lambda: messages.Unchoke(response=bytestring),
              2: lambda: messages.Interested(response=bytestring),
              3: lambda: messaged.Interested(response=bytestring),
              4: lambda: messages.Have(response=bytestring),
              5: lambda: messages.Bitfield(response=bytestring),
              6: lambda: messages.Request(response=bytestring),
              7: lambda: messages.Piece(response=bytestring),
              8: lambda: messages.Cancel(response=bytestring),
              9: lambda: messages.Port(response=bytestring),
            }[self.message_buffer[4]]()     #response[4] is the msg_id
        self.message_buffer = self.message_buffer[length:]
        return message_obj

    def connectionLost(self, reason):
        self.factory.protocols.remove(self)

class BittorrentFactory(ClientFactory):
    def __init__(self, active_torrent):
        self.protocols = []
        self.active_torrent = active_torrent

    def startedConnecting(self,connector):
        print 'Started to connect.'

    def buildProtocol(self,addr):  
        print 'Connected.'
        protocol = BittorrentProtocol(self)
        self.protocols.append(protocol)
        return protocol

    def clientConnectionLost(self,connector,reason):
        print 'Lost connection. Reason: ', reason
        #reconnect?

    def clientConnectionFailed(self,connector,reason):
        print 'Connection failed. Reason: ', reason

