#!/usr/bin/env bash
# One command for the video: E1 through the full stack with a real alert.
exec "$(dirname "$0")/demo.sh" SIM_E1_CROSS_DURING_ROLLOUT --alerts
