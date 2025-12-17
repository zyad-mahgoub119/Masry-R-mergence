"""
Log Processor Script
====================
Processes error logs by removing duplicates and sorting by frequency.
Tracks new errors across runs and maintains rotation of historical logs.

Usage:
    python process_log.py
"""

import re
import os
from collections import defaultdict
from tools.shared.fetch_logs import get_log_directory_from_config


def rotate_log_files(cleaned, old, oldest):
    """Rotate log files: cleaned -> old -> oldest."""
    if os.path.exists(oldest):
        os.remove(oldest)
    if os.path.exists(old):
        os.rename(old, oldest)
    if os.path.exists(cleaned):
        os.rename(cleaned, old)


def load_old_entries(filepath):
    """Load previous log entries for comparison."""
    if not os.path.exists(filepath):
        return set()
    
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
            # Extract log entries without COUNT metadata
            entries = re.split(r'COUNT:\d+.*?\n\n', content)
            return {entry.strip() for entry in entries if entry.strip()}
    except (IOError, UnicodeDecodeError) as e:
        print(f"Warning: Could not read old log file: {e}")
        return set()


def read_log_file(filepath):
    """Read log file with fallback encoding."""
    encodings = ['utf-8', 'latin-1', 'cp1252']
    
    for encoding in encodings:
        try:
            with open(filepath, 'r', encoding=encoding) as f:
                return f.readlines()
        except (UnicodeDecodeError, IOError):
            continue
    
    raise IOError(f"Could not read log file with supported encodings: {filepath}")


def parse_log_entries(log_lines):
    """Parse log entries and count occurrences."""
    # Patterns for cleaning and parsing
    timestamp_pattern = re.compile(r'\[\d{2}:\d{2}:\d{2}\]')
    file_ref_pattern = re.compile(r'^\[.*\.cpp:\d+\]')
    
    entries_count = defaultdict(int)
    current_entry = []
    
    for line in log_lines:
        # Remove timestamps
        cleaned_line = timestamp_pattern.sub('', line).strip()
        
        # Check if this is a new log entry
        if file_ref_pattern.match(cleaned_line):
            if current_entry:
                entry_str = '\n'.join(current_entry).strip()
                entries_count[entry_str] += 1
                current_entry = []
        
        if cleaned_line:  # Only append non-empty lines
            current_entry.append(cleaned_line)
    
    # Don't forget the last entry
    if current_entry:
        entry_str = '\n'.join(current_entry).strip()
        entries_count[entry_str] += 1
    
    return entries_count


def format_output_entry(entry, count, old_entries, max_lines=3):
    """Format a single log entry with metadata."""
    lines = entry.split('\n')
    
    # Truncate if needed
    if len(lines) > max_lines:
        entry_text = '\n'.join(lines[:max_lines])
        shortened = True
    else:
        entry_text = entry
        shortened = False
    
    # Build metadata line
    metadata = f"COUNT:{count}"
    if entry_text not in old_entries:
        metadata += "  !! NEW !!"
    if shortened:
        metadata += "  (entry shortened)"
    
    return f"{metadata}\n\n{entry_text}\n\n"


def write_cleaned_log(entries_count, old_entries, output_path):
    """Write the cleaned and sorted log file."""
    # Sort by count descending
    sorted_entries = sorted(entries_count.items(), key=lambda x: x[1], reverse=True)
    
    # Format all entries
    output_lines = [
        format_output_entry(entry, count, old_entries)
        for entry, count in sorted_entries
    ]
    
    # Write to file
    with open(output_path, 'w', encoding='utf-8') as f:
        f.writelines(output_lines)
    
    return len(sorted_entries)


def process_log(error_log, cleaned_log, old_log, oldest_log):
    """Main processing function."""
    # Rotate existing log files
    rotate_log_files(cleaned_log, old_log, oldest_log)
    
    # Load previous entries for comparison
    old_entries = load_old_entries(old_log)
    
    # Read and parse current log
    log_lines = read_log_file(error_log)
    entries_count = parse_log_entries(log_lines)
    
    # Write cleaned output
    num_entries = write_cleaned_log(entries_count, old_entries, cleaned_log)
    
    print(f"✓ Processed {len(log_lines)} lines into {num_entries} unique entries")
    print(f"✓ Output saved to: {cleaned_log}")


def main():
    """Entry point for the script."""
    try:
        config_path = get_log_directory_from_config()
        
        # Define file paths
        error_log = os.path.join(config_path, 'error.log')
        cleaned_log = os.path.join(config_path, 'cleaned_error.log')
        old_log = os.path.join(config_path, 'cleaned_error_old.log')
        oldest_log = os.path.join(config_path, 'cleaned_error_oldest.log')
        
        # Verify input file exists
        if not os.path.exists(error_log):
            print(f"Error: Log file not found: {error_log}")
            return 1
        
        # Process the log
        process_log(error_log, cleaned_log, old_log, oldest_log)
        return 0
        
    except Exception as e:
        print(f"Error processing log: {e}")
        return 1


if __name__ == '__main__':
    exit(main())
