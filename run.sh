#!/bin/bash

# Run WorkSpeak Bot

set -e

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$DIR"

# Load environment if exists
if [ -f .env ]; then
    export $(grep -v '^#' .env | xargs)
fi

# Create logs directory
mkdir -p logs

# Run bot
python -m slack_message_bot "$@"
