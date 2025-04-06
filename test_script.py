#!/usr/bin/env python3
"""
Loan Management System API Client

This script demonstrates how to use the Loan Management System API
to populate data and test the key features.
"""

import requests
import json
import time
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from enum import Enum


# Enums to match API
class UserKYCStatus(str, Enum):
    PENDING = "pending"
    VERIFIED = "verified"
    REJECTED = "rejected"


class UserAccountStatus(str, Enum):
    ACTIVE = "active"
    SUSPENDED = "suspended"
    CLOSED = "closed"


# Base URL for the API
BASE_URL = "http://localhost:8000/api/v1"

# Headers for API requests
HEADERS = {
    "Content-Type": "application/json",
    "Accept": "application/json"
}


class LMSClient:
    """Client for interacting with the Loan Management System API."""

    def __init__(self, base_url: str = BASE_URL):
        """Initialize the client with the base URL."""
        self.base_url = base_url
        self.users = {}  # Cache for created users
        self.loan_accounts = {}  # Cache for created loan accounts
        self.cards = {}  # Cache for created cards

    def _make_request(self, method: str, endpoint: str, data: Optional[Dict] = None) -> Dict:
        """Make a request to the API and return the response data."""
        url = f"{self.base_url}{endpoint}"

        try:
            print(f"\nMaking {method} request to {url}")
            if data:
                print(f"Request data: {json.dumps(data, indent=2)}")

            if method.upper() == "GET":
                response = requests.get(url, headers=HEADERS)
            elif method.upper() == "POST":
                response = requests.post(url, headers=HEADERS, json=data)
            elif method.upper() == "PUT":
                response = requests.put(url, headers=HEADERS, json=data)
            elif method.upper() == "DELETE":
                response = requests.delete(url, headers=HEADERS)
            else:
                raise ValueError(f"Unsupported HTTP method: {method}")

            # Print response for debugging
            print(f"Response status: {response.status_code}")
            if response.content:
                try:
                    print(f"Response content: {json.dumps(response.json(), indent=2)}")
                except:
                    print(f"Response content: {response.content}")

            # Check if the request was successful
            response.raise_for_status()

            # Parse the response
            response_data = response.json()

            # Check response status
            if response_data.get("status") != "success":
                raise requests.exceptions.RequestException(
                    f"API returned error: {response_data.get('error', 'Unknown error')}"
                )

            # Return just the data part of the response
            return response_data.get("data", {})

        except requests.exceptions.RequestException as e:
            if response and response.content:
                try:
                    error_data = response.json()
                    if "detail" in error_data:
                        raise requests.exceptions.RequestException(
                            f"API Error: {error_data['detail']}"
                        ) from e
                except json.JSONDecodeError:
                    pass
            raise e

    # User Management
    def create_user(self, name: str, email: str, phone: str, password: str) -> Dict:
        """Create a new user."""
        data = {
            "name": name,
            "email": email,
            "phone": phone,
            "password": password,
            "kyc_status": UserKYCStatus.VERIFIED,
            "account_status": UserAccountStatus.ACTIVE
        }

        try:
            user = self._make_request("POST", "/users/", data)
            self.users[user["id"]] = user
            print(f"Created user: {name} (ID: {user['id']})")
            return user
        except requests.exceptions.RequestException as e:
            print(f"Failed to create user: {e}")
            raise

    def get_user(self, user_id: int) -> Dict:
        """Get user details by ID."""
        user = self._make_request("GET", f"/users/{user_id}")
        return user

    # Loan Account Management
    def create_loan_account(self, user_id: int, credit_limit: float, apr: float = 25.0) -> Dict:
        """Create a new loan account for a user."""
        data = {
            "user_id": user_id,
            "credit_limit": credit_limit,
            "apr": apr
        }

        loan_account = self._make_request("POST", "/loan-accounts/", data)
        self.loan_accounts[loan_account["id"]] = loan_account
        print(f"Created loan account for user {user_id} (ID: {loan_account['id']})")
        return loan_account

    def get_loan_account(self, loan_account_id: int) -> Dict:
        """Get loan account details by ID."""
        loan_account = self._make_request("GET", f"/loan-accounts/{loan_account_id}")
        return loan_account

    def apply_daily_interest(self, loan_account_id: int) -> Dict:
        """Apply daily interest to a loan account."""
        result = self._make_request("POST", f"/loan-accounts/{loan_account_id}/apply-interest")
        print(f"Applied interest to loan account {loan_account_id}: £{result['interest_applied']:.2f}")
        return result

    def apply_late_fee(self, loan_account_id: int) -> Dict:
        """Apply a late fee to a loan account if applicable."""
        result = self._make_request("POST", f"/loan-accounts/{loan_account_id}/apply-late-fee")
        if result.get("fee_applied", 0) > 0:
            print(f"Applied late fee to loan account {loan_account_id}: £{result['fee_applied']:.2f}")
        else:
            print(
                f"No late fee applied to loan account {loan_account_id}: {result.get('reason', 'No reason provided')}")
        return result

    # Card Management
    def create_card(self, user_id: int, loan_account_id: int, card_type: str = "virtual") -> Dict:
        """Create a new card for a user and loan account."""
        data = {
            "user_id": user_id,
            "loan_account_id": loan_account_id,
            "type": card_type,
            "status": "active"
        }

        card = self._make_request("POST", "/cards/", data)
        self.cards[card["id"]] = card
        print(f"Created {card_type} card for user {user_id} (ID: {card['id']})")
        return card

    def lock_card(self, card_id: int) -> Dict:
        """Lock a card."""
        result = self._make_request("PUT", f"/cards/{card_id}/lock")
        print(f"Locked card {card_id}")
        return result

    def unlock_card(self, card_id: int) -> Dict:
        """Unlock a card."""
        result = self._make_request("PUT", f"/cards/{card_id}/unlock")
        print(f"Unlocked card {card_id}")
        return result

    # Repayment Management
    def get_repayment_options(self, loan_account_id: int) -> Dict:
        """Get repayment options for a loan account."""
        options = self._make_request("GET", f"/repayments/loan-accounts/{loan_account_id}/repayment-options")
        print(f"\nRepayment options for loan account {loan_account_id}:")
        print(f"Current balance: £{options['current_balance']:.2f}")
        print(f"Current APR: {options['current_apr']}%")
        print("\nAvailable options:")
        for option in options['options']:
            print(f"- Pay {option['percentage']}% (£{option['amount']:.2f})")
            print(f"  Interest to pay next month: £{option['interest_to_pay']:.2f}")
            print(f"  Interest saved: £{option['interest_saved']:.2f}")
        return options

    def make_repayment(self, loan_account_id: int, amount: float, method: str = "manual") -> Dict:
        """Process a repayment for a loan account."""
        data = {
            "loan_account_id": loan_account_id,
            "amount": amount,
            "method": method.lower()  # Convert to lowercase to match the enum values
        }

        print(f"Making repayment with data: {data}")
        result = self._make_request("POST", "/repayments/", data)
        print(f"Made repayment of £{amount:.2f} to loan account {loan_account_id}")
        return result

    # Reward Management
    def check_rewards(self, user_id: int) -> Dict:
        """Check if a user is eligible for APR reduction and apply if eligible."""
        result = self._make_request("POST", f"/rewards/users/{user_id}/check-rewards")
        if result.get("eligible", False):
            print(f"Applied APR reduction for user {user_id}: {result['old_apr']}% -> {result['new_apr']}%")
        else:
            print(f"User {user_id} not eligible for APR reduction: {result.get('reason', 'No reason provided')}")
        return result

    def get_reward_history(self, user_id: int) -> List[Dict]:
        """Get reward history for a user."""
        history = self._make_request("GET", f"/rewards/users/{user_id}/rewards")
        print(f"Retrieved reward history for user {user_id}")
        return history

    # Transaction Management
    def get_transactions(self, loan_account_id: int) -> List[Dict]:
        """Get all transactions for a loan account."""
        transactions = self._make_request("GET", f"/transactions/loan-accounts/{loan_account_id}/transactions")
        print(f"Retrieved transactions for loan account {loan_account_id}")
        return transactions

    def create_transaction(self, loan_account_id: int, amount: float, type: str, description: str = None) -> Dict:
        """Create a new transaction."""
        data = {
            "loan_account_id": loan_account_id,
            "type": type.lower(),  # Convert to lowercase to match the enum values
            "amount": amount,
            "description": description
        }

        transaction = self._make_request("POST", "/transactions/", data)
        print(f"Created {type} transaction for £{amount:.2f} on loan account {loan_account_id}")
        return transaction

    def get_statement(self, loan_account_id: int) -> Dict:
        """Get a statement for a loan account."""
        statement = self._make_request("GET", f"/transactions/loan-accounts/{loan_account_id}/statement")
        print(f"Retrieved statement for loan account {loan_account_id}")
        return statement


