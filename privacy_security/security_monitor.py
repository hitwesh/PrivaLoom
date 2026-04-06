"""
Security event monitoring system for federated learning attacks and anomalies.

This module provides comprehensive security event logging, monitoring, and alerting
for federated learning systems:
- Structured event logging in JSONL format
- Real-time attack detection and alerting
- Client attack pattern analysis
- Security metrics and dashboard support
- Integration with SIEM systems

Events are logged to persistent storage for audit trails and incident response.
"""

import json
import time
import threading
from pathlib import Path
from typing import Dict, List, Optional, Any, Set
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
from enum import Enum

from utils.logging import setup_logger, log_info, log_warning, log_error

# Initialize logger
logger = setup_logger("privaloom.security_monitor")


class SecurityEventType(Enum):
    """Types of security events that can be detected."""
    OUTLIER_DETECTED = "outlier_detected"
    MALICIOUS_UPDATE = "malicious_update"
    REPUTATION_DECREASED = "reputation_decreased"
    AGGREGATION_FAILED = "aggregation_failed"
    CLIENT_BLACKLISTED = "client_blacklisted"
    VALIDATION_FAILED = "validation_failed"
    SUSPICIOUS_PATTERN = "suspicious_pattern"
    ATTACK_CAMPAIGN = "attack_campaign"
    SYSTEM_COMPROMISE = "system_compromise"


