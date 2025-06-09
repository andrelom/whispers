#
# Main

FROM ubuntu:22.04 AS main

ENV DEBIAN_FRONTEND=noninteractive

# Install dependencies for building SoapySDR and SoapyAirspy,
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

# Install SoapySDR and SoapyAirspy.
RUN git clone --depth=1 https://github.com/pothosware/SoapySDR.git && \
  cd SoapySDR && \
  mkdir build && cd build && \
  cmake .. -DENABLE_PYTHON3=ON && \
  make -j"$(nproc)" && \
  make install && \
  ldconfig && \
  cd ../.. && rm -rf SoapySDR

# Install SoapyAirspy.
RUN git clone --depth=1 https://github.com/pothosware/SoapyAirspy.git && \
  cd SoapyAirspy && \
  mkdir build && cd build && \
  cmake .. && \
  make -j"$(nproc)" && \
  make install && \
  ldconfig && \
  cd ../.. && rm -rf SoapyAirspy

WORKDIR /whispers

# Copy the application files.
COPY . .

# Install Python requirements.
RUN pip3 install --no-cache-dir -r ./requirements.txt

ENTRYPOINT ["./entrypoint.sh"]
