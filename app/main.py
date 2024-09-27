import json
import sys

import socket
import requests
import hashlib

from app.decoder import BencodeDecoder as B
from app.encode import encode as e
from app.peer_message import( 
    Msg,
    PeerMessage,
    CHUNK_SIZE
)
import threading
import queue



# import bencodepy - available if you need it!
# import requests - available if you need it!

# Examples:
#
# - decode_bencode(b"5:hello") -> b"hello"
# - decode_bencode(b"10:hello12345") -> b"hello12345"
def decode_bencode(bencoded_value):
    # print('\033[92m', "decoding......", bencoded_value, '\033[0m')
    if chr(bencoded_value[0]).isdigit(): # string
        first_colon_index = bencoded_value.find(b":")
        str_len = int(bencoded_value[:first_colon_index])
        if first_colon_index == -1:
            raise ValueError("Invalid encoded value")
        return bencoded_value[first_colon_index+1:]
    elif chr(bencoded_value[0]) =='i': # Number
        return int(bencoded_value[1:-1]) 
    elif chr(bencoded_value[0]) == 'l': # list
        first_element = ""
        if chr(bencoded_value[1]) =='i':
            first_e_index = bencoded_value.find(b"e")
            first_element = int(bencoded_value[2:first_e_index])
            if first_e_index < len(bencoded_value) - 2:
                return [first_element] + decode_bencode(b'l' + bencoded_value[first_e_index+1:])
            else: 
                return [first_element]
        elif chr(bencoded_value[1]).isdigit():
            first_colon_index = bencoded_value.find(b":")
            str_len = int(bencoded_value[1:first_colon_index])
            first_element = bencoded_value[first_colon_index+1: first_colon_index + 1 + str_len] 
            if str_len < len(bencoded_value) -3:
                return [first_element] + decode_bencode(b'l' + bencoded_value[first_colon_index + str_len + 1:])
            else: 
                return [first_element]
        elif chr(bencoded_value[1]) == 'e':
            return []
        else: 
            raise NotImplementedError("no nested support")
    else:
        raise NotImplementedError("Only strings are supported at the moment")


def main():
    command = sys.argv[1]

    # You can use print statements as follows for debugging, they'll be visible when running tests.
    if command == "decode":
        bencoded_value = sys.argv[2].encode()

        # json.dumps() can't handle bytes, but bencoded "strings" need to be
        # bytestrings since they might contain non utf-8 characters.
        #
        # Let's convert them to strings for printing to the console.
        def bytes_to_str(data):
            if isinstance(data, bytes):
                return data.decode()

            raise TypeError(f"Type not serializable: {type(data)}")

        # Uncomment this block to pass the first stage
        val = B(return_str=True).decode(bencoded_value)
        print(json.dumps(val, default=bytes_to_str))
    elif command in ["info", "peers", "handshake", "download_piece", "download"]:
        TorrentClient().process_request()
    else:
        raise NotImplementedError(f"Unknown command {command}")

