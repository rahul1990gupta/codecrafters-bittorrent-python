import json
import sys
from app.decoder import BencodeDecoder as B
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
            import pdb;pdb.set_trace()
            if isinstance(data, bytes):
                return data.decode()

            raise TypeError(f"Type not serializable: {type(data)}")

        # Uncomment this block to pass the first stage
        val = B(return_str=True).decode(bencoded_value)
        print(json.dumps(val, default=bytes_to_str))
    elif command == "info":
        metafile = sys.argv[2]
        with open(metafile, 'rb') as f: 
            info_dict = B().decode(f.read())
            # import pdb;pdb.set_trace()
            print("Tracker URL:", info_dict[b"announce"].decode().strip())
            print("Length:", info_dict[b"info"][b"length"])
    else:
        raise NotImplementedError(f"Unknown command {command}")


if __name__ == "__main__":
    main()
