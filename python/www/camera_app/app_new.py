#!/usr/bin/env python3
#
# Copyright (c) 2023, NVIDIA CORPORATION. All rights reserved.
#
# Permission is hereby granted, free of charge, to any person obtaining a
# copy of this software and associated documentation files (the 'Software'),
# to deal in the Software without restriction, including without limitation
# the rights to use, copy, modify, merge, publish, distribute, sublicense,
# and/or sell copies of the Software, and to permit persons to whom the
# Software is furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED 'AS IS', WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT.  IN NO EVENT SHALL
# THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING
# FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER
# DEALINGS IN THE SOFTWARE.
#

import os
import flask
import argparse
import time

from stream import Stream
from utils import rest_property
    
    
parser = argparse.ArgumentParser(formatter_class=argparse.RawTextHelpFormatter, epilog=Stream.usage())

parser.add_argument("--host", default='0.0.0.0', type=str, help="interface for the webserver to use (default is all interfaces, 0.0.0.0)")
parser.add_argument("--port", default=8050, type=int, help="port used for webserver (default is 8050)")
parser.add_argument("--ssl-key", default=os.getenv('SSL_KEY'), type=str, help="path to PEM-encoded SSL/TLS key file for enabling HTTPS")
parser.add_argument("--ssl-cert", default=os.getenv('SSL_CERT'), type=str, help="path to PEM-encoded SSL/TLS certificate file for enabling HTTPS")
parser.add_argument("--title", default='Oks camera image viewer', type=str, help="the title of the webpage as shown in the browser")
parser.add_argument("--input", default='webrtc://@:8554/input', type=str, help="input camera stream or video file")
parser.add_argument("--output", default='webrtc://@:8554/output', type=str, help="WebRTC output stream to serve from --input")
parser.add_argument("--use-udp", default=True, type=lambda x: (str(x).lower() in ['true', '1', 'yes']), help="use UDP streams from oks_perception instead of CSI cameras (default: True, use --use-udp=false to disable)")
parser.add_argument("--udp-base-port", default=5000, type=int, help="base UDP port for camera streams (default: 5000)")

args = parser.parse_known_args()[0]
    
    
# create Flask & stream instance
app = flask.Flask(__name__)
parser2 = argparse.ArgumentParser()
parser2.add_argument("--input")
parser2.add_argument("--output")
parser2.add_argument("--output-encoder")
parser2.add_argument("--input-rate", type=int)

# Define argument lists for each stream
args_list = [
    "--output-encoder=cpu",
    "--input-rate=5",
    "--input-width=640",
    "--input-height=480",
    "--input-flip=rotate-180"
]

# Camera configuration
if args.use_udp:
    # Add MJPEG codec for UDP/RTP streams (camera_manager sends RTP/JPEG)
    args_list.append("--input-codec=mjpeg")
    # Use UDP streams from oks_perception
    print("=== Using UDP streams from oks_perception ===")
    print("Make sure oks_perception is running with UDP streaming enabled:")
    print("  ./scripts/start_local_stream.sh")
    print("=" * 50)
    
    # UDP ports: 5000-5003 for cameras LEFT, REAR, FRONT, RIGHT
    ports = [0, 1, 2, 3]  # UDP port offsets
    labels = ["left", "rear", "front", "right"]
    input_prefix = f"udp://@:{args.udp_base_port}"  # Base UDP source
else:
    # Use CSI cameras directly (original behavior)
    print("=== Using CSI cameras directly ===")
    print("Note: This will not work if oks_perception is running")
    print("=" * 50)
    
    ports = [0, 3, 2, 1]  # CSI camera IDs
    labels = ["left", "right", "front", "back"]
    input_prefix = "csi://"

streams = []
webrtc_ports = []

for idx, port in enumerate(ports):
    if args.use_udp:
        # Use RTP protocol which is supported by jetson-utils
        # camera_manager sends RTP/JPEG to UDP ports
        # jetson-utils can receive with rtp:// protocol
        input_arg = f"--input=rtp://0.0.0.0:{args.udp_base_port + port}"
    else:
        # CSI camera: csi://0, csi://3, etc.
        input_arg = f"--input=csi://{port}"
    
    webrtc_ports.append(idx + 8554)
    output_arg = f"--output=webrtc://@:{8554 + idx}/output"
    
    this_args_list = [input_arg, output_arg]
    parsed_args = parser2.parse_args(this_args_list)
    
    print(f"Stream {idx}: {input_arg} -> {output_arg}")
    
    stream = Stream(parsed_args, args_list)
    streams.append(stream)

@app.route('/')
def index():
    return flask.render_template('index_new.html', title=args.title, send_webrtc=False,
                                 input_stream=args.input, output_stream=webrtc_ports, labels=labels)

    
# start stream thread
print("\nStarting camera streams...")
for idx, stream in enumerate(streams):
    print(f"  Starting stream {idx}: {labels[idx]}")
    stream.start()
    time.sleep(2)

print("\nAll streams started successfully!")
print(f"Web interface available at: http://{args.host}:{args.port}")

# check if HTTPS/SSL requested
ssl_context = None

if args.ssl_cert and args.ssl_key:
    ssl_context = (args.ssl_cert, args.ssl_key)
    
# start the webserver
app.run(host=args.host, port=args.port, ssl_context=ssl_context, debug=True, use_reloader=False)
