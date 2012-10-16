#!usr/bin/env python

#kristen widman
#Oct 15, 2012


def number_to_bytes(number):  #returns a number 4 bytes long
    if number < 255:
        length = '\x00\x00\x00' + chr(number)
    elif number < 256**2:
        length = '\x00\x00' + chr((number)/256) + chr((number) % 256)
    elif number < 256**3:
        length = ('\x00'+ chr((number)/256**2) + chr(((number) % 256**2) / 256) +
            chr(((number) % 256**2) % 256))
    else:
        length = (chr((number)/256**3) + chr(((number)%256**3)/256**2) + chr((((number)%256**3)%256**2)/256) + chr((((number)%256**3)%256**2)%256))
    return length

def bytes_to_number(bytestring):  #assumed to be 4 bytes long
    number = 0
    i = 3
    for byte in bytestring:
        number += ord(byte) * 256**i
        i -= 1
    return number

def determine_msg_type(response):
    if len(response) < 4:
        return None,response
    length = bytes_to_number(response[0:4]) + 4
    if len(response) < length:
        return None,response
    elif response[0:4] == '\x00\x00\x00\x00':
        message_obj = Message('keep_alive')
    else:
        bytestring = response[:length]
        result = {
          '\x00': Message('choke'),
          '\x01': Message('unchoke'),
          '\x02': Message('interested'),
          '\x03': Message('not interested'),
          '\x04': Have(bytestring),
          '\x05': Bitfield(bytestring),
          '\x06': Request(bytestring),
          '\x07': Piece(bytestring),
          '\x08': Cancel(bytestring),
          '\x09': Port(bytestring),
        }[response[4]]
        message_obj = result
    response = response[length:]
    return message_obj,response

class Handshake(object):
    """Represents a handshake object"""
    def __init__(self,*args):
        if len(args) == 1: self.__setup1(*args)
        elif len(args) == 5: self.__setup2(*args)

    def __setup1(self,payload):
        self.pstrlen = payload[0]
        self.pstr = payload[1:20]  #may not always be 19
        self.reserved = payload[20:28]
        self.info_hash = payload[28:48]
        self.peer_id = payload[48:68]

    def __setup2(self,pstrlen,pstr,reserved,info_hash,peer_id):
        self.pstrlen = pstrlen
        self.pstr = pstr
        self.reserved = reserved
        self.info_hash = info_hash
        self.peer_id = peer_id

    def __repr__(self):
        return repr(self.pstrlen+self.pstr+self.reserved+self.info_hash+self.peer_id)

    def __len__(self):
        return 49+ord(self.pstrlen)

class Message(object):
    def __init__(self,*args):
        if len(args) == 1: self.__setup1(*args)
        elif len(args) > 1: self.__setup2(*args)

    def __setup1(self,payload):
        self.length = payload[0:4]
        if len(payload) > 4:
            self.msg_id = payload[4]
    
    def __setup2(self,length,msg_id):
        self.length = length
        self.msg_id = msg_id

    def __repr__(self):
        return self.length + self.msg_id

    def __len__(self):
        return bytes_to_number(self.length) + 4

class Have(Message):
    def __init__(self,**kwargs):
        self.length = '\x00\x00\x00\x05'  #or '5'
        self.msg_id = '\x04'   #or '4'
        if index in kwargs:
            self.byte_index = number_to_bytes(index) 
        elif response in kwargs:
            self.byte_index = response[5:9]

    def __repr__(self):
        return repr(self.length + self.msg_id + self.byte_index)
    
    def __len__(self):
        return bytes_to_number(self.length)+4

    @property
    def index(self):
        return bytes_to_number(self.byte_index)

class Bitfield(Message):
    def __init__(self, **kwargs):
        self.msg_id = '\x05'
        if bitfield in kwargs:
            self.bitfield = bitfield  #assumes sending bitfield as byte string
            self.length = number_to_bytes(len(self.bitfield + 1))
        elif response in kwargs:
            self.length = response[0:4]
            self.bitfield = response[5:]
        #need to determine length of response and deal with bitfield len or always pass in parameters that create exactly one object, no extra chars

    def __repr__(self):
        return repr(self.length + self.msg_id + self.bitfield) 

    def __len__(self):
        return bytes_to_number(self.length)+4

class Request(Message):
    def __init__(self,*args):
        if len(args) == 1: self.__setup1(*args)
        elif len(args) == 5: self.__setup2(*args)

    def __setup1(self, payload):
        Message.__init__(self,payload)
        self.index = payload[5:9]
        self.begin = payload[9:13]
        self.msg_length = payload[13:]

    def __setup2(self, length, msg_id, index, begin, msg_length):
        Message.__init__(self,length,msg_id)
        self.index = index
        self.begin = begin
        self.msg_length = msg_length

    def __repr__(self):
        return repr(self.length + self.msg_id + self.index + self.begin + self.msg_length)

class Piece(Message):
    def __init__(self, *args):
        if len(args) == 1: self.__setup1(*args)
        elif len(args) == 5: self.__setup2(*args)

    def __setup1(self, payload):
        Message.__init__(self,payload)
        self.index = payload[5:9]
        self.begin = payload[9:13]
        self.block = payload[13:]

    def __setup2(self, length, msg_id, index, begin, block):
        Message.__init__(self,length, msg_id)
        self.index = index
        self.begin = begin
        self.block = block

    def __repr__(self):
        return repr(self.length + self.msg_id + self.index + self.begin + self.block)

class Cancel(Message):   
    def __init__(self,*args):
        if len(args) == 1: self.__setup1(*args)
        elif len(args) == 5: self.__setup2(*args)

    def __setup1(self, payload):
        Message.__init__(self,payload)
        self.index = payload[5:9]
        self.begin = payload[9:13]    
        self.msg_length = payload[13:]

    def __setup2(self, length, msg_id, index, begin, msg_length):
        Message.__init__(self,length,msg_id)
        self.index = index
        self.begin = begin
        self.msg_length = msg_length

    def __repr__(self):
        return repr(self.length + self.msg_id + self.index + self.begin + self.msg_length)

class Port(Message):
    def __init__(self, *args):
        if len(args) == 1: self.__setup1(*args)
        elif len(args) == 3: self.__setup2(*args)

    def __setup1(self,payload):
        Message.__init__(self,payload)
        self.port = payload[5:]

    def __setup2(self, length, msg_id, port):
        Message.__init__(self,length,msg_id)
        self.port = port

    def __repr__(self):
        return repr(self.length + self.msg_id + self.port)

if __name__ == '__main__':
    print 257 == bytes_to_number('\x00\x00\x01\x01')
    print determine_msg_type('\x00\x00\x00\x00')



