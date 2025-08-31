"""Repository interfaces for dependency injection."""

from abc import ABC, abstractmethod
from typing import Optional, List
from datetime import datetime

from app.storage.models import InboxEvent, OutboxMessage


class InboxEventsRepoIface(ABC):
    """Interface for inbox events repository."""
    
    @abstractmethod
    async def create(self, event: InboxEvent) -> InboxEvent:
        """Create a new inbox event."""
        pass
    
    @abstractmethod
    async def get_by_provider_id(self, provider: str, provider_event_id: str) -> Optional[InboxEvent]:
        """Get inbox event by provider and provider event ID."""
        pass
    
    @abstractmethod
    async def list_by_provider(self, provider: str, limit: int = 100) -> List[InboxEvent]:
        """List inbox events by provider."""
        pass


class OutboxRepoIface(ABC):
    """Interface for outbox messages repository."""
    
    @abstractmethod
    async def create(self, message: OutboxMessage) -> OutboxMessage:
        """Create a new outbox message."""
        pass
    
    @abstractmethod
    async def get_by_provider_id(self, channel: str, provider_message_id: str) -> Optional[OutboxMessage]:
        """Get outbox message by channel and provider message ID."""
        pass
    
    @abstractmethod
    async def list_by_channel(self, channel: str, limit: int = 100) -> List[OutboxMessage]:
        """List outbox messages by channel."""
        pass
    
    @abstractmethod
    async def mark_sent(self, message_id: int, provider_message_id: str) -> OutboxMessage:
        """Mark a message as sent."""
        pass
    
    @abstractmethod
    async def mark_failed(self, message_id: int, error: str) -> OutboxMessage:
        """Mark a message as failed."""
        pass


class IncidentsRepoIface(ABC):
    """Interface for incidents repository."""
    
    @abstractmethod
    async def create(self, incident: dict) -> dict:
        """Create a new incident."""
        pass
    
    @abstractmethod
    async def get_by_id(self, incident_id: int) -> Optional[dict]:
        """Get incident by ID."""
        pass
    
    @abstractmethod
    async def list_active(self, limit: int = 100) -> List[dict]:
        """List active incidents."""
        pass
    
    @abstractmethod
    async def update(self, incident_id: int, updates: dict) -> dict:
        """Update an incident."""
        pass

