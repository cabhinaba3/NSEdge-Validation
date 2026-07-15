# Base Image: Ubuntu 22.04 LTS
FROM ubuntu:22.04

# Prevent interactive prompts during apt-get
ENV DEBIAN_FRONTEND=noninteractive

# Update system and install prerequisite packages for Micromamba, OMNeT++, and EdgeCloudSim
RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    wget \
    git \
    tar \
    bison \
    flex \
    make \
    gcc \
    g++ \
    cmake \
    python3 \
    python3-pip \
    openjdk-11-jdk \
    ant \
    maven \
    unzip \
    && rm -rf /var/lib/apt/lists/*

# Set up generic workspace directory
RUN mkdir -p /workspace
WORKDIR /workspace

# Copy the entire codebase into the container
COPY . /workspace/

# Execute the Dependency Installation script (Downloads OMNeT++ 5.6 & 6.0, INET, and Micromamba)
RUN chmod +x install_dep.sh && ./install_dep.sh

# Compile OMNeT++, INET, and Simu5G Native Environments
RUN cd third_party && chmod +x build_omnetpp6.sh build_inet_603.sh build_simu5g.sh
RUN cd third_party && ./build_omnetpp6.sh
RUN cd third_party && ./build_inet_603.sh
RUN cd third_party && ./build_simu5g.sh

# Provide instructions upon entry
CMD ["/bin/bash", "-c", "echo 'Container Ready! Run: python3 src/simulators/dipdce_real_injection.py to execute the full evaluation suite natively.' && /bin/bash"]
