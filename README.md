# 🏦 Lenme API - Peer-to-Peer Lending Platform

## Project Overview

This Django REST API project implements a peer-to-peer lending platform for Lenme, facilitating loan applications, funding, and repayment processes between borrowers and lenders.

## Configuration & Setup

### Prerequisites
- Python 3.8+
- PostgreSQL (preferred) or SQLite
- Redis (for background tasks)
- pip

### Installation

1. **Clone the repository**
```bash
git clone https://github.com/devkhedr/lenme-api.git
cd lenme-project
```

2. **Set up virtual environment**
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. **Install dependencies**
```bash
pip install -r requirements.txt
```

4. **Database Configuration**
Create a `.env` file in the project root:
```env
DB_NAME=your_db_name
DB_USER=your_db_user
DB_PASSWORD=your_db_password
DB_HOST=localhost
DB_PORT=5432
```

5. **Install and start Redis**
```bash
# Ubuntu/Debian
sudo apt-get install redis-server
sudo systemctl start redis-server

# macOS
brew install redis
brew services start redis
```

6. **Run migrations**
```bash
python manage.py makemigrations
python manage.py migrate
```

7. **Run tests**
```bash
pytest
```

8. **Start the application**
```bash
# Terminal 1: Start Django server
python manage.py runserver

# Terminal 2: Start Celery worker
celery -A core worker --loglevel=info

# Terminal 3: Start Celery Beat scheduler
celery -A core beat --loglevel=info
```

The API will be available at `http://localhost:8000/`


## Project Requirements Implementation

### Core Functionality

1. **Loan Request Submission**: Borrowers can submit loan requests (e.g., $5,000 for 6 months)
2. **Available Loans Listing**: Lenders can retrieve loans without assigned lenders
3. **Offer Submission**: Lenders can submit offers with interest rates (e.g., 15% APR)
4. **Offer Acceptance**: Borrowers can accept lender offers
5. **Balance Validation**: System ensures lenders have sufficient funds (Loan Amount + $3.75 Lenme Fee)
6. **Loan Funding**: Automatic status update to "Funded" upon successful funding
7. **Payment Scheduling**: Six monthly payments scheduled from funding date
8. **Payment Processing**: API for borrowers to make monthly payments
9. **Loan Completion**: Status updates to "Completed" after all payments

### Technical Features

- **Database**: PostgreSQL (preferred) with Django ORM
- **Authentication**: User management for borrowers and lenders
- **Balance Management**: Account balance tracking and validation
- **Payment Calculations**: Simple interest calculations for monthly payments
- **Automated Tasks**: Celery-powered background repayment processing
- **Unit Testing**: Comprehensive pytest test suite (30 tests covering complete workflow)
- **API Documentation**: Swagger/OpenAPI integration

## Models & Database Schema

### Core Models

#### UserProfile
- **user**: OneToOne relationship with Django User
- **balance**: Decimal field for account balance (lenders need sufficient funds)
- **user_type**: Choice between 'borrower' and 'lender'

#### Loan
- **borrower**: Foreign key to User (loan applicant)
- **lender**: Foreign key to User (nullable until funded)
- **loan_amount**: Requested amount (e.g., $5,000)
- **loan_period_months**: Repayment period (e.g., 6 months)
- **annual_interest_rate**: Interest rate (e.g., 15%, nullable until funded)
- **lenme_fee**: Platform fee ($3.75)
- **total_loan_amount**: loan_amount + lenme_fee
- **status**: 'pending' → 'funded' → 'completed'
- **created_at**: Loan creation timestamp
- **funded_at**: Timestamp when loan was funded

#### LoanOffer
- **loan**: Foreign key to Loan
- **lender**: Foreign key to User
- **annual_interest_rate**: Offered interest rate
- **created_at**: Offer creation timestamp
- **is_accepted**: Boolean flag

#### Payment
- **loan**: Foreign key to Loan
- **payment_number**: Sequential payment number (1-6 for 6-month loan)
- **amount**: Monthly payment amount
- **due_date**: Payment due date
- **status**: 'pending' or 'paid'
- **paid_at**: Timestamp when payment was made
- **platform_fee**: Lenme's portion ($3.75 ÷ 6 months)
- **lender_amount**: Lender's portion

## API Endpoints Documentation

### Complete Lending Flow (Use Case Example)

#### 1. Create Users
```http
POST /api/lending/user/
{
    "username": "borrower_user",
    "email": "borrower@example.com",
    "password": "secure123",
    "user_type": "borrower"
}

POST /api/lending/user/
{
    "username": "lender_user", 
    "email": "lender@example.com",
    "password": "secure123",
    "user_type": "lender",
    "balance": "10000.00"
}
```

