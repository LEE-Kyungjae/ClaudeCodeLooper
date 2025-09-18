# Data Model: Claude Code Automated Restart System

## Core Entities

### MonitoringSession
Represents an active monitoring period of Claude Code terminal output.

**Fields**:
- `session_id`: Unique identifier for the monitoring session
- `start_time`: When monitoring began (ISO 8601)
- `status`: Current session status (active, waiting, stopped)
- `claude_process_id`: PID of monitored Claude Code process
- `detection_count`: Number of limit detections in this session
- `last_activity`: Timestamp of last monitored activity

**State Transitions**:
- `inactive` → `active` (start monitoring)
- `active` → `waiting` (limit detected)
- `waiting` → `active` (restart after cooldown)
- `active|waiting` → `stopped` (manual termination)

### LimitDetectionEvent
Represents a detected usage limit notification.

**Fields**:
- `event_id`: Unique identifier for the detection event
- `detection_time`: When the limit was detected (ISO 8601)
- `matched_pattern`: The regex pattern that matched
- `matched_text`: The actual text that triggered detection
- `session_id`: Reference to the monitoring session
- `cooldown_start`: When the waiting period began
- `cooldown_end`: When the waiting period expires

**Validation Rules**:
- `detection_time` must be valid ISO 8601 timestamp
- `matched_text` must be non-empty
- `cooldown_end` must be exactly 5 hours after `cooldown_start`

### RestartCommandConfiguration
Represents user-defined commands and parameters for Claude Code restart.

**Fields**:
- `config_id`: Unique identifier for the configuration
- `command_template`: Base command to execute Claude Code
- `arguments`: List of command-line arguments
- `working_directory`: Directory to start Claude Code in
- `environment_variables`: Key-value pairs for environment setup
- `retry_count`: Number of restart attempts on failure
- `retry_delay`: Seconds to wait between retry attempts

**Validation Rules**:
- `command_template` must be valid executable path
- `working_directory` must exist or be creatable
- `retry_count` must be between 0 and 10
- `retry_delay` must be between 1 and 300 seconds

### WaitingPeriod
Represents an active 5-hour countdown period.

**Fields**:
- `period_id`: Unique identifier for the waiting period
- `start_time`: When the waiting period began (ISO 8601)
- `duration_hours`: Duration in hours (default: 5)
- `end_time`: Calculated completion time
- `remaining_seconds`: Live countdown value
- `status`: Current period status (active, completed, cancelled)
- `associated_event_id`: Reference to triggering detection event

**State Transitions**:
- `pending` → `active` (countdown starts)
- `active` → `completed` (time expires)
- `active` → `cancelled` (manual intervention)

### TaskCompletionMonitor
Represents the mechanism for ensuring Claude Code tasks finish before restart cycles.

**Fields**:
- `monitor_id`: Unique identifier for the monitor
- `task_patterns`: List of regex patterns indicating task completion
- `timeout_seconds`: Maximum time to wait for task completion
- `check_interval`: Frequency of completion checks in seconds
- `last_activity_time`: Timestamp of last detected activity
- `completion_detected`: Boolean indicating if task completion was detected

**Validation Rules**:
- `timeout_seconds` must be between 60 and 3600 (1 hour max)
- `check_interval` must be between 1 and 60 seconds
- `task_patterns` must contain at least one valid regex

### SystemConfiguration
Represents global system settings and preferences.

**Fields**:
- `config_version`: Version of configuration schema
- `log_level`: Logging verbosity (DEBUG, INFO, WARN, ERROR)
- `log_file_path`: Path to main log file
- `max_log_size_mb`: Maximum log file size before rotation
- `detection_patterns`: List of regex patterns for limit detection
- `persistence_file`: Path to state persistence file
- `backup_count`: Number of backup files to maintain

**Default Values**:
- `log_level`: "INFO"
- `max_log_size_mb`: 50
- `backup_count`: 3
- `detection_patterns`: ["usage limit", "5-hour limit", "please wait"]

## Entity Relationships

```
MonitoringSession (1) ←→ (many) LimitDetectionEvent
LimitDetectionEvent (1) ←→ (1) WaitingPeriod
MonitoringSession (1) ←→ (1) TaskCompletionMonitor
RestartCommandConfiguration (1) ←→ (many) MonitoringSession
SystemConfiguration (1) ←→ (many) MonitoringSession
```

## Data Persistence

**Storage Format**: JSON files with atomic write operations
**File Structure**:
- `state.json`: Current system state and active sessions
- `config.json`: User configuration and preferences
- `history.json`: Historical detection events and statistics
- `backups/`: Timestamped backup files

**Backup Strategy**: Automatic backup before state changes, retention based on `backup_count` setting.