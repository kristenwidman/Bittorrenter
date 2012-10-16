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
        return None, response
    length = bytes_to_number(response[0:4]) + 4
    if len(response) < length:
        return None, response
    elif response[0:4] == '\x00\x00\x00\x00':
        message_obj = Message('keep_alive')
    else:
        bytestring = response[:length]
        result = {
          '\x00': lambda: Message('choke'),
          '\x01': lambda: Message('unchoke'),
          '\x02': lambda: Message('interested'),
          '\x03': lambda: Message('not interested'),
          '\x04': lambda: Have(response=bytestring),
          '\x05': lambda: Bitfield(response=bytestring),
          '\x06': lambda: Request(response=bytestring),
          '\x07': lambda: Piece(response=bytestring),
          '\x08': lambda: Cancel(response=bytestring),
          '\x09': lambda: Port(response=bytestring),
        }[response[4]]()
        message_obj = result
    response = response[length:]
    return message_obj, response

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
    """This is for everything but Handshake"""
    protocol_args = []
    protocol_extended = None

    def __init__(self,**kwargs):
        if 'response' in kwargs:
            self.__setup_from_bytestring(kwargs['response'])
        elif set(self.protocol_args + ([self.protocol_extended] if self.protocol_extended else [])) == set(kwargs.keys()):
            self.__setup_from_args(kwargs)
        else:
            print 'asdf'
            print 'stuff from message class', set(self.protocol_args + [self.protocol_extended] if self.protocol_extended else [])
            print 'kwargs', set(kwargs.keys())
            raise Exception("Bad init values")

    def __setup_from_bytestring(self, bytestring):
        self.length = bytestring[0:4]
        if len(bytestring) > 4:
            self.msg_id = bytestring[4]
        else:
            self.msg_id = ''
        payload = bytestring[5:]
        for i, arg_name in enumerate(self.protocol_args):
            setattr(self, arg_name, payload[:4])
            payload = payload[4:]
        if self.protocol_extended:
            setattr(self, self.protocol_extened, payload)

    def __setup_from_args(self, kwargs):
        for arg_name in self.protocol_args:
            setattr(self, arg_name, kwargs[arg_name])
        if self.protocol_extended:
            setattr(self, self.protocol_extended, kwargs[self.protocol_extended])
        if isinstance(self, KeepAlive):
            self.length = number_to_bytes(sum([len(x) for x in kwargs.values()]))
        else:
            self.length = number_to_bytes(sum([len(x) for x in kwargs.values()]) + 1)

    def __repr__(self):
        s = ''
        s += self.length
        s += self.msg_id
        for i, arg_name in enumerate(self.protocol_args):
            getattr(self, arg_name)
        if self.protocol_extended:
            getattr(self, self.protocol_extened)
        return s

    def __len__(self):
        return bytes_to_number(self.length) + 4

class Have(Message):
    protocol_args = ['index']
    protocol_extended = None
    msg_id = '\x00\x00\x00\x04'

class Bitfield(Message):
    protocol_extended = 'bitfield'
    msg_id = 5

class KeepAlive(Message):
    msg_id = ''

class Request(Message):
    def __init__(self,**kwargs):
        self.msg_id = '\x06'
        self.args = ['index', 'begin', 'piece_length']
        if set(kwargs.keys()) == set(self.args):

            pass
        elif 'response' in kwargs:
            self.length = kwargs['response'][0:4]
            self.bitfield = kwargs['response'][5:]

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
#    print 257 == bytes_to_number('\x00\x00\x01\x01')
#    print determine_msg_type('\x00\x00\x00\x00trainling')
#    print determine_msg_type('\x00\x00\x00\x01\x01trainling')
#    print determine_msg_type('\x00\x00\x00\x01\x02trailing')
#    print determine_msg_type('\x00\x00\x00\x01\x03trailing')
    print 'have', repr(determine_msg_type('\x00\x00\x00\x05\x04\x00\x00\x00\x01trailing'))
    print 'have from args:', repr(Have(index='\x00\x00\x00\x03'))
#    print 'bitfield', determine_msg_type('\x00\x00\x00\x03\x05\xff\x00trailing')
#    print 'request', determine_msg_type('\x00\x00\x00\x0d\x06\x00\x00\x00\x01\x00\x00\x00\x02\x00\x00\x00\x03trailing')

