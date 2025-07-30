# Copyright (c) 2020, NVIDIA CORPORATION. All rights reserved.
#
# Permission is hereby granted, free of charge, to any person obtaining a
# copy of this software and associated documentation files (the "Software"),
# to deal in the Software without restriction, including without limitation
# the rights to use, copy, modify, merge, publish, distribute, sublicense,
# and/or sell copies of the Software, and to permit persons to whom the
# Software is furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT.  IN NO EVENT SHALL
# THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING
# FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER
# DEALINGS IN THE SOFTWARE.
#
# Build this Dockerfile by running the following commands:
#
#     $ cd /path/to/your/jetson-inference
#     $ docker/build.sh
#
# Also you should set your docker default-runtime to nvidia:
#     https://github.com/dusty-nv/jetson-containers#docker-default-runtime
#

ARG BASE_IMAGE=nvcr.io/nvidia/l4t-pytorch:r35.2.1-pth2.0-py3
#ARG BASE_IMAGE=nvcr.io/nvidia/l4t-base:r35.2.1
# ARG BASE_IMAGE=nvcr.io/nvidia/l4t-tensorrt:r8.6.2-devel
# ARG BASE_IMAGE=quay.io/rapyuta/oks_perception:devel

##############################
# Stage 1    ^`^t Build & Compile
##############################
FROM ${BASE_IMAGE} AS builder

ENV DEBIAN_FRONTEND=noninteractive
WORKDIR /jetson-inference

RUN apt-get update && \
    apt-get purge -y '*opencv*' || true && \
    apt-get install -y --no-install-recommends \
        cmake \
        nano \
        mesa-utils \
        lsb-release \
        gstreamer1.0-tools \
        gstreamer1.0-libav \
        gstreamer1.0-rtsp \
        gstreamer1.0-plugins-good \
        gstreamer1.0-plugins-bad \
        gstreamer1.0-plugins-ugly \
        libgstreamer-plugins-base1.0-dev \
        libgstreamer-plugins-good1.0-dev \
        libgstreamer-plugins-bad1.0-dev \
        python3-distutils \
        make \
        build-essential \
        python3-pip 
#&& \
#    && rm -rf /var/lib/apt/lists/* \
#    && apt-get clean

# make a copy of this cause it gets purged...
RUN mkdir -p /usr/local/include/gstreamer-1.0/gst
RUN cp -r /usr/include/gstreamer-1.0/gst/webrtc /usr/local/include/gstreamer-1.0/gst
RUN ls -ll /usr/local/include/ 
RUN ls -ll /usr/local/include/gstreamer-1.0/gst/webrtc


# 
# install python packages
#
#COPY python/training/detection/ssd/requirements.txt /tmp/pytorch_ssd_requirements.txt
#COPY python/www/flask/requirements.txt /tmp/flask_requirements.txt
#COPY python/www/dash/requirements.txt /tmp/dash_requirements.txt
RUN apt install python3-pip -y

RUN pip3 install --no-cache-dir --verbose --upgrade Cython
#    pip3 install --no-cache-dir --verbose -r /tmp/pytorch_ssd_requirements.txt && \
#    pip3 install --no-cache-dir --verbose -r /tmp/flask_requirements.txt 
#    pip3 install --no-cache-dir --verbose -r /tmp/dash_requirements.txt
     
#
# copy source
#
COPY jetson-utils utils
RUN apt install libnvinfer-dev -y
RUN apt install libsoup2.4-dev -y
RUN apt install libjson-glib-dev -y
RUN apt install libglew-dev -y
RUN apt install libgstrtspserver-1.0-dev -y
#
# build source
#
RUN cd utils &&   mkdir build && \
    cd build && \
    cmake ../ -DNVBUF_UTILS=OFF && \
    make -j$(nproc) && \
    make install && \
    /bin/bash -O extglob -c "cd /jetson-inference/build; rm -rf -v !($(uname -m)|download-models.*)" && \
    rm -rf /var/lib/apt/lists/* \
    && apt-get clean


##############################
WORKDIR /jetson-inference/python/www/
COPY /jetson-inference/python/www/camera_app /jetson-inference/python/www/camera_app
RUN pip3 install -r /jetson-inference/python/www/camera_app/requirements.txt
ENV SSL_CERT=/jetson-inference/data/cert.pem
ENV SSL_KEY=/jetson-inference/data/key.pem

CMD mkdir /jetson-inference/data && cd /jetson-inference/data && openssl req -x509 -newkey rsa:4096 -keyout key.pem -out cert.pem -sha256 -days 365 -nodes -subj '/CN=localhost' && python3 /jetson-inference/python/www/camera_app/app_new.py --headless
nu/libgomp.so.1:/lib/aarch64-linux-gnu/libGLdispatch.so.0
