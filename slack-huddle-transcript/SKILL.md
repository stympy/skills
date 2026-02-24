---
name: slack-huddle-transcript
description: "Extract and format Slack huddle transcripts for analysis. Use this skill when processing Slack huddle transcript files (.vtt), when user mentions huddle transcript or Slack transcript, when user uploads a VTT file from Slack, or when user asks to summarize or analyze a Slack meeting/huddle. Handles VTT format transcripts with speaker identification, timestamps, and conversation merging."
---

# Slack Huddle Transcript Processor

Parse and format Slack huddle transcripts into clean, readable output for analysis.

## Quick Start

```bash
python scripts/parse_transcript.py <transcript.vtt> --format markdown
```

## Getting Transcripts from Slack

### Method 1: Download from Slack UI (Recommended)
1. Open the Slack channel where the huddle occurred
2. Find the huddle thread (shows as "Huddle" with participants)
3. Click the thread to expand it
4. Look for "Transcript" attachment
5. Click the download icon (⬇️) to save as `.vtt` file

### Method 2: Slack API
```bash
# List recent files to find transcript
curl -H "Authorization: Bearer $SLACK_TOKEN" \
  "https://slack.com/api/files.list?types=transcript"

# Download specific file
curl -H "Authorization: Bearer $SLACK_TOKEN" \
  "https://slack.com/api/files.info?file=FILE_ID"
```

### Method 3: Copy-Paste Raw VTT
If user provides raw VTT content, save to file first:
```bash
cat > /tmp/transcript.vtt << 'EOF'
<paste VTT content here>
EOF
```

## Script Usage

### Basic parsing (markdown output)
```bash
python scripts/parse_transcript.py transcript.vtt
```

### Output formats
```bash
# Markdown (default) - best for reading/sharing
python scripts/parse_transcript.py transcript.vtt --format markdown

# JSON - best for further processing
python scripts/parse_transcript.py transcript.vtt --format json

# Plain text - minimal formatting
python scripts/parse_transcript.py transcript.vtt --format plain
```

### Options
- `--no-merge`: Keep all entries separate (default merges consecutive same-speaker entries)
- `--title "Meeting Name"`: Custom title for markdown output
- `--output file.md`: Write to file instead of stdout
- `--stdin`: Read VTT content from stdin

## VTT Format Reference

Slack huddle transcripts use WebVTT format:
```
WEBVTT

00:00:01.000 --> 00:00:05.000
Alice: Hey everyone, let's get started.

00:00:05.500 --> 00:00:08.000
Bob: Sounds good, I have a few updates.
```

The script automatically:
- Extracts speaker names from the text
- Merges consecutive same-speaker entries
- Formats timestamps for readability
- Generates participant summary

## Common Workflows

### Summarize a huddle
```bash
python scripts/parse_transcript.py meeting.vtt > meeting.md
# Then analyze meeting.md for key points, action items, decisions
```

### Extract action items
Parse to JSON for programmatic extraction:
```bash
python scripts/parse_transcript.py meeting.vtt --format json | \
  jq '.entries[] | select(.text | contains("action") or contains("TODO"))'
```

### Compare multiple huddles
```bash
for f in huddle_*.vtt; do
  python scripts/parse_transcript.py "$f" --format json > "${f%.vtt}.json"
done
```
