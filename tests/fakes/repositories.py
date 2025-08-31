"""In-memory fake repository implementations for contract tests."""

from typing import Optional, List, Dict, Any
from datetime import datetime
import uuid

from app.storage.interfaces import InboxEventsRepoIface, OutboxRepoIface, IncidentsRepoIface
from app.storage.models import InboxEvent, OutboxMessage


class InboxEventsRepoFake(InboxEventsRepoIface):
    """In-memory fake implementation of inbox events repository."""
    
    def __init__(self):
        self._events: Dict[str, InboxEvent] = {}
        self._counter = 0
    
    async def create(self, event: InboxEvent) -> InboxEvent:
        """Create a new inbox event."""
        self._counter += 1
        event.id = self._counter
        event.created_at = datetime.utcnow()
        
        # Use provider + provider_event_id as key for deduplication
        key = f"{event.provider}:{event.provider_event_id}"
        self._events[key] = event
        return event
    
    async def get_by_provider_id(self, provider: str, provider_event_id: str) -> Optional[InboxEvent]:
        """Get inbox event by provider and provider event ID."""
        key = f"{provider}:{provider_event_id}"
        return self._events.get(key)
    
    async def list_by_provider(self, provider: str, limit: int = 100) -> List[InboxEvent]:
        """List inbox events by provider."""
        events = [event for event in self._events.values() if event.provider == provider]
        return sorted(events, key=lambda x: x.created_at, reverse=True)[:limit]


class OutboxRepoFake(OutboxRepoIface):
    """In-memory fake implementation of outbox messages repository."""
    
    def __init__(self):
        self._messages: Dict[str, OutboxMessage] = {}
        self._counter = 0
    
    async def create(self, message: OutboxMessage) -> OutboxMessage:
        """Create a new outbox message."""
        self._counter += 1
        message.id = self._counter
        message.created_at = datetime.utcnow()
        message.status = "pending"
        
        # Use channel + provider_message_id as key for deduplication
        key = f"{message.channel}:{message.provider_message_id}"
        self._messages[key] = message
        return message
    
    async def get_by_provider_id(self, channel: str, provider_message_id: str) -> Optional[OutboxMessage]:
        """Get outbox message by channel and provider message ID."""
        key = f"{channel}:{provider_message_id}"
        return self._messages.get(key)
    
    async def list_by_channel(self, channel: str, limit: int = 100) -> List[OutboxMessage]:
        """List outbox messages by channel."""
        messages = [msg for msg in self._messages.values() if msg.channel == channel]
        return sorted(messages, key=lambda x: x.created_at, reverse=True)[:limit]
    
    async def mark_sent(self, message_id: int, provider_message_id: str) -> OutboxMessage:
        """Mark a message as sent."""
        for message in self._messages.values():
            if message.id == message_id:
                message.status = "sent"
                message.sent_at = datetime.utcnow()
                message.provider_message_id = provider_message_id
                return message
        raise ValueError(f"Message with ID {message_id} not found")
    
    async def mark_failed(self, message_id: int, error: str) -> OutboxMessage:
        """Mark a message as failed."""
        for message in self._messages.values():
            if message.id == message_id:
                message.status = "failed"
                message.error = error
                message.failed_at = datetime.utcnow()
                return message
        raise ValueError(f"Message with ID {message_id} not found")


class IncidentsRepoFake(IncidentsRepoIface):
    """In-memory fake implementation of incidents repository."""
    
    def __init__(self):
        self._incidents: Dict[int, dict] = {}
        self._counter = 0
    
    async def create(self, incident: dict) -> dict:
        """Create a new incident."""
        self._counter += 1
        incident["id"] = self._counter
        incident["created_at"] = datetime.utcnow().isoformat()
        incident["status"] = incident.get("status", "open")
        
        self._incidents[self._counter] = incident
        return incident
    
    async def get_by_id(self, incident_id: int) -> Optional[dict]:
        """Get incident by ID."""
        return self._incidents.get(incident_id)
    
    async def list_active(self, limit: int = 100) -> List[dict]:
        """List active incidents."""
        active = [inc for inc in self._incidents.values() if inc.get("status") == "open"]
        return sorted(active, key=lambda x: x["created_at"], reverse=True)[:limit]
    
    async def update(self, incident_id: int, updates: dict) -> dict:
        """Update an incident."""
        if incident_id not in self._incidents:
            raise ValueError(f"Incident with ID {incident_id} not found")
        
        self._incidents[incident_id].update(updates)
        self._incidents[incident_id]["updated_at"] = datetime.utcnow().isoformat()
        return self._incidents[incident_id]
