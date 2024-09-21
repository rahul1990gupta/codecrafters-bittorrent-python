import json
import sys
from app.decoder import BencodeDecoder as B
from app.encode import encode as e
import socket
import requests
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
    if command in ["info", "peers", "handshake"]:
        process_fc(command, sys.argv[2])
        return

    if command == "decode":
        bencoded_value = sys.argv[2].encode()

        # json.dumps() can't handle bytes, but bencoded "strings" need to be
        # bytestrings since they might contain non utf-8 characters.
        #
        # Let's convert them to strings for printing to the console.
        def bytes_to_str(data):
            import pdb;pdb.set_trace()
            if isinstance(data, bytes):
                return data.decode()

            raise TypeError(f"Type not serializable: {type(data)}")

        # Uncomment this block to pass the first stage
        val = B(return_str=True).decode(bencoded_value)
        print(json.dumps(val, default=bytes_to_str))
    else:
        raise NotImplementedError(f"Unknown command {command}")


def process_fc(command, metafile):
    file_dict = {}
    info_dict = {}
    with open(metafile, 'rb') as f: 
        file_dict = B().decode(f.read())
        info_dict = file_dict[b"info"]
    be_dict = e(info_dict)
    import hashlib
 
    info_hash = hashlib.sha1(be_dict)
    tracker_url = file_dict[b"announce"].decode().strip()
    
    if command == "info":
        print("Tracker URL:", tracker_url)
        print("Length:", info_dict[b"length"])
        
        print("Info Hash:", info_hash.hexdigest())
        print("Piece Length:", info_dict[b"piece length"])
        print("Piece Hashes:")
        i = 0 
        cp = info_dict[b"pieces"]
        
        while i < len(cp):
            ph = cp[i:i + 20]
            print(ph.hex())
            i+=20

            """
            To calculate the info hash, you'll need to:

                Extract the info dictionary from the torrent file after parsing
                Bencode the contents of the info dictionary
                Calculate the SHA-1 hash of this bencoded dictionary
            """
    elif command == "peers":
        payload = {
                "info_hash": info_hash.digest(),
                "peer_id": "00112233445566778899",
                "port": 6881,
                "uploaded": 0,
                "downloaded": 0,
                "left": info_dict[b"length"],
                "compact": 1
        }
        response = requests.get(tracker_url, params=payload)
        response_bd = B().decode(response.content)
        peers = response_bd[b"peers"]
        i = 0
        while i < len(peers):
            peer = peers[i:i+6]
            p1 = peer[0]
            p2 = peer[1]
            p3 = peer[2]
            p4 = peer[3]

            port = int.from_bytes(peer[4:], 'big')
            print(f"{p1}.{p2}.{p3}.{p4}:{port}")
            i += 6
    elif command == "handshake":
        # generate handshake message
        """
        length of the protocol string (BitTorrent protocol) which is 19 (1 byte)
        the string BitTorrent protocol (19 bytes)
        eight reserved bytes, which are all set to zero (8 bytes)
        sha1 infohash (20 bytes) (NOT the hexadecimal representation, which is 40 bytes long)
        peer id (20 bytes) (you can use 00112233445566778899 for this challenge)
        """
        message =  b"BitTorrent protocol" + bytes(8) + info_hash.digest() + \
                b"00112233445566778899"

        handshake = int(19).to_bytes(1, 'big') + message
        ip, port = sys.argv[3].split(':')
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.connect((ip, int(port)))
            s.send(handshake)
            print(f"Peer ID: {s.recv(68)[48:].hex()}")
    else:
        raise NotImplementedError(f"Unknown command {command}")



if __name__ == "__main__":
    main()