#### 2. Borrower Submits Loan Request ($5,000 for 6 months)
```http
POST /api/lending/loan/
{
    "borrower_id": 1,
    "loan_amount": "5000.00",
    "loan_period_months": 6
}
```

#### 3. Lender Views Available Loans
```http
GET /api/lending/loan-list/
```

#### 4. Lender Submits Offer (15% Annual Interest Rate)
```http
POST /api/lending/offers/submit/
{
    "loan_id": 1,
    "lender_id": 2,
    "annual_interest_rate": "15.0"
}
```

#### 5. Borrower Accepts Offer (Loan becomes "Funded")
```http
POST /api/lending/offers/accept/
{
    "offer_id": 1
}
```

#### 6. View Loan Details & Payment Schedule
```http
GET /api/lending/loan/1/
```

#### 7. Borrower Makes Monthly Payments
```http
POST /api/payment/make/
{
    "payment_id": 1,
    "borrower_id": 1
}
```

## Business Logic Implementation

### Payment Calculation (Simple Interest)
For the $5,000 loan at 15% APR over 6 months:
- **Monthly Interest Rate**: 15% ÷ 12 = 1.25%
- **Principal Portion**: $5,003.75 ÷ 6 = $833.96
- **Interest Portion**: $5,003.75 × 1.25% = $62.55
- **Monthly Payment**: $833.96 + $62.55 = $896.51

### Lenme Fee Distribution
- **Total Fee**: $3.75 per loan (paid by lender)
- **Monthly Platform Fee**: $3.75 ÷ 6 = $0.625 per payment
- **Monthly Lender Amount**: $896.51 - $0.625 = $895.885 per payment

### Balance Validation System
1. **At Offer Submission**: Verify lender has ≥ $5,003.75 ($5,000 + $3.75)
2. **At Offer Acceptance**: Re-verify balance (prevents double-spending)
3. **Automatic Deduction**: Balance reduced when loan is funded

### Loan Status Flow
```
PENDING → FUNDED → COMPLETED
   ↑         ↑         ↑
Loan      Offer     All payments
Request   Accepted   completed
```

## Security Features

- Balance validation at multiple checkpoints
- User type verification for appropriate actions
- Offer uniqueness constraints
- Transaction atomicity for financial operations


### Use Case Data Flow
```
Borrower Request → Available Loans → Lender Offer → Acceptance → Funding → Payments → Completion
     ($5K/6mo)        (API List)      (15% APR)     (Accept)    (Funded)   (6 × $896.51)  (Completed)
```

## Unit Testing

Comprehensive test coverage for the lending workflow as required:

### Test Execution
```bash
pytest                              # Run all tests
pytest -v                          # Verbose output
pytest tests/test_lending_workflow.py  # Specific workflow tests
```

### Required Test Coverage
**Borrower Loan Request, Lender Offer, and Loan Funding Process Tests:**

1. **Loan Request Tests**:
   - Successful $5,000 loan request for 6 months
   - Validation for missing required fields
   - Non-existent borrower handling

2. **Lender Offer Tests**:
   - Successful offer submission with 15% interest rate
   - Insufficient balance validation (< $5,003.75)
   - Offer on non-existent loans

3. **Loan Funding Process Tests**:
   - Successful offer acceptance and funding
   - Balance deduction ($5,003.75 from lender)
   - Loan status update (pending → funded)
   - Payment schedule creation (6 monthly payments)
   - Double-acceptance prevention

### Complete Test Suite (30 Tests)
- User creation and management
- Loan application workflow
- Offer system validation
- Payment processing and scheduling
- Platform fee calculations
- Error handling and edge cases
- Integration testing end-to-end flow


## Background Tasks

Implemented Celery for automated loan repayment processing:

### Automated Repayment Processing
- **Hourly Task**: Automatically processes loan repayments every hour
- **Balance Validation**: Checks borrower balances before processing
- **Payment Distribution**: Automatically distributes payments between lenders and platform
- **Loan Completion**: Marks loans as completed when all payments are made


## Security Features

- Balance validation at multiple checkpoints
- User type verification for appropriate actions
- Offer uniqueness constraints
- Transaction atomicity for financial operations

---

*This Django REST API project fulfills all requirements for the Lenme peer-to-peer lending platform, including the specific $5,000/6-month/15% APR use case with comprehensive unit testing coverage.*