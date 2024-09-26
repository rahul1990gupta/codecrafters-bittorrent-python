
from enum import Enum 

class Msg(Enum):
    choke = 0
    unchoke = 1
    interested = 2
    not_interested = 3
    have = 4
    bitfield = 5
    request = 6
    piece = 7
    cancel = 8


CHUNK_SIZE = 16 * 1024 
class PeerMessage:
    def __init__(self):
        pass 

    def send(self, s, msg_type):
        func_dict = {
            Msg.interested.value: self.send_interested,
            Msg.request.value: self.send_request,
        }

        func_dict[msg_type.value](s)

    def send_interested(self, s):
        msg = b"\x02"
        s.send(len(msg).to_bytes(4, "big") + msg)
    
    def send_request(self, s, piece_index, begin, curr_size):
        values = [
            Msg.request.value,
            int(piece_index),
            begin,
            curr_size 
        ]
        msg = b"".join([ v.to_bytes(4, "big")
            for v in values])
        full_mgs = len(msg).to_bytes(4, "big") + msg
        
        s.send(full_mgs)

    def recv(self, s, msg_type):
        func_dict = {
            Msg.bitfield.value: self.recv_bitfield,
            Msg.unchoke.value: self.recv_unchoke

        }

        func_dict[msg_type.value](s)

    def recv_bitfield(self, s):
        mlen = int.from_bytes(s.recv(4), "big")
        bf_buffer = s.recv(mlen)
        msg_type = bf_buffer[0] # 5 for bitfield
        print("bf rcved")
        bitfield = bf_buffer[1:]
        print("bitfield", bitfield)
        return bitfield 
    
    def recv_unchoke(self, s):
        unchoke_buffer = s.recv(5)
        assert unchoke_buffer[4] == Msg.unchoke.value 
    
    def recv_piece(self, s):
        buff = self.recv_msg(s) 
        key = buff[:1]
    
        assert int.from_bytes(key) == Msg.piece.value

        index = buff[1:5]
        offset = buff[5:9]
        # slot = int.from_bytes(buff[5:9], "big") // chunk_size
        return buff[9:]

    
    def recv_msg(self, s):
        mlen = 0
        while mlen == 0:
            mlen = int.from_bytes(s.recv(4), "big")
            # import time; time.sleep(0.5)
        
        print("--------", mlen)
        got = 0
        ret = b""
        while got < mlen:
            buff = s.recv(mlen-got)
            ret +=buff
            got += len(buff)
        return ret