class SecuritySeverity(Enum):
    """Security event severity levels."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class SecurityEvent:
    """Represents a single security event."""
    event_type: SecurityEventType
    severity: SecuritySeverity
    client_id: str
    timestamp: str
    details: Dict[str, Any]
    source_component: str  # Component that generated the event
    detection_method: str  # Method used to detect the event
    confidence: float  # Confidence in detection (0.0-1.0)

    def __post_init__(self):
        """Validate event data."""
        if not isinstance(self.event_type, SecurityEventType):
            self.event_type = SecurityEventType(self.event_type)
        if not isinstance(self.severity, SecuritySeverity):
            self.severity = SecuritySeverity(self.severity)
        self.confidence = max(0.0, min(1.0, self.confidence))

    def to_dict(self) -> Dict[str, Any]:
        """Convert event to dictionary for JSON serialization."""
        return {
            "event_type": self.event_type.value,
            "severity": self.severity.value,
            "client_id": self.client_id,
            "timestamp": self.timestamp,
            "details": self.details,
            "source_component": self.source_component,
            "detection_method": self.detection_method,
            "confidence": self.confidence
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'SecurityEvent':
        """Create event from dictionary."""
        return cls(
            event_type=SecurityEventType(data["event_type"]),
            severity=SecuritySeverity(data["severity"]),
            client_id=data["client_id"],
            timestamp=data["timestamp"],
            details=data["details"],
            source_component=data["source_component"],
            detection_method=data["detection_method"],
            confidence=data["confidence"]
        )


@dataclass
class AttackPattern:
    """Pattern of attacks from specific client or group."""
    client_ids: Set[str]
    event_types: Set[SecurityEventType]
    start_time: str
    end_time: str
    event_count: int
    confidence: float
    pattern_type: str  # "single_client", "coordinated", "campaign"


class SecurityMonitor:
    """Monitors and logs security events with alerting capabilities."""

    def __init__(self, log_file_path: Optional[str] = None,
                 alert_threshold: int = 5,
                 alert_window_hours: int = 1,
                 enable_real_time_alerts: bool = True):
        """Initialize security monitor.

        Args:
            log_file_path: Path to security event log file (defaults to ~/.privaloom/security_events.jsonl)
            alert_threshold: Number of events to trigger alert
            alert_window_hours: Time window for alert threshold
            enable_real_time_alerts: Enable real-time alerting
        """
        if log_file_path is None:
            default_dir = Path.home() / ".privaloom"
            default_dir.mkdir(parents=True, exist_ok=True)
            log_file_path = str(default_dir / "security_events.jsonl")

        self.log_file = Path(log_file_path)
        self.alert_threshold = alert_threshold
        self.alert_window_hours = alert_window_hours
        self.enable_real_time_alerts = enable_real_time_alerts

        self._events_buffer: List[SecurityEvent] = []
        self._client_attack_counts: Dict[str, List[datetime]] = {}
        self._lock = threading.Lock()

        # Create log file if it doesn't exist
        if not self.log_file.exists():
            self.log_file.touch()

        log_info(logger, "Security monitor initialized",
                 log_file=str(self.log_file), alert_threshold=alert_threshold,
                 alert_window_hours=alert_window_hours)

    def log_event(self, event: SecurityEvent) -> None:
        """Log security event to persistent storage.

        Args:
            event: Security event to log
        """
        with self._lock:
            # Add to in-memory buffer
            self._events_buffer.append(event)

            # Track client attack counts for alerting
            if event.client_id not in self._client_attack_counts:
                self._client_attack_counts[event.client_id] = []
            self._client_attack_counts[event.client_id].append(datetime.now())

            # Write to persistent log
            self._write_event_to_log(event)

            # Check for real-time alerts
            if self.enable_real_time_alerts:
                self._check_alert_conditions(event)

            # Log to application logger based on severity
            if event.severity == SecuritySeverity.CRITICAL:
                log_error(logger, f"CRITICAL security event: {event.event_type.value}",
                         extra=event.to_dict())
            elif event.severity == SecuritySeverity.HIGH:
                log_warning(logger, f"HIGH severity security event: {event.event_type.value}",
                          extra=event.to_dict())
            else:
                log_info(logger, f"Security event: {event.event_type.value}",
                        extra=event.to_dict())

    def _write_event_to_log(self, event: SecurityEvent) -> None:
        """Write event to JSONL log file.

        Args:
            event: Security event to write
        """
        try:
            with open(self.log_file, 'a', encoding='utf-8') as f:
                json.dump(event.to_dict(), f)
                f.write('\n')
        except Exception as e:
            log_error(logger, f"Failed to write security event to log: {e}")

    def _check_alert_conditions(self, event: SecurityEvent) -> None:
        """Check if current event triggers alerting conditions.

        Args:
            event: Recent security event
        """
        client_id = event.client_id
        now = datetime.now()
        cutoff_time = now - timedelta(hours=self.alert_window_hours)

        # Count recent events for this client
        recent_events = [t for t in self._client_attack_counts.get(client_id, [])
                        if t >= cutoff_time]

        if len(recent_events) >= self.alert_threshold:
            # Trigger alert
            alert_event = SecurityEvent(
                event_type=SecurityEventType.ATTACK_CAMPAIGN,
                severity=SecuritySeverity.HIGH,
                client_id=client_id,
                timestamp=now.isoformat(),
                details={
                    "trigger_event": event.to_dict(),
                    "recent_event_count": len(recent_events),
                    "alert_threshold": self.alert_threshold,
                    "window_hours": self.alert_window_hours
                },
                source_component="security_monitor",
                detection_method="threshold_alerting",
                confidence=0.9
            )

            # Log the alert (this won't trigger recursion since it's a different event type)
            with open(self.log_file, 'a', encoding='utf-8') as f:
                json.dump(alert_event.to_dict(), f)
                f.write('\n')

            log_warning(logger, f"SECURITY ALERT: Client {client_id} has {len(recent_events)} events in {self.alert_window_hours}h")

    def get_recent_events(self, hours: int = 24,
                         client_id: Optional[str] = None,
                         event_types: Optional[List[SecurityEventType]] = None,
                         min_severity: Optional[SecuritySeverity] = None) -> List[SecurityEvent]:
        """Get recent security events matching criteria.

        Args:
            hours: Number of hours to look back
            client_id: Filter by specific client ID
            event_types: Filter by event types
            min_severity: Minimum severity level

        Returns:
            List of matching security events
        """
        cutoff_time = datetime.now() - timedelta(hours=hours)
        cutoff_iso = cutoff_time.isoformat()

        events = []

        try:
            # Read from log file
            with open(self.log_file, 'r', encoding='utf-8') as f:
                for line in f:
                    if line.strip():
                        try:
                            data = json.loads(line)
                            event = SecurityEvent.from_dict(data)

                            # Apply filters
                            if event.timestamp < cutoff_iso:
                                continue
                            if client_id and event.client_id != client_id:
                                continue
                            if event_types and event.event_type not in event_types:
                                continue
                            if min_severity and self._severity_level(event.severity) < self._severity_level(min_severity):
                                continue

                            events.append(event)

                        except (json.JSONDecodeError, KeyError) as e:
                            log_warning(logger, f"Failed to parse security event: {e}")

        except FileNotFoundError:
            pass  # Log file doesn't exist yet

        # Sort by timestamp (newest first)
        events.sort(key=lambda e: e.timestamp, reverse=True)
        return events

    def _severity_level(self, severity: SecuritySeverity) -> int:
        """Convert severity to numeric level for comparison."""
        levels = {
            SecuritySeverity.LOW: 1,
            SecuritySeverity.MEDIUM: 2,
            SecuritySeverity.HIGH: 3,
            SecuritySeverity.CRITICAL: 4
        }
        return levels[severity]

    def get_client_attack_count(self, client_id: str, hours: int = 24) -> int:
        """Get number of attacks from specific client in time window.

        Args:
            client_id: Client identifier
            hours: Time window in hours

        Returns:
            Number of attacks from client
        """
        events = self.get_recent_events(hours=hours, client_id=client_id)
        return len(events)

    def get_attack_statistics(self, hours: int = 24) -> Dict[str, Any]:
        """Get comprehensive attack statistics.

        Args:
            hours: Time window in hours

        Returns:
            Dictionary with attack statistics
        """
        events = self.get_recent_events(hours=hours)

        if not events:
            return {
                "total_events": 0,
                "time_window_hours": hours,
                "events_by_type": {},
                "events_by_severity": {},
                "unique_clients": 0,
                "most_active_client": None
            }

        # Analyze events
        events_by_type = {}
        events_by_severity = {}
        client_counts = {}

        for event in events:
            # Count by type
            event_type = event.event_type.value
            events_by_type[event_type] = events_by_type.get(event_type, 0) + 1

            # Count by severity
            severity = event.severity.value
            events_by_severity[severity] = events_by_severity.get(severity, 0) + 1

            # Count by client
            client_id = event.client_id
            client_counts[client_id] = client_counts.get(client_id, 0) + 1

        most_active_client = max(client_counts.items(), key=lambda x: x[1]) if client_counts else None

        return {
            "total_events": len(events),
            "time_window_hours": hours,
            "events_by_type": events_by_type,
            "events_by_severity": events_by_severity,
            "unique_clients": len(client_counts),
            "most_active_client": {
                "client_id": most_active_client[0],
                "event_count": most_active_client[1]
            } if most_active_client else None,
            "client_attack_counts": client_counts
        }

    def detect_attack_patterns(self, hours: int = 24) -> List[AttackPattern]:
        """Detect coordinated attack patterns.

        Args:
            hours: Time window to analyze

        Returns:
            List of detected attack patterns
        """
        events = self.get_recent_events(hours=hours)
        patterns = []

        if len(events) < 3:  # Need minimum events to detect patterns
            return patterns

        # Group events by client
        client_events = {}
        for event in events:
            if event.client_id not in client_events:
                client_events[event.client_id] = []
            client_events[event.client_id].append(event)

        # Detect single-client attack campaigns
        for client_id, client_event_list in client_events.items():
            if len(client_event_list) >= 3:  # Multiple events from same client
                event_types = {event.event_type for event in client_event_list}
                timestamps = [event.timestamp for event in client_event_list]

                pattern = AttackPattern(
                    client_ids={client_id},
                    event_types=event_types,
                    start_time=min(timestamps),
                    end_time=max(timestamps),
                    event_count=len(client_event_list),
                    confidence=0.8,
                    pattern_type="single_client"
                )
                patterns.append(pattern)

        # Detect coordinated attacks (multiple clients with similar patterns)
        if len(client_events) >= 2:
            # Look for clients with similar event types around the same time
            for client_id1, events1 in client_events.items():
                for client_id2, events2 in client_events.items():
                    if client_id1 >= client_id2:  # Avoid duplicates
                        continue

                    # Check for temporal correlation and similar event types
                    types1 = {event.event_type for event in events1}
                    types2 = {event.event_type for event in events2}
                    shared_types = types1.intersection(types2)

                    if len(shared_types) >= 2:  # Share at least 2 event types
                        all_events = events1 + events2
                        timestamps = [event.timestamp for event in all_events]

                        pattern = AttackPattern(
                            client_ids={client_id1, client_id2},
                            event_types=shared_types,
                            start_time=min(timestamps),
                            end_time=max(timestamps),
                            event_count=len(all_events),
                            confidence=0.7,
                            pattern_type="coordinated"
                        )
                        patterns.append(pattern)

        return patterns

    def generate_security_report(self, hours: int = 24) -> Dict[str, Any]:
        """Generate comprehensive security report.

        Args:
            hours: Time window for report

        Returns:
            Comprehensive security report
        """
        stats = self.get_attack_statistics(hours=hours)
        patterns = self.detect_attack_patterns(hours=hours)
        recent_events = self.get_recent_events(hours=hours, min_severity=SecuritySeverity.MEDIUM)

        return {
            "report_timestamp": datetime.now().isoformat(),
            "time_window_hours": hours,
            "summary": {
                "total_events": stats["total_events"],
                "unique_clients": stats["unique_clients"],
                "detected_patterns": len(patterns),
                "high_severity_events": len([e for e in recent_events
                                           if e.severity in [SecuritySeverity.HIGH, SecuritySeverity.CRITICAL]])
            },
            "statistics": stats,
            "attack_patterns": [asdict(pattern) for pattern in patterns],
            "recent_high_severity_events": [event.to_dict() for event in recent_events[:10]],  # Top 10
            "recommendations": self._generate_recommendations(stats, patterns)
        }

    def _generate_recommendations(self, stats: Dict[str, Any], patterns: List[AttackPattern]) -> List[str]:
        """Generate security recommendations based on analysis.

        Args:
            stats: Attack statistics
            patterns: Detected attack patterns

        Returns:
            List of recommendation strings
        """
        recommendations = []

        # Check for high attack volume
        if stats["total_events"] > 50:
            recommendations.append("High volume of security events detected. Consider tightening aggregation parameters.")

        # Check for coordinated attacks
        coordinated_patterns = [p for p in patterns if p.pattern_type == "coordinated"]
        if coordinated_patterns:
            recommendations.append(f"Detected {len(coordinated_patterns)} coordinated attack patterns. Consider implementing IP-based filtering.")

        # Check for persistent attackers
        if stats.get("most_active_client") and stats["most_active_client"]["event_count"] > 10:
            client_id = stats["most_active_client"]["client_id"]
            recommendations.append(f"Client {client_id} has high attack frequency. Consider blacklisting.")

        # Check for specific attack types
        if "malicious_update" in stats["events_by_type"]:
            malicious_count = stats["events_by_type"]["malicious_update"]
            if malicious_count > stats["total_events"] * 0.3:
                recommendations.append("High rate of malicious updates detected. Consider strengthening outlier detection.")

        if not recommendations:
            recommendations.append("No significant security concerns detected. Continue monitoring.")

        return recommendations

    def export_events(self, hours: int = 24, format: str = "json") -> str:
        """Export security events in specified format.

        Args:
            hours: Time window to export
            format: Export format ("json" or "csv")

        Returns:
            Exported events as string
        """
        events = self.get_recent_events(hours=hours)

        if format == "json":
            return json.dumps([event.to_dict() for event in events], indent=2)

        elif format == "csv":
            import csv
            import io

            output = io.StringIO()
            if events:
                writer = csv.DictWriter(output, fieldnames=events[0].to_dict().keys())
                writer.writeheader()
                for event in events:
                    writer.writerow(event.to_dict())

            return output.getvalue()

        else:
            raise ValueError(f"Unsupported export format: {format}")

    def clear_old_events(self, keep_days: int = 30) -> int:
        """Remove old events from log file to prevent unbounded growth.

        Args:
            keep_days: Number of days of events to keep

        Returns:
            Number of events removed
        """
        if not self.log_file.exists():
            return 0

        cutoff_time = datetime.now() - timedelta(days=keep_days)
        cutoff_iso = cutoff_time.isoformat()

        kept_events = []
        removed_count = 0

        try:
            # Read existing events
            with open(self.log_file, 'r', encoding='utf-8') as f:
                for line in f:
                    if line.strip():
                        try:
                            data = json.loads(line)
                            if data["timestamp"] >= cutoff_iso:
                                kept_events.append(line)
                            else:
                                removed_count += 1
                        except (json.JSONDecodeError, KeyError):
                            pass  # Skip malformed lines

            # Rewrite file with kept events
            with open(self.log_file, 'w', encoding='utf-8') as f:
                for line in kept_events:
                    f.write(line)

            log_info(logger, f"Cleaned security event log: removed {removed_count} old events")

        except Exception as e:
            log_error(logger, f"Failed to clean security event log: {e}")

        return removed_count


# Convenience functions for creating security events
def create_outlier_event(client_id: str, detection_method: str, confidence: float,
                        details: Optional[Dict[str, Any]] = None) -> SecurityEvent:
    """Create outlier detection security event."""
    return SecurityEvent(
        event_type=SecurityEventType.OUTLIER_DETECTED,
        severity=SecuritySeverity.MEDIUM,
        client_id=client_id,
        timestamp=datetime.now().isoformat(),
        details=details or {},
        source_component="outlier_detector",
        detection_method=detection_method,
        confidence=confidence
    )


def create_malicious_update_event(client_id: str, reason: str,
                                 details: Optional[Dict[str, Any]] = None) -> SecurityEvent:
    """Create malicious update security event."""
    return SecurityEvent(
        event_type=SecurityEventType.MALICIOUS_UPDATE,
        severity=SecuritySeverity.HIGH,
        client_id=client_id,
        timestamp=datetime.now().isoformat(),
        details=details or {"reason": reason},
        source_component="update_validator",
        detection_method="validation_check",
        confidence=0.9
    )


def create_reputation_event(client_id: str, old_score: float, new_score: float,
                          details: Optional[Dict[str, Any]] = None) -> SecurityEvent:
    """Create reputation decrease security event."""
    severity = SecuritySeverity.HIGH if new_score < 0.3 else SecuritySeverity.MEDIUM

    return SecurityEvent(
        event_type=SecurityEventType.REPUTATION_DECREASED,
        severity=severity,
        client_id=client_id,
        timestamp=datetime.now().isoformat(),
        details=details or {"old_score": old_score, "new_score": new_score},
        source_component="reputation_manager",
        detection_method="score_update",
        confidence=1.0
    )


# Global security monitor instance
_global_security_monitor: Optional[SecurityMonitor] = None


def get_security_monitor(**kwargs) -> SecurityMonitor:
    """Get global security monitor instance."""
    global _global_security_monitor

    if _global_security_monitor is None:
        _global_security_monitor = SecurityMonitor(**kwargs)

    return _global_security_monitor


def reset_security_monitor(**kwargs) -> SecurityMonitor:
    """Reset global security monitor with new configuration."""
    global _global_security_monitor
    _global_security_monitor = SecurityMonitor(**kwargs)
    return _global_security_monitor