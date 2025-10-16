# xt-imager

Flash big binary files through the u-boot and TFTP server to the eMMC on the R-CAR board.

Based on https://github.com/xen-troops/rcar_flash.

### Usage:
```
[sudo] xt-imager.py [-h] [-s SERIAL] [-b BAUD] [-t TFTP] [--serverip SERVERIP] [--ipaddr IPADDR] [-v] image
```

### Command line options:

```
-s
--serial
```
Serial device to be used for communications with the u-boot.
`/dev/ttyUSB0` is used if not provided.

```
-b
--baud
```
The baud rate to be used on the serial console. Default value is 921600.

```
-t
--tftp
```
Path to the root of the running TFTP server. If no path is specified,
then `/srv/tftp` isused.

```
--serverip
```
IP address of the host. If not provided, then u-boot will use it's
own settings from environment. If provided, then script will execute
`set serverip {SERVERIP}` before start of TFTP operations.

```
--ipaddr
```
IP address of the board. If not provided, then u-boot will use it's
own settings from environment. If provided, then script will execute
`set ipaddr {IPADDR}` before start of TFTP operations.

```
-v
--verbose
```
Print the output from the serial console. Pay attention, that this
option results in thousands of the lines of the text.

```
image
```
Path to the image file. Raw (.img) or .xz-packed files are acceptable.
This file will be split into chunks (`chunk.bin`),
that can be transmitted to the board by TFTP and flashed into eMMC
device 1 partition 0, starting from address 0.

### Examples of usage

Flash `full.img` using `/srv/tftp` as TFTP root, `/dev/ttyUSB0` as
serial console and set provided IP inside u-boot environment.
```
./xt-imager.py --serverip 10.10.1.15 --ipaddr 10.10.1.10 ./full.img
```
