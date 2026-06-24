#!/usr/bin/env bash
# Convenience wrapper — sets the right Python for gcloud and proxies all args.
# Usage: ./gcloud.sh auth login
#        ./gcloud.sh run deploy vibeci ...
export CLOUDSDK_PYTHON="/Users/danielglickman/Documents/Antigravity/Capstone V2/.venv/bin/python3"
/Users/danielglickman/google-cloud-sdk/google-cloud-sdk/bin/gcloud "$@"
