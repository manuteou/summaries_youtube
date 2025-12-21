"""
Analytics module for SynthetIA - Usage statistics and insights.
Provides data for dashboard visualizations.
"""
import os
import json
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, asdict
from collections import Counter


@dataclass
class UsageEvent:
    """Represents a tracked usage event."""
    event_type: str  # "synthesis", "export", "search", "api_call"
    timestamp: str
    data: Dict[str, Any]


class AnalyticsManager:
    """
    Tracks and aggregates usage statistics.
    Stores events in a JSON file for persistence.
    """
    
    def __init__(self, data_path: str = None):
        if data_path is None:
            base_dir = os.path.dirname(os.path.abspath(__file__))
            data_dir = os.path.join(base_dir, "data")
            os.makedirs(data_dir, exist_ok=True)
            data_path = os.path.join(data_dir, "analytics.json")
        
        self.data_path = data_path
        self._load_data()
    
    def _load_data(self):
        """Load analytics data from file."""
        if os.path.exists(self.data_path):
            try:
                with open(self.data_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.events = [UsageEvent(**e) for e in data.get('events', [])]
                    self.cumulative = data.get('cumulative', {
                        'total_syntheses': 0,
                        'total_videos_processed': 0,
                        'total_time_saved_minutes': 0,
                        'total_words_generated': 0,
                        'topics': {}
                    })
            except:
                self._init_empty()
        else:
            self._init_empty()
    
    def _init_empty(self):
        self.events = []
        self.cumulative = {
            'total_syntheses': 0,
            'total_videos_processed': 0,
            'total_time_saved_minutes': 0,
            'total_words_generated': 0,
            'topics': {}
        }
    
    def _save_data(self):
        """Save analytics data to file."""
        # Keep only last 500 events
        self.events = self.events[-500:]
        data = {
            'events': [asdict(e) for e in self.events],
            'cumulative': self.cumulative,
            'updated_at': datetime.now().isoformat()
        }
        with open(self.data_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    
    # --- Event Tracking ---
    
    def track_synthesis(self, num_videos: int, video_duration_sec: int, 
                        word_count: int, summary_type: str, topic: str = None):
        """
        Track a synthesis event.
        
        Args:
            num_videos: Number of videos synthesized
            video_duration_sec: Total duration of videos in seconds
            word_count: Number of words in generated summary
            summary_type: Type of summary
            topic: Optional topic/search query
        """
        # Estimate time saved: video duration - reading time (200 words/min)
        reading_time_min = word_count / 200
        video_time_min = video_duration_sec / 60
        time_saved = max(0, video_time_min - reading_time_min)
        
        event = UsageEvent(
            event_type="synthesis",
            timestamp=datetime.now().isoformat(),
            data={
                'num_videos': num_videos,
                'video_duration_sec': video_duration_sec,
                'word_count': word_count,
                'summary_type': summary_type,
                'time_saved_min': round(time_saved, 1),
                'topic': topic
            }
        )
        self.events.append(event)
        
        # Update cumulative stats
        self.cumulative['total_syntheses'] += 1
        self.cumulative['total_videos_processed'] += num_videos
        self.cumulative['total_time_saved_minutes'] += time_saved
        self.cumulative['total_words_generated'] += word_count
        
        if topic:
            topic_lower = topic.lower()[:50]
            self.cumulative['topics'][topic_lower] = self.cumulative['topics'].get(topic_lower, 0) + 1
        
        self._save_data()
    
    def track_export(self, format: str):
        """Track an export event."""
        event = UsageEvent(
            event_type="export",
            timestamp=datetime.now().isoformat(),
            data={'format': format}
        )
        self.events.append(event)
        self._save_data()
    
    def track_search(self, query: str, results_count: int):
        """Track a search event."""
        event = UsageEvent(
            event_type="search",
            timestamp=datetime.now().isoformat(),
            data={'query': query, 'results_count': results_count}
        )
        self.events.append(event)
        self._save_data()
    
    # --- Statistics Retrieval ---
    
    def get_summary_stats(self) -> Dict[str, Any]:
        """Get summary statistics."""
        return {
            'total_syntheses': self.cumulative['total_syntheses'],
            'total_videos': self.cumulative['total_videos_processed'],
            'time_saved_hours': round(self.cumulative['total_time_saved_minutes'] / 60, 1),
            'words_generated': self.cumulative['total_words_generated']
        }
    
    def get_activity_by_day(self, days: int = 30) -> List[Dict]:
        """Get synthesis activity by day for the last N days."""
        cutoff = datetime.now() - timedelta(days=days)
        cutoff_str = cutoff.isoformat()
        
        # Count events by day
        daily_counts = Counter()
        for event in self.events:
            if event.event_type == "synthesis" and event.timestamp >= cutoff_str:
                day = event.timestamp[:10]  # YYYY-MM-DD
                daily_counts[day] += 1
        
        # Fill in missing days
        result = []
        for i in range(days):
            day = (datetime.now() - timedelta(days=days-1-i)).strftime("%Y-%m-%d")
            result.append({
                'date': day,
                'count': daily_counts.get(day, 0)
            })
        
        return result
    
    def get_top_topics(self, limit: int = 10) -> List[Dict]:
        """Get most synthesized topics."""
        topics = self.cumulative.get('topics', {})
        sorted_topics = sorted(topics.items(), key=lambda x: x[1], reverse=True)
        
        return [
            {'topic': t[0], 'count': t[1]}
            for t in sorted_topics[:limit]
        ]
    
    def get_summary_type_distribution(self) -> Dict[str, int]:
        """Get distribution of summary types."""
        type_counts = Counter()
        for event in self.events:
            if event.event_type == "synthesis":
                summary_type = event.data.get('summary_type', 'unknown')
                type_counts[summary_type] += 1
        
        return dict(type_counts)
    
    def get_export_format_distribution(self) -> Dict[str, int]:
        """Get distribution of export formats."""
        format_counts = Counter()
        for event in self.events:
            if event.event_type == "export":
                fmt = event.data.get('format', 'unknown')
                format_counts[fmt] += 1
        
        return dict(format_counts)
    
    def get_hourly_activity(self) -> Dict[int, int]:
        """Get activity by hour of day."""
        hourly = Counter()
        for event in self.events:
            if event.event_type == "synthesis":
                try:
                    hour = int(event.timestamp[11:13])
                    hourly[hour] += 1
                except:
                    pass
        
        return {h: hourly.get(h, 0) for h in range(24)}
    
    def get_average_stats(self) -> Dict[str, float]:
        """Get average statistics per synthesis."""
        synth_events = [e for e in self.events if e.event_type == "synthesis"]
        
        if not synth_events:
            return {
                'avg_videos': 0,
                'avg_words': 0,
                'avg_time_saved': 0
            }
        
        total_videos = sum(e.data.get('num_videos', 0) for e in synth_events)
        total_words = sum(e.data.get('word_count', 0) for e in synth_events)
        total_time = sum(e.data.get('time_saved_min', 0) for e in synth_events)
        count = len(synth_events)
        
        return {
            'avg_videos': round(total_videos / count, 1),
            'avg_words': round(total_words / count, 0),
            'avg_time_saved': round(total_time / count, 1)
        }


# Singleton
_analytics_instance = None

def get_analytics() -> AnalyticsManager:
    global _analytics_instance
    if _analytics_instance is None:
        _analytics_instance = AnalyticsManager()
    return _analytics_instance