def populate_sample_data():
    """Populate the system with sample data and demonstrate key features."""
    client = LMSClient()

    try:
        # Generate unique timestamp for email addresses
        timestamp = int(time.time())
        
        print("\n=== Creating Users ===")
        user1 = client.create_user(
            name="John Doe",
            email=f"john.doe.{timestamp}@example.com",
            phone="+44123456789",
            password="password123"
        )

        user2 = client.create_user(
            name="Jane Smith",
            email=f"jane.smith.{timestamp}@example.com",
            phone="+44987654321",
            password="password456"
        )

        print("\n=== Creating Loan Accounts ===")
        loan_account1 = client.create_loan_account(
            user_id=user1["id"],
            credit_limit=5000.0,
            apr=25.0  # Adding default APR
        )

        loan_account2 = client.create_loan_account(
            user_id=user2["id"],
            credit_limit=7500.0,
            apr=25.0  # Adding default APR
        )

        print("\n=== Creating Cards ===")
        virtual_card = client.create_card(
            user_id=user1["id"],
            loan_account_id=loan_account1["id"],
            card_type="virtual"
        )

        physical_card = client.create_card(
            user_id=user1["id"],
            loan_account_id=loan_account1["id"],
            card_type="physical"
        )

        print("\n=== Demonstrating Card Security ===")
        # Lock and unlock a card
        client.lock_card(virtual_card["id"])
        time.sleep(1)  # Small delay for demonstration
        client.unlock_card(virtual_card["id"])

        print("\n=== Simulating Account Activity ===")
        # Add some purchases to build up a balance
        purchases = [
            ("Grocery shopping", 150.0),
            ("Electronics", 500.0),
            ("Dining out", 75.0),
            ("Online shopping", 275.0)
        ]
        
        for desc, amount in purchases:
            client.create_transaction(
                loan_account_id=loan_account1["id"],
                amount=amount,
                type="purchase",
                description=desc
            )
            time.sleep(0.5)  # Small delay between transactions
        
        # Get updated loan account
        loan_account1 = client.get_loan_account(loan_account1["id"])
        print(f"Current balance after purchases: £{loan_account1['current_balance']:.2f}")

        # Apply interest for a few days to build up some balance
        for day in range(5):
            client.apply_daily_interest(loan_account1["id"])
            time.sleep(0.5)

        # Apply a late fee
        client.apply_late_fee(loan_account1["id"])

        # Get updated loan account
        loan_account1 = client.get_loan_account(loan_account1["id"])
        print(f"Balance after interest and fees: £{loan_account1['current_balance']:.2f}")

        print("\n=== Demonstrating Repayment Options ===")
        # Get repayment options
        options = client.get_repayment_options(loan_account1["id"])

        # Display options with interest transparency
        print("Repayment options:")
        for option in options["options"]:
            print(f"  {option['percentage']}%: £{option['amount']:.2f} "
                  f"(Interest to pay: £{option['interest_to_pay']:.2f}, "
                  f"Interest saved: £{option['interest_saved']:.2f})")

        print("\n=== Making Repayments ===")
        # Make a series of repayments
        repayments = [
            (200.0, "First repayment"),
            (300.0, "Second repayment"),
            (250.0, "Third repayment")
        ]
        
        for amount, desc in repayments:
            client.make_repayment(
                loan_account_id=loan_account1["id"],
                amount=amount,
                method="manual"
            )
            
            # Check for rewards after each repayment
            client.check_rewards(user1["id"])
            time.sleep(0.5)

        print("\n=== Checking Final Status ===")
        reward_history = client.get_reward_history(user1["id"])
        print("Reward history:")
        rewards = reward_history.get("data", {}).get("rewards", [])
        for reward in rewards:
            adjusted_on = reward['adjusted_on'].split('T')[0] if 'T' in reward['adjusted_on'] else reward['adjusted_on']
            print(f"  {adjusted_on}: {reward['old_apr']}% -> {reward['new_apr']}% ({reward['reason']})")
        
        print("\nDone!")

        # Get statement
        statement = client.get_statement(loan_account1["id"])
        print("\nStatement summary:")
        print(f"  Current balance: £{statement['summary']['current_balance']:.2f}")
        print(f"  Current APR: {statement['summary']['current_apr']}%")
        print(f"  Total purchases: £{statement['summary']['total_purchases']:.2f}")
        print(f"  Total interest: £{statement['summary']['total_interest']:.2f}")
        print(f"  Total fees: £{statement['summary']['total_fees']:.2f}")
        print(f"  Total repayments: £{statement['summary']['total_repayments']:.2f}")

        print("\n=== Data Population Complete ===")

    except requests.exceptions.RequestException as e:
        print(f"\nError during data population: {e}")
        raise


if __name__ == "__main__":
    try:
        populate_sample_data()
    except requests.exceptions.RequestException as e:
        print(f"Error: {e}")
        print("\nMake sure the LMS API is running at http://localhost:8000")
        print("You can start it with: docker-compose up -d") 