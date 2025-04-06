import pytest
from app.domain.services.security_service import StandardSecurityService
from app.domain.models.models import Card, CardStatus, AuditLog


class TestSecurityService:
    """Test the security service."""
    
    def test_lock_card(self, db_session, test_card):
        """Test locking a card."""
        # Setup
        security_service = StandardSecurityService(db_session)
        
        # Lock card
        result = security_service.lock_card(test_card.id)
        
        # Verify result
        assert result["success"] is True
        assert result["card_id"] == test_card.id
        assert result["status"] == CardStatus.LOCKED
        
        # Verify database changes
        db_session.refresh(test_card)
        assert test_card.status == CardStatus.LOCKED
        
        # Verify audit log
        audit_log = db_session.query(AuditLog).filter(
            AuditLog.entity_type == "Card",
            AuditLog.entity_id == test_card.id,
            AuditLog.action == "CARD_LOCK"
        ).first()
        assert audit_log is not None
    
    def test_lock_card_already_locked(self, db_session, test_card):
        """Test locking a card that is already locked."""
        # Setup
        security_service = StandardSecurityService(db_session)
        test_card.status = CardStatus.LOCKED
        db_session.commit()
        
        # Try to lock card again
        result = security_service.lock_card(test_card.id)
        
        # Verify result
        assert result["success"] is False
        assert "already locked" in result["message"]
    
    def test_unlock_card(self, db_session, test_card):
        """Test unlocking a card."""
        # Setup
        security_service = StandardSecurityService(db_session)
        test_card.status = CardStatus.LOCKED
        db_session.commit()
        
        # Unlock card
        result = security_service.unlock_card(test_card.id)
        
        # Verify result
        assert result["success"] is True
        assert result["card_id"] == test_card.id
        assert result["status"] == CardStatus.ACTIVE
        
        # Verify database changes
        db_session.refresh(test_card)
        assert test_card.status == CardStatus.ACTIVE
        
        # Verify audit log
        audit_log = db_session.query(AuditLog).filter(
            AuditLog.entity_type == "Card",
            AuditLog.entity_id == test_card.id,
            AuditLog.action == "CARD_UNLOCK"
        ).first()
        assert audit_log is not None
    
    def test_unlock_card_already_active(self, db_session, test_card):
        """Test unlocking a card that is already active."""
        # Setup
        security_service = StandardSecurityService(db_session)
        
        # Try to unlock card that's already active
        result = security_service.unlock_card(test_card.id)
        
        # Verify result
        assert result["success"] is False
        assert "already active" in result["message"]
    
    def test_mask_pan(self, db_session):
        """Test masking PAN for PCI compliance."""
        # Setup
        security_service = StandardSecurityService(db_session)
        
        # Test with 16-digit PAN
        pan = "4111111111111111"
        masked = security_service.mask_pan(pan)
        assert masked == "XXXXXXXXXXXX1111"
        
        # Test with formatted PAN
        pan = "4111 1111 1111 1111"
        masked = security_service.mask_pan(pan)
        assert masked == "XXXX XXXX XXXX 1111"
        
        # Test with invalid PAN
        with pytest.raises(ValueError):
            security_service.mask_pan("invalid")
    
    def test_mask_cvv(self, db_session):
        """Test masking CVV for PCI compliance."""
        # Setup
        security_service = StandardSecurityService(db_session)
        
        # Test with 3-digit CVV
        cvv = "123"
        masked = security_service.mask_cvv(cvv)
        assert masked == "XXX"
        
        # Test with 4-digit CVV
        cvv = "1234"
        masked = security_service.mask_cvv(cvv)
        assert masked == "XXXX"
        
        # Test with invalid CVV
        with pytest.raises(ValueError):
            security_service.mask_cvv("invalid")
    
    def test_log_security_event(self, db_session, test_user):
        """Test logging a security event."""
        # Setup
        security_service = StandardSecurityService(db_session)
        
        # Log security event
        result = security_service.log_security_event(
            user_id=test_user.id,
            action="TEST_ACTION",
            entity_type="Test",
            entity_id=1,
            ip_address="127.0.0.1",
            details="Test security event"
        )
        
        # Verify result
        assert "log_id" in result
        assert result["action"] == "TEST_ACTION"
        
        # Verify audit log
        audit_log = db_session.query(AuditLog).filter(
            AuditLog.user_id == test_user.id,
            AuditLog.action == "TEST_ACTION"
        ).first()
        assert audit_log is not None
        assert audit_log.entity_type == "Test"
        assert audit_log.entity_id == 1
        assert audit_log.ip_address == "127.0.0.1"
        assert audit_log.details == "Test security event"
