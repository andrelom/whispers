#
# Main

FROM ubuntu:22.04 AS main

ENV DEBIAN_FRONTEND=noninteractive

# Install dependencies for building the application,
# as well as Python 3 and pip.
RUN apt-get update && \
  apt-get install -y --no-install-recommends \
  build-essential \
  cmake \
  git \
  libairspy-dev \
  libairspy0 \
  libpython3-dev \
  libtool \
  libusb-1.0-0 \
  libusb-1.0-0-dev \
  pkg-config \
  python3 \
  python3-pip \
  python3-setuptools \
  python3-wheel \
  swig \
  python3-numpy && \
  apt-get clean && rm -rf /var/lib/apt/lists/*

# Install SoapySDR core library.
RUN git clone --depth=1 https://github.com/pothosware/SoapySDR.git && \
  cd SoapySDR && \
  mkdir build && cd build && \
  cmake .. -DENABLE_PYTHON3=ON && \
  make -j"$(nproc)" && \
  make install && \
  ldconfig && \
  cd ../.. && rm -rf SoapySDR

# Install SoapyAirspy support.
RUN git clone --depth=1 https://github.com/pothosware/SoapyAirspy.git && \
  cd SoapyAirspy && \
  mkdir build && cd build && \
  cmake .. && \
  make -j"$(nproc)" && \
  make install && \
  ldconfig && \
  cd ../.. && rm -rf SoapyAirspy

# Install RTL-SDR core library.
RUN git clone --depth=1 https://github.com/osmocom/rtl-sdr.git && \
  cd rtl-sdr && \
  mkdir build && cd build && \
  cmake .. -DINSTALL_UDEV_RULES=ON -DDETACH_KERNEL_DRIVER=ON && \
  make -j"$(nproc)" && \
  make install && \
  ldconfig && \
  cd ../.. && rm -rf rtl-sdr

# Install SoapyRTLSDR support.
RUN git clone --depth=1 https://github.com/pothosware/SoapyRTLSDR.git && \
  cd SoapyRTLSDR && \
  mkdir build && cd build && \
  cmake .. && \
  make -j"$(nproc)" && \
  make install && \
  ldconfig && \
  cd ../.. && rm -rf SoapyRTLSDR

WORKDIR /whispers

# Copy the application files.
COPY . .

# Install Python requirements.
RUN pip3 install --no-cache-dir -r ./requirements.txt

# Set executable permissions for the entrypoint script.
RUN chmod +x ./entrypoint.sh

ENTRYPOINT ["./entrypoint.sh"]
