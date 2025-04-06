from fastapi import APIRouter

from app.api.routes import users, loan_accounts, repayments, cards, rewards, transactions

api_router = APIRouter()

api_router.include_router(users.router, prefix="/users", tags=["users"])
api_router.include_router(loan_accounts.router, tags=["loan-accounts"])
api_router.include_router(repayments.router, prefix="/repayments", tags=["repayments"])
api_router.include_router(cards.router, prefix="/cards", tags=["cards"])
api_router.include_router(rewards.router, prefix="/rewards", tags=["rewards"])
api_router.include_router(transactions.router, prefix="/transactions", tags=["transactions"])
