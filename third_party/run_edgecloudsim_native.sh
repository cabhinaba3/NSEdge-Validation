#!/bin/bash
cd /proj/oasees-PG0/NS3-Edge/validation_experiment/third_party/EdgeCloudSim/scripts/sample_app1

# Run EdgeCloudSim natively
OUTPUT=$(java -classpath '../../bin:../../lib/cloudsim-4.0.jar:../../lib/commons-math3-3.6.1.jar:../../lib/colt.jar' edu.boun.edgecloudsim.applications.sample_app1.MainApp config/default_config.properties config/edge_devices.xml config/applications.xml output_test 1)

# Extract native delay
DELAY=$(echo "$OUTPUT" | grep "average service time:" | awk '{print $4}')

if [ -z "$DELAY" ] || [ "$DELAY" = "NaN" ]; then
    DELAY=0.0
fi

echo "{\"EdgeCloudSim_Native_Delay\": $DELAY}" > /proj/oasees-PG0/NS3-Edge/validation_experiment/third_party/ecs_native_metrics.json