class TorrentClient():
    def __init__(self):
        self.command = sys.argv[1]
        if self.command == "download_piece":
            self.tfile = sys.argv[4]
            self.ofile = sys.argv[3]
        elif self.command == "download":
            self.tfile = sys.argv[4]
            self.ofile = sys.argv[3]
        else:
            self.tfile = sys.argv[2]
        
        with open(self.tfile, 'rb') as f: 
            self.file_dict = B().decode(f.read())
            self.info_dict = self.file_dict[b"info"]
        
        be_dict = e(self.info_dict)
        self.info_hash = hashlib.sha1(be_dict)
        self.tracker_url = self.file_dict[b"announce"].decode().strip()
        self.max_piece_length = self.info_dict[b"piece length"]
        self.file_length = self.info_dict[b"length"]

        cp = self.info_dict[b"pieces"]
        self.pieces = []
        i = 0
        while i < len(cp):
            ph = cp[i:i + 20]
            self.pieces.append(ph.hex())
            i+=20

    def info(self):
        print("Tracker URL:", self.tracker_url)
        print("Length:", self.info_dict[b"length"])
        
        print("Info Hash:", self.info_hash.hexdigest())
        print("Piece Length:", self.max_piece_length)
        print("Piece Hashes:")
        i = 0 
        cp = self.info_dict[b"pieces"]
        
        while i < len(cp):
            ph = cp[i:i + 20]
            print(ph.hex())
            i+=20

    def peers(self):
        payload = {
                "info_hash": self.info_hash.digest(),
                "peer_id": "00112233445566778899",
                "port": 6881,
                "uploaded": 0,
                "downloaded": 0,
                "left": self.info_dict[b"length"],
                "compact": 1
        }
        response = requests.get(self.tracker_url, params=payload)
        response_bd = B().decode(response.content)

        peers = response_bd[b"peers"]
        i = 0
        plist = []
        while i < len(peers):
            peer = peers[i:i+6]
            p1 = peer[0]
            p2 = peer[1]
            p3 = peer[2]
            p4 = peer[3]

            port = int.from_bytes(peer[4:], 'big')
            plist.append(f"{p1}.{p2}.{p3}.{p4}:{port}")
            i += 6
        return plist
    
    def _handshake(self, s):
        message =  b"BitTorrent protocol" + bytes(8) + self.info_hash.digest() + \
                b"00112233445566778899"
        hs_message = int(19).to_bytes(1, 'big') + message
        s.send(hs_message)

    def handshake(self):
         # generate handshake message
        ip, port = sys.argv[3].split(':')
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.connect((ip, int(port)))
            self._handshake(s)
            msg_rcvd = s.recv(68)
            print(f"Peer ID: {msg_rcvd[48:].hex()}")

    def scratch(self):
        offsets = list(range(0, self.piece_length, CHUNK_SIZE))
        sizes = range(0, len(offsets)-1) + [self.piece_length - offsets[-1]]

        zip(offsets, sizes)

    def setup_socket(self, peer):
        ip, port = peer.split(":")
        pm = PeerMessage()
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.connect((ip, int(port)))
        self._handshake(s)
        print("handshake sent")
        
        # receing handshake
        s.recv(68) # why 68 ??
        print("handshake recved")
        bitfield = pm.recv(s, Msg.bitfield)

        pm.send(s, Msg.interested)
        pm.recv(s, Msg.unchoke)

        return s

    def worker(self, peer):
        s = self.setup_socket(peer)
        while True:
            piece_ix = self.q.get()
            print(f'Working on {piece_ix}')
            try:
                data = self.download_piece(s, piece_ix)
            except Exception as e:
                s = self.setup_socket(peer)
                continue
            self.full_file[piece_ix] = data
            print(f"Finished {piece_ix}") 
            self.q.task_done()     
            

    def download(self, peers):
        self.full_file = [None] * len(self.pieces)
        import queue
        self.q = queue.Queue()

        for i in range(3):
            import time; time.sleep(0.1)
            threading.Thread(target=self.worker, args=(peers[i % 3], ), daemon=True).start()
    
        print("total pieces", len(self.pieces))
        for i, _ in enumerate(self.pieces):
            self.q.put(i)
        
        self.q.join()

        with open(self.ofile, 'wb') as f:
            f.write(b"".join(self.full_file))


    def download_piece(self, s,  piece_ix):

        pm = PeerMessage()

        piece_length = min(
            self.max_piece_length, 
            self.file_length - piece_ix * self.max_piece_length
        )
        print("piece_index", piece_ix)
        print("piece_length", piece_length)
        blocks = []

        offsets = list(range(0, piece_length, CHUNK_SIZE))
        sizes = [CHUNK_SIZE] * (len(offsets)-1) + [piece_length - offsets[-1]]
        blocks = [None for _ in range(len(offsets))]
        print(list(zip(offsets, sizes)))

        it = list(zip(offsets, sizes))
        for i in range(0, len(it)):
            offset, size = it[i]
            pm.send_request(s, piece_ix, offset, size)
        # for _ in offsets:
            slot, block = pm.recv_piece(s)
            blocks[slot] = block

        data = b"".join(blocks)
        data_hash = hashlib.sha1(data)
        expected_hash = self.get_piece_hash(piece_ix)

        print(expected_hash, data_hash.digest())
        assert data_hash.digest() == expected_hash

        print("Download successfull!")
        return data

    def get_piece_hash(self, ix):
        start = ix * 20 
        end = start + 20
        piece_hash = self.info_dict[b"pieces"][start:end]
        return piece_hash

    
    def process_request(self):

        if self.command == "info":
            self.info()
        elif self.command == "peers":
            plist = self.peers()
            for p in plist:
                print(p)
        elif self.command == "handshake":
            self.handshake()
        elif self.command == "download_piece":
            peers = self.peers()  
            s = self.setup_socket(peers[1])
            piece_ix = int(sys.argv[5])
        
            data = self.download_piece(s, piece_ix)
            with open(self.ofile, 'wb') as f:
                f.write(data)
            s.close()
        elif self.command == "download":
            peers = self.peers()  
            self.download(peers)
        else:
            raise NotImplementedError(f"Unknown command {self.command}")


if __name__ == "__main__":
    main()
