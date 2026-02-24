#!/usr/bin/env python3
"""
Parse Slack huddle transcripts (VTT format) into structured, readable output.

Usage:
    python parse_transcript.py <transcript_file> [--format markdown|json|plain]
    python parse_transcript.py --stdin [--format markdown|json|plain]

Examples:
    python parse_transcript.py huddle_transcript.vtt
    python parse_transcript.py huddle_transcript.vtt --format json
    cat transcript.vtt | python parse_transcript.py --stdin
"""

import argparse
import json
import re
import sys
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Optional


@dataclass
class TranscriptEntry:
    """Single transcript entry with speaker, timestamp, and text."""
    speaker: str
    start_time: str
    end_time: str
    text: str
    start_seconds: float = 0.0


def parse_vtt_timestamp(ts: str) -> tuple[str, float]:
    """Parse VTT timestamp to readable format and total seconds."""
    # VTT format: HH:MM:SS.mmm or MM:SS.mmm
    ts = ts.strip()
    parts = ts.replace(',', '.').split(':')
    
    if len(parts) == 3:
        hours, minutes, seconds = parts
        total = int(hours) * 3600 + int(minutes) * 60 + float(seconds)
        readable = f"{int(hours):02d}:{int(minutes):02d}:{float(seconds):06.3f}"
    elif len(parts) == 2:
        minutes, seconds = parts
        total = int(minutes) * 60 + float(seconds)
        readable = f"{int(minutes):02d}:{float(seconds):06.3f}"
    else:
        return ts, 0.0
    
    return readable, total


def parse_vtt_content(content: str) -> list[TranscriptEntry]:
    """Parse VTT content into transcript entries."""
    entries = []
    lines = content.strip().split('\n')
    
    i = 0
    # Skip WEBVTT header
    while i < len(lines) and not re.match(r'\d+:\d+', lines[i]):
        i += 1
    
    current_speaker = "Unknown"
    
    while i < len(lines):
        line = lines[i].strip()
        
        # Skip empty lines and cue identifiers
        if not line or re.match(r'^\d+$', line):
            i += 1
            continue
        
        # Check for timestamp line (e.g., "00:00:01.000 --> 00:00:05.000")
        timestamp_match = re.match(r'(\d+:[\d:.]+)\s*-->\s*(\d+:[\d:.]+)', line)
        if timestamp_match:
            start_raw, end_raw = timestamp_match.groups()
            start_time, start_seconds = parse_vtt_timestamp(start_raw)
            end_time, _ = parse_vtt_timestamp(end_raw)
            
            # Collect text lines until next timestamp or empty line
            i += 1
            text_lines = []
            while i < len(lines):
                text_line = lines[i].strip()
                if not text_line or re.match(r'^\d+$', text_line) or re.match(r'\d+:[\d:.]+\s*-->', text_line):
                    break
                text_lines.append(text_line)
                i += 1
            
            full_text = ' '.join(text_lines)
            
            # Extract speaker from text (Slack format: "Speaker Name: text")
            speaker_match = re.match(r'^([^:]+):\s*(.*)$', full_text)
            if speaker_match:
                current_speaker = speaker_match.group(1).strip()
                text = speaker_match.group(2).strip()
            else:
                text = full_text
            
            if text:
                entries.append(TranscriptEntry(
                    speaker=current_speaker,
                    start_time=start_time,
                    end_time=end_time,
                    text=text,
                    start_seconds=start_seconds
                ))
        else:
            i += 1
    
    return entries


def merge_consecutive_speaker_entries(entries: list[TranscriptEntry], gap_threshold: float = 3.0) -> list[TranscriptEntry]:
    """Merge consecutive entries from the same speaker if within gap threshold."""
    if not entries:
        return entries
    
    merged = []
    current = entries[0]
    
    for entry in entries[1:]:
        if entry.speaker == current.speaker and (entry.start_seconds - current.start_seconds) < gap_threshold:
            # Merge: extend text and end time
            current = TranscriptEntry(
                speaker=current.speaker,
                start_time=current.start_time,
                end_time=entry.end_time,
                text=f"{current.text} {entry.text}",
                start_seconds=current.start_seconds
            )
        else:
            merged.append(current)
            current = entry
    
    merged.append(current)
    return merged


