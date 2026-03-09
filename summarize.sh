#!/bin/bash

# YouTube Summarizer Runner
# This script prompts for a URL, runs the summarizer, and displays the result with glow.

# 1. Ask for YouTube URL
echo -n "Enter YouTube video URL: "
read VIDEO_URL

if [ -z "$VIDEO_URL" ]; then
    echo "Error: No URL provided."
    exit 1
fi

# 2. Run the summarizer
# We use tee to show the progress in real-time while capturing the output
echo "Processing video..."
TEMP_OUTPUT=$(mktemp)
uv run yt-summarizer "$VIDEO_URL" 2>&1 | tee "$TEMP_OUTPUT"

# 3. Extract the output file path
# The CLI prints: Done! Summary saved to: path/to/file.md
FILE_PATH=$(grep "Summary saved to:" "$TEMP_OUTPUT" | sed 's/.*Summary saved to: //')

# Clean up temp file
rm "$TEMP_OUTPUT"

# 4. Run glow if file exists
if [ -n "$FILE_PATH" ] && [ -f "$FILE_PATH" ]; then
    echo -e "\n--- Summary Finished ---\n"
    if command -v glow >/dev/null 2>&1; then
        glow "$FILE_PATH"
    else
        echo "Summary saved to: $FILE_PATH"
        echo "Note: 'glow' not found, displaying as plain text:"
        cat "$FILE_PATH"
    fi
else
    echo "Error: Could not determine the output file path or file was not created."
    exit 1
fi
