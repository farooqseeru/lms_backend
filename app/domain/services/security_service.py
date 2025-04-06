from abc import ABC, abstractmethod
from datetime import datetime
from typing import Dict, Any, Optional

from app.core.config import settings


class SecurityService(ABC):
    """Abstract base class for security service."""
    
    @abstractmethod
    def lock_card(self, card_id: int) -> Dict[str, Any]:
        """Lock a card."""
        pass
    
    @abstractmethod
    def unlock_card(self, card_id: int) -> Dict[str, Any]:
        """Unlock a card."""
        pass
    
    @abstractmethod
    def mask_pan(self, pan: str) -> str:
        """Mask PAN (Primary Account Number) for PCI compliance."""
        pass
    
    @abstractmethod
    def mask_cvv(self, cvv: str) -> str:
        """Mask CVV for PCI compliance."""
        pass
    
    @abstractmethod
    def log_security_event(self, user_id: int, action: str, entity_type: str, 
                          entity_id: int, ip_address: str, details: Optional[str] = None) -> Dict[str, Any]:
        """Log a security event."""
        pass


class StandardSecurityService(SecurityService):
    """Standard implementation of security service."""
    
    def __init__(self, db_session):
        """Initialize the service with database session."""
        self.db = db_session
    
    def lock_card(self, card_id: int) -> Dict[str, Any]:
        """Lock a card."""
        from app.domain.models.models import Card, CardStatus, AuditLog
        
        # Get the card
        card = self.db.query(Card).filter(Card.id == card_id).first()
        if not card:
            raise ValueError(f"Card with ID {card_id} not found")
        
        # Check if card is already locked
        if card.status == CardStatus.LOCKED:
            return {
                "success": False,
                "message": "Card is already locked"
            }
        
        # Lock the card
        card.status = CardStatus.LOCKED
        
        # Create audit log
        audit_log = AuditLog(
            user_id=card.user_id,
            action="CARD_LOCK",
            entity_type="Card",
            entity_id=card_id,
            details="Card locked"
        )
        self.db.add(audit_log)
        
        # Commit changes
        self.db.commit()
        
        return {
            "success": True,
            "card_id": card_id,
            "status": card.status,
            "timestamp": datetime.utcnow()
        }
    
    def unlock_card(self, card_id: int) -> Dict[str, Any]:
        """Unlock a card."""
        from app.domain.models.models import Card, CardStatus, AuditLog
        
        # Get the card
        card = self.db.query(Card).filter(Card.id == card_id).first()
        if not card:
            raise ValueError(f"Card with ID {card_id} not found")
        
        # Check if card is already active
        if card.status == CardStatus.ACTIVE:
            return {
                "success": False,
                "message": "Card is already active"
            }
        
        # Check if card can be unlocked (not expired or cancelled)
        if card.status in [CardStatus.EXPIRED, CardStatus.CANCELLED]:
            return {
                "success": False,
                "message": f"Card cannot be unlocked because it is {card.status}"
            }
        
        # Unlock the card
        card.status = CardStatus.ACTIVE
        
        # Create audit log
        audit_log = AuditLog(
            user_id=card.user_id,
            action="CARD_UNLOCK",
            entity_type="Card",
            entity_id=card_id,
            details="Card unlocked"
        )
        self.db.add(audit_log)
        
        # Commit changes
        self.db.commit()
        
        return {
            "success": True,
            "card_id": card_id,
            "status": card.status,
            "timestamp": datetime.utcnow()
        }
    
    def mask_pan(self, pan: str) -> str:
        """Mask PAN (Primary Account Number) for PCI compliance.
        
        Format: XXXX XXXX XXXX 1234 (last 4 digits visible)
        """
        if not pan:
            return ""
        
        # Remove any spaces or dashes
        clean_pan = pan.replace(" ", "").replace("-", "")
        
        # Check if PAN is valid
        if not clean_pan.isdigit() or len(clean_pan) < 13 or len(clean_pan) > 19:
            raise ValueError("Invalid PAN format")
        
        # Mask all but last 4 digits
        masked = "X" * (len(clean_pan) - 4) + clean_pan[-4:]
        
        # Format with spaces for readability
        formatted = ""
        for i in range(0, len(masked), 4):
            formatted += masked[i:i+4] + " "
        
        return formatted.strip()
    
    def mask_cvv(self, cvv: str) -> str:
        """Mask CVV for PCI compliance.
        
        Format: XXX (all digits masked)
        """
        if not cvv:
            return ""
        
        # Check if CVV is valid
        if not cvv.isdigit() or len(cvv) < 3 or len(cvv) > 4:
            raise ValueError("Invalid CVV format")
        
        # Mask all digits
        return "X" * len(cvv)
    
    def log_security_event(self, user_id: int, action: str, entity_type: str, 
                          entity_id: int, ip_address: str, details: Optional[str] = None) -> Dict[str, Any]:
        """Log a security event."""
        from app.domain.models.models import AuditLog
        
        # Create audit log
        audit_log = AuditLog(
            user_id=user_id,
            action=action,
            entity_type=entity_type,
            entity_id=entity_id,
            ip_address=ip_address,
            details=details
        )
        self.db.add(audit_log)
        self.db.commit()
        self.db.refresh(audit_log)
        
        return {
            "log_id": audit_log.id,
            "timestamp": audit_log.timestamp,
            "action": action
        }
