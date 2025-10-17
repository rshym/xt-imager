#!/usr/bin/env python3

import os
import pathlib
import logging
import argparse
from typing import List
from string import printable
import gzip
import serial

logging.basicConfig(level=logging.INFO, format="[%(levelname)s] %(message)s")
log = logging.getLogger(__name__)


def main():
    """Main function"""

    parser = argparse.ArgumentParser(
        description='Flash image files through u-boot and tftp',
        formatter_class=argparse.ArgumentDefaultsHelpFormatter)


    parser.add_argument(
        'image',
        type=pathlib.Path,
        help='Name of the image file to flash')

    parser.add_argument(
        '-s',
        '--serial',
        default='/dev/ttyUSB0',
        help='Serial console to use')

    parser.add_argument(
        '-b',
        '--baud',
        default=921600,
        help='Baudrate')

    parser.add_argument(
        '-t',
        '--tftp',
        type=pathlib.Path,
        default="/srv/tftp",
        help="Path to the TFTP directory")

    parser.add_argument(
        '-l',
        '--loadaddr',
        default='0x58000000',
        help='loadaddr for u-boot, 0x.. format')

    parser.add_argument(
        '-m',
        '--mmc',
        default=0,
        help='MMC device in u-boot')

    parser.add_argument(
        '-b',
        '--buffersize',
        default=512*1024*1024,
        help='Buffer size, 512-bytes aligned')

    parser.add_argument(
        '--serverip',
        help='IP of the host that will be used TFTP transfer.')

    parser.add_argument(
        '--ipaddr',
        help='IP of the board that will be used TFTP transfer.')

    parser.add_argument(
        '-v',
        '--verbose',
        action="store_true",
        help='Print the output from the serial console')

    args = parser.parse_args()

    if not os.path.isdir(args.tftp):
        raise NotADirectoryError("-t parameter is not a directory")

    log.info("Use %s as a TFTP root.", {args.tftp})

    do_flash_image(args, args.tftp)

def do_flash_image(args, tftp_root):
    """Flash image to the eMMC"""

    log.info(args.image)

    conn = serial.Serial(port=args.serial, baudrate=args.baud, timeout=20)

    uboot_prompt = "=>"
    # Send 'CR', and check for one of the possible options:
    # - uboot_prompt appears, if u-boot console is already active
    # - u-boot is just starting, so we will get "Hit any key.."
    log.info('Waiting for u-boot prompt...')
    conn_send(conn, "\r")
    conn_wait_for_any(conn, [uboot_prompt, "Hit any key to stop autoboot:"], args.verbose)
    # In case we got "Hit any key", let's stop the boot
    conn_send(conn, "\r")
    conn_wait_for_any(conn, [uboot_prompt], args.verbose)

    image_size = os.path.getsize(args.image)

    chunk_filename = "chunk.bin.gz"
    chunk_size_in_bytes = args.buffersize

    f_img = open(args.image, "rb")

    bytes_sent = 0
    out_fullname = os.path.join(tftp_root, chunk_filename)

    if args.serverip:
        conn_send(conn, f"env set serverip {args.serverip}\r")
        conn_wait_for_any(conn, [uboot_prompt], args.verbose)

    if args.ipaddr:
        conn_send(conn, f"env set ipaddr {args.ipaddr}\r")
        conn_wait_for_any(conn, [uboot_prompt], args.verbose)

    conn_send(conn, f"env set loadaddr {args.loadaddr}\r")
    conn_wait_for_any(conn, [uboot_prompt], args.verbose)

    try:
        # do in loop:
        # - read X MB chunk from image file
        # - save chunk to file in tftp root
        # - tell u-boot to 'tftp-and-emmc' chunk
        while True:
            data = f_img.read(chunk_size_in_bytes)

            if not data:
                break

            # create chunk
            f_out = open(out_fullname, "wb")
            data_packed = gzip.compress(data, compresslevel=1)
            f_out.write(data_packed)
            f_out.close()
            conn_send(conn, f"tftp ${{loadaddr}} {chunk_filename}\r")
            # check that all bytes are transmitted
            conn_wait_for_any(conn, [f"Bytes transferred = {len(data_packed)}"], args.verbose)
            conn_wait_for_any(conn, [uboot_prompt], args.verbose)
            # write to eMMC
            conn_send(conn, f"gzwrite mmc {args.mmc} ${{loadaddr}} ${{filesize}} 400000 {bytes_sent:X}\r")
            conn_wait_for_any(conn, [uboot_prompt], args.verbose)

            bytes_sent += len(data)

            if args.verbose:
                # in the verbose mode we need to print progress on the new line
                # and move to the next line
                print('')
                end_of_string = '\n'
            else:
                # in the regular mode we print progress in one line
                end_of_string = '\r'

            if image_size:
                print(f"Progress: {bytes_sent:_}/{image_size:_} ({bytes_sent*100 // image_size}%)",
                    end=end_of_string)
            else:
                print(f"Progress: {bytes_sent:_}", end=end_of_string)
    finally:
        # remove chunk from tftp root
        os.remove(out_fullname)

    f_img.close()
    conn.close()

    if not args.verbose:
        # move to the next line, below the progress
        print('')
    log.info("Image was flashed successfully.")


def conn_wait_for_any(conn, expect: List[str], verbose: bool):
    """ Wait for any of the expected response from u-boot"""

    rcv_str = ""
    # stay in the read loop until any of expected string is received
    # in other words - all expected substrings are not in received buffer
    while all([x not in rcv_str for x in expect]):
        data = conn.read(1)
        if not data:
            raise TimeoutError(f"Timeout waiting for `{expect}` from the device")
        rcv_char = chr(data[0])
        if verbose and (rcv_char in printable or rcv_char == '\b'):
            print(rcv_char, end='', flush=True)
        rcv_str += rcv_char


def conn_send(conn, data):
    """ Send the string to the u-boot"""
    conn.write(data.encode("ascii"))


if __name__ == "__main__":
    main()
