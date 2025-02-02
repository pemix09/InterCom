#!/usr/bin/env python
# PYTHON_ARGCOMPLETE_OK

'''Chunk compression by byte-planes using DEFLATE. 24 bits/sample. 4 code-streams.'''

import zlib
import numpy as np
import struct
import math
import minimal
import compress
import logging

class Compression3_24(compress.Compression):
    def __init__(self):
        super().__init__()
        logging.info(__doc__)

    def pack(self, chunk_number, chunk):
        assert np.all( abs(chunk) < (1<<24) )
        #chunk += 32768
        #channel_0_MSB2 = (chunk[:, 0] // (1<<24)).astype(np.int8)
        channel_0_MSB1 = (chunk[:, 0] // (1<<16)).astype(np.int8)
        channel_0_MSB0 = (chunk[:, 0] // (1<<8)).astype(np.uint8)
        channel_0_LSB  = (chunk[:, 0] % (1<<8)).astype(np.uint8)
        #channel_1_MSB2 = (chunk[:, 1] // (1<<24)).astype(np.int8)
        channel_1_MSB1 = (chunk[:, 1] // (1<<16)).astype(np.int8)
        channel_1_MSB0 = (chunk[:, 1] // (1<<8)).astype(np.uint8)
        channel_1_LSB  = (chunk[:, 1] % (1<<8)).astype(np.uint8)
        #MSB2 = np.concatenate([channel_0_MSB2, channel_1_MSB2])
        MSB1 = np.concatenate([channel_0_MSB1, channel_1_MSB1])
        MSB0 = np.concatenate([channel_0_MSB0, channel_1_MSB0])
        LSB  = np.concatenate([channel_0_LSB, channel_1_LSB])
        #compressed_MSB2 = zlib.compress(MSB2)
        compressed_MSB1 = zlib.compress(MSB1)
        compressed_MSB0 = zlib.compress(MSB0)
        compressed_LSB  = zlib.compress(LSB)
        packed_chunk = struct.pack("!HHH", chunk_number, len(compressed_MSB1), len(compressed_MSB0)) + compressed_MSB1 + compressed_MSB0 + compressed_LSB 
        return packed_chunk

    def unpack(self, packed_chunk):
        (chunk_number, len_compressed_MSB1, len_compressed_MSB0) = struct.unpack("!HHH", packed_chunk[:6])
        offset = 6 # Header size
        #compressed_MSB2 = packed_chunk[offset : len_compressed_MSB2 + offset]
        #offset += len_compressed_MSB2
        compressed_MSB1 = packed_chunk[offset : len_compressed_MSB1 + offset]
        offset += len_compressed_MSB1 
        compressed_MSB0 = packed_chunk[offset : len_compressed_MSB0 + offset]
        offset += len_compressed_MSB0 
        compressed_LSB = packed_chunk[offset :]
        #buffer_MSB2 = zlib.decompress(compressed_MSB2)
        buffer_MSB1 = zlib.decompress(compressed_MSB1)
        buffer_MSB0 = zlib.decompress(compressed_MSB0)
        buffer_LSB  = zlib.decompress(compressed_LSB)
        #channel_MSB2 = np.frombuffer(buffer_MSB2, dtype=np.int8)
        channel_MSB1 = np.frombuffer(buffer_MSB1, dtype=np.int8)
        channel_MSB0 = np.frombuffer(buffer_MSB0, dtype=np.uint8)
        channel_LSB  = np.frombuffer(buffer_LSB, dtype=np.uint8)
        chunk = np.empty((minimal.args.frames_per_chunk, 2), dtype=np.int32)
        chunk[:, 0] = channel_MSB1[:len(channel_MSB1)//2]*(1<<16) + channel_MSB0[:len(channel_MSB0)//2]*(1<<8) + channel_LSB[:len(channel_LSB)//2]
        chunk[:, 1] = channel_MSB1[len(channel_MSB1)//2:]*(1<<16) + channel_MSB0[len(channel_MSB0)//2:]*(1<<8) + channel_LSB[len(channel_LSB)//2:]
        #chunk -= 32768
        return chunk_number, chunk

class Compression3_24__verbose(Compression3_24, compress.Compression__verbose):

    def __init__(self):
        super().__init__()

    def unpack(self, packed_chunk):
        (chunk_number, len_compressed_MSB1, len_compressed_MSB0) = struct.unpack("!HHH", packed_chunk[:6])
        len_compressed_LSB = len(packed_chunk) - (len_compressed_MSB1 + len_compressed_MSB0 + 6)

        # Ojo, que esto no son los bps / canal
        self.bps[1] += (len_compressed_MSB1 + len_compressed_MSB0)*8
        self.bps[0] += len_compressed_LSB*8
        return Compression3_24.unpack(self, packed_chunk)

try:
    import argcomplete  # <tab> completion for argparse.
except ImportError:
    logging.warning("Unable to import argcomplete (optional)")

if __name__ == "__main__":
    minimal.parser.description = __doc__
    try:
        argcomplete.autocomplete(minimal.parser)
    except Exception:
        logging.warning("argcomplete not working :-/")

    minimal.args = minimal.parser.parse_known_args()[0]
    if minimal.args.show_stats or minimal.args.show_samples:
        intercom = Compression3_24__verbose()
    else:
        intercom = Compression3_24()
    try:
        intercom.run()
    except KeyboardInterrupt:
        minimal.parser.exit("\nInterrupted by user")
