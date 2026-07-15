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

# Set up exactly matching workspace directory to prevent absolute path errors
RUN mkdir -p /proj/oasees-PG0/NS3-Edge/NSEdge-Validation
WORKDIR /proj/oasees-PG0/NS3-Edge/NSEdge-Validation

# Copy the entire codebase into the container
COPY . /proj/oasees-PG0/NS3-Edge/NSEdge-Validation/

# Execute the Dependency Installation script (Downloads OMNeT++ 5.6 & 6.0, INET, and Micromamba)
RUN chmod +x install_dep.sh && ./install_dep.sh

# Provide instructions upon entry
CMD ["/bin/bash", "-c", "echo 'Container Ready! Navigate to third_party and run build_omnetpp6.sh and build_simu5g.sh to compile the discrete-event engines. Then run python3 src/simulators/dipdce_real_injection.py' && /bin/bash"]