def format_as_markdown(entries: list[TranscriptEntry], title: str = "Huddle Transcript") -> str:
    """Format transcript entries as markdown."""
    lines = [f"# {title}", ""]
    
    # Summary
    speakers = sorted(set(e.speaker for e in entries))
    if entries:
        duration_seconds = entries[-1].start_seconds
        duration_min = int(duration_seconds // 60)
        duration_sec = int(duration_seconds % 60)
        lines.extend([
            "## Summary",
            f"- **Participants**: {', '.join(speakers)}",
            f"- **Duration**: ~{duration_min}m {duration_sec}s",
            f"- **Entries**: {len(entries)}",
            ""
        ])
    
    # Transcript
    lines.extend(["## Transcript", ""])
    
    for entry in entries:
        # Format: [00:01:23] **Speaker**: Text
        ts = entry.start_time.split('.')[0]  # Remove milliseconds for readability
        if ts.startswith("00:"):
            ts = ts[3:]  # Remove leading "00:" for shorter timestamps
        lines.append(f"**[{ts}] {entry.speaker}**: {entry.text}")
        lines.append("")
    
    return '\n'.join(lines)


def format_as_plain(entries: list[TranscriptEntry]) -> str:
    """Format transcript entries as plain text."""
    lines = []
    for entry in entries:
        ts = entry.start_time.split('.')[0]
        if ts.startswith("00:"):
            ts = ts[3:]
        lines.append(f"[{ts}] {entry.speaker}: {entry.text}")
    return '\n'.join(lines)


def format_as_json(entries: list[TranscriptEntry]) -> str:
    """Format transcript entries as JSON."""
    data = {
        "entries": [asdict(e) for e in entries],
        "summary": {
            "speakers": sorted(set(e.speaker for e in entries)),
            "entry_count": len(entries),
            "duration_seconds": entries[-1].start_seconds if entries else 0
        }
    }
    return json.dumps(data, indent=2)


def main():
    parser = argparse.ArgumentParser(
        description="Parse Slack huddle transcripts (VTT format)",
        epilog="Supports VTT files from Slack huddle transcripts."
    )
    parser.add_argument('file', nargs='?', help='Path to transcript file (VTT format)')
    parser.add_argument('--stdin', action='store_true', help='Read from stdin')
    parser.add_argument('--format', '-f', choices=['markdown', 'json', 'plain'], 
                       default='markdown', help='Output format (default: markdown)')
    parser.add_argument('--no-merge', action='store_true', 
                       help='Do not merge consecutive speaker entries')
    parser.add_argument('--title', '-t', default='Huddle Transcript',
                       help='Title for markdown output')
    parser.add_argument('--output', '-o', help='Output file (default: stdout)')
    
    args = parser.parse_args()
    
    # Read input
    if args.stdin:
        content = sys.stdin.read()
    elif args.file:
        path = Path(args.file)
        if not path.exists():
            print(f"Error: File not found: {args.file}", file=sys.stderr)
            sys.exit(1)
        content = path.read_text(encoding='utf-8')
    else:
        parser.print_help()
        sys.exit(1)
    
    # Parse
    entries = parse_vtt_content(content)
    
    if not args.no_merge:
        entries = merge_consecutive_speaker_entries(entries)
    
    # Format output
    if args.format == 'markdown':
        output = format_as_markdown(entries, args.title)
    elif args.format == 'json':
        output = format_as_json(entries)
    else:
        output = format_as_plain(entries)
    
    # Write output
    if args.output:
        Path(args.output).write_text(output, encoding='utf-8')
        print(f"Written to {args.output}", file=sys.stderr)
    else:
        print(output)


if __name__ == '__main__':
    main()
