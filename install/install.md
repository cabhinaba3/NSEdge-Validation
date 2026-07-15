# Validation Environment Installation Guide

This document outlines the step-by-step procedures required to set up the multi-framework execution environment for validating `NSEdge` alongside third-party simulators (`Simu5G`, `EdgeSimPy`, `EdgeCloudSim`, and `FogNetSim++`).

Due to heavy version conflicts among different frameworks (e.g. `Simu5G` demanding OMNeT++ 6.0 while legacy simulators demand OMNeT++ 5.x/4.x), we use an isolated dual-framework setup managed via `micromamba`.

## 1. Automated Dependency Staging

To quickly download all necessary environments, compilers, and framework archives, run the provided script from the `NSEdge-Validation` directory:

```bash
cd NSEdge-Validation
chmod +x install/install_dep.sh
bash install/bootstrap_sims.sh
```

This script will:
1. Initialize a local `micromamba` binary in `third_party/micromamba`.
2. Create `sim_env` (for OMNeT++ compilation).
3. Create `edgesimpy_env` (for executing the Python EdgeSimPy models).
4. Download and extract **OMNeT++ 6.0.3** and **OMNeT++ 5.6.2**.
5. Download **INET 4.5.0** (required for `Simu5G`).
6. Clone the `Simu5G` and `EdgeCloudSim` repositories.

---

## 2. Compiling OMNeT++ Versions

You must compile both versions of OMNeT++ sequentially.

### 2.1 Compiling OMNeT++ 6.0.3 (For Simu5G)
Activate the simulation environment and configure the build:

```bash
export MAMBA_ROOT_PREFIX=$(pwd)/third_party/micromamba_root
export PATH=$MAMBA_ROOT_PREFIX/envs/sim_env/bin:$PATH

cd third_party/omnetpp-6.0.3
source setenv -f
./configure WITH_QTENV=no WITH_OSG=no WITH_OSGEARTH=no
make -j$(nproc)
cd ..
```

### 2.2 Compiling OMNeT++ 5.6.2 (For Legacy Frameworks)
```bash
export PATH=$MAMBA_ROOT_PREFIX/envs/sim_env/bin:$PATH

cd third_party/omnetpp-5.6.2
source setenv -f
./configure WITH_QTENV=no WITH_OSG=no WITH_OSGEARTH=no
make -j$(nproc)
cd ..
```

---

## 3. Compiling INET and Target Frameworks

### 3.1 INET 4.5.0 + Simu5G
Simu5G relies exclusively on INET 4.5.0 and OMNeT++ 6.0.3.

1. **Build INET 4.5.0**:
   ```bash
   cd third_party/inet45_603
   export PATH=$MAMBA_ROOT_PREFIX/envs/sim_env/bin:$PATH:$(pwd)/../omnetpp-6.0.3/bin
   source ../omnetpp-6.0.3/setenv -f
   make makefiles
   make -j$(nproc)
   cd ..
   ```

2. **Build Simu5G**:
   ```bash
   cd third_party/Simu5G
   source ../omnetpp-6.0.3/setenv -f
   make makefiles
   make -j$(nproc)
   cd ..
   ```

### 3.2 EdgeSimPy
The `install_dep.sh` script automatically handles the compilation and installation of `EdgeSimPy` into the `edgesimpy_env` Python 3.10 container.
To run EdgeSimPy baselines, use:
```bash
$MAMBA_ROOT_PREFIX/envs/edgesimpy_env/bin/python3 benchmark/measure_edgesimpy.py
```

### 3.3 EdgeCloudSim (Java)
EdgeCloudSim is purely Java-based and does not strictly require `omnetpp`. You can run its build script via standard Java environments:
```bash
cd third_party/EdgeCloudSim
# Requires openjdk
./build.sh
```

### 3.4 FogNetSim++ (Legacy Alert)
> [!WARNING]
> **FogNetSim++ Compilation is Not Recommended.**
> FogNetSim++ is intrinsically tied to **OMNeT++ 4.6** and an outdated version of INET. Attempts to port it to modern GCC compilers or OMNeT++ 5.x/6.x will result in massive macro API compilation failures (`cClassDescriptor` discrepancies, `string2double` depreciations). For modern integration, rely on mathematical proxy outputs rather than native physical compilation.

---

## 4. Running the Complete Benchmark

Once the environments are compiled, you can trigger the unified execution script to gather the baseline metrics for all frameworks sequentially:

```bash
cd third_party
chmod +x run_final_baselines.sh
./run_final_baselines.sh
```
