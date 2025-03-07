# Bills New API Documentation

This document provides an overview of the API endpoints available in the `bills_new` app and examples of how to use them.

## Base URL

All API endpoints are accessible under the base path `/api/new/`.

## Authentication

Currently, during the testing phase, the API allows anonymous access. In production, proper authentication will be required.

## Available Endpoints

### Persons

Manage person profiles linked to user accounts.

- **List all persons**: `GET /api/new/persons/`
- **Create a person**: `POST /api/new/persons/`
- **Retrieve a person**: `GET /api/new/persons/{id}/`
- **Update a person**: `PUT /api/new/persons/{id}/`
- **Partial update a person**: `PATCH /api/new/persons/{id}/`
- **Delete a person**: `DELETE /api/new/persons/{id}/`
- **Current user info**: `GET /api/new/persons/me/`

### Groups

Manage expense sharing groups.

- **List all groups**: `GET /api/new/groups/`
- **Create a group**: `POST /api/new/groups/`
- **Retrieve a group**: `GET /api/new/groups/{id}/`
- **Update a group**: `PUT /api/new/groups/{id}/`
- **Partial update a group**: `PATCH /api/new/groups/{id}/`
- **Delete a group**: `DELETE /api/new/groups/{id}/`
- **Add member to group**: `POST /api/new/groups/{id}/add_member/`
- **Remove member from group**: `POST /api/new/groups/{id}/remove_member/`

### Bills

Manage shared bills.

- **List all bills**: `GET /api/new/bills/`
- **Create a bill**: `POST /api/new/bills/`
- **Retrieve a bill**: `GET /api/new/bills/{id}/`
- **Update a bill**: `PUT /api/new/bills/{id}/`
- **Partial update a bill**: `PATCH /api/new/bills/{id}/`
- **Delete a bill**: `DELETE /api/new/bills/{id}/`
- **Bill details**: `GET /api/new/bills/{id}/details/`
- **Recalculate all shares**: `POST /api/new/bills/{id}/recalculate_shares/`

### Bill Participants

Manage participants on a bill.

- **List all bill participants**: `GET /api/new/bill-participants/`
- **Create a bill participant**: `POST /api/new/bill-participants/`
- **Retrieve a bill participant**: `GET /api/new/bill-participants/{id}/`
- **Update a bill participant**: `PUT /api/new/bill-participants/{id}/`
- **Partial update a bill participant**: `PATCH /api/new/bill-participants/{id}/`
- **Delete a bill participant**: `DELETE /api/new/bill-participants/{id}/`
- **Calculate owed amount**: `POST /api/new/bill-participants/{id}/calculate_owed/`

Response format for bill participant endpoints:
```json
{
    "id": 1,
    "bill": 2,
    "person": 1,
    "owed_amount": "25.00",     // Calculated and stored amount this person owes
    "paid_amount": "50.00",     // Calculated from bill payments (read-only)
    "balance": "25.00"          // Calculated difference (read-only)
}
```

### Bill Items

Manage individual items within a bill.

- **List all bill items**: `GET /api/new/bill-items/`
- **Create a bill item**: `POST /api/new/bill-items/`
- **Retrieve a bill item**: `GET /api/new/bill-items/{id}/`
- **Update a bill item**: `PUT /api/new/bill-items/{id}/`
- **Partial update a bill item**: `PATCH /api/new/bill-items/{id}/`
- **Delete a bill item**: `DELETE /api/new/bill-items/{id}/`

### Item Shares

Manage how bill items are shared among participants.

- **List all item shares**: `GET /api/new/item-shares/`
- **Create an item share**: `POST /api/new/item-shares/`
- **Retrieve an item share**: `GET /api/new/item-shares/{id}/`
- **Update an item share**: `PUT /api/new/item-shares/{id}/`
- **Partial update an item share**: `PATCH /api/new/item-shares/{id}/`
- **Delete an item share**: `DELETE /api/new/item-shares/{id}/`

### Payments

Manage payments between participants and for bills.

- **List all payments**: `GET /api/new/payments/`
- **Create a payment**: `POST /api/new/payments/`
- **Retrieve a payment**: `GET /api/new/payments/{id}/`
- **Update a payment**: `PUT /api/new/payments/{id}/`
- **Partial update a payment**: `PATCH /api/new/payments/{id}/`
- **Delete a payment**: `DELETE /api/new/payments/{id}/`
- **List settlements only**: `GET /api/new/payments/settlements/`
- **List bill payments only**: `GET /api/new/payments/bill_payments/`
- **Payments for a specific bill**: `GET /api/new/payments/by_bill/?bill_id={id}`
- **Create settlement payment**: `POST /api/new/payments/create_settlement/`
- **Create bill payment**: `POST /api/new/payments/create_bill_payment/`
- **Person balance**: `GET /api/new/payments/balance/?person_id={id}`
- **Balance between people**: `GET /api/new/payments/balance_between/?person1_id={id}&person2_id={id}`

## Example: Creating a Complete Bill

Creating a bill with participants, items, and item shares involves multiple API calls. Here's a step-by-step example:

### 1. Create a Bill

```json
POST /api/new/bills/
{
    "title": "Dinner at Italian Restaurant",
    "description": "Saturday night dinner",
    "date": "2023-11-18",
    "group": 1
}
```

Response:
```json
{
    "id": 2,
    "title": "Dinner at Italian Restaurant",
    "description": "Saturday night dinner",
    "date": "2023-11-18",
    "created_at": "2023-11-19T12:00:00Z",
    "created_by": 1,
    "group": 1,
    "participants": [],
    "total_amount": "0.00",
    "items": [],
    "bill_participants": []
}
```

### 2. Add Participants to the Bill

```json
POST /api/new/bill-participants/
{
    "bill": 2,
    "person": 1
}
```

Note: The owed_amount will be automatically calculated based on item shares. The paid_amount is calculated from bill payments.

```json
POST /api/new/bill-participants/
{
    "bill": 2,
    "person": 2
}
```

```json
POST /api/new/bill-participants/
{
    "bill": 2,
    "person": 3
}
```

### 3. Add Items to the Bill

```json
POST /api/new/bill-items/
{
    "bill": 2,
    "name": "Pizza Margherita",
    "price": "15.00"
}
```

```json
POST /api/new/bill-items/
{
    "bill": 2,
    "name": "Spaghetti Carbonara",
    "price": "18.00"
}
```

```json
POST /api/new/bill-items/
{
    "bill": 2,
    "name": "Tiramisu",
    "price": "8.00"
}
```

```json
POST /api/new/bill-items/
{
    "bill": 2,
    "name": "Bottle of Wine",
    "price": "30.00"
}
```

### 4. Add Item Shares

Equal split for Pizza (all participants):

```json
POST /api/new/item-shares/
{
    "item": 4,
    "person": 1,
    "split_type": "EQUAL"
}
```

```json
POST /api/new/item-shares/
{
    "item": 4,
    "person": 2,
    "split_type": "EQUAL"
}
```

```json
POST /api/new/item-shares/
{
    "item": 4,
    "person": 3,
    "split_type": "EQUAL"
}
```

Spaghetti for person 1 only:

```json
POST /api/new/item-shares/
{
    "item": 5,
    "person": 1,
    "split_type": "EXACT",
    "exact_amount": "18.00"
}
```

Tiramisu shared by person 2 and 3:

```json
POST /api/new/item-shares/
{
    "item": 6,
    "person": 2,
    "split_type": "EQUAL"
}
```

```json
POST /api/new/item-shares/
{
    "item": 6,
    "person": 3,
    "split_type": "EQUAL"
}
```

Wine split by percentage:

```json
POST /api/new/item-shares/
{
    "item": 7,
    "person": 1,
    "split_type": "PERCENTAGE",
    "percentage": "50.00"
}
```

```json
POST /api/new/item-shares/
{
    "item": 7,
    "person": 2,
    "split_type": "PERCENTAGE",
    "percentage": "25.00"
}
```

```json
POST /api/new/item-shares/
{
    "item": 7,
    "person": 3,
    "split_type": "PERCENTAGE",
    "percentage": "25.00"
}
```

### 5. Record Payments

#### 5.1 Bill Payment (Person contributes to bill)

```json
POST /api/new/payments/create_bill_payment/
{
    "person": 1,
    "bill": 2,
    "amount": 50.00,
    "date": "2023-11-18",
    "description": "Initial payment at restaurant"
}
```

```json
POST /api/new/payments/create_bill_payment/
{
    "person": 2,
    "bill": 2,
    "amount": 25.00,
    "date": "2023-11-18",
    "description": "Cash contribution"
}
```

#### 5.2 Settlement Payment (Person pays another person directly)

```json
POST /api/new/payments/create_settlement/
{
    "from_person": 3,
    "to_person": 1,
    "amount": 20.00,
    "date": "2023-11-19",
    "description": "Paid via bank transfer"
}
```

### 6. Get Bill Details and Balances

Get bill details:
```
GET /api/new/bills/2/details/
```

Get payments for the bill:
```
GET /api/new/payments/by_bill/?bill_id=2
```

Get a person's overall balance:
```
GET /api/new/payments/balance/?person_id=1
```

Get balance between two people:
```
GET /api/new/payments/balance_between/?person1_id=1&person2_id=3
```

## Split Types

The following split types are available for item shares:

- `EQUAL`: Split the cost equally among all participants
- `PERCENTAGE`: Split based on percentage values for each participant
- `EXACT`: Specify an exact amount for each participant
- `SHARES`: Split based on share units (e.g., 2 shares vs 1 share)
- `ADJUSTED`: Equal split with adjustments

## Payment Types

The system supports two types of payments:

- `BILL`: A payment made by a person toward a bill (contributes to their paid amount)
- `SETTLEMENT`: A direct payment between two people to settle debts

For settlements, the system creates a pair of transactions:
1. A positive amount record for the payer (money going out)
2. A negative amount record for the receiver (money coming in)

These pairs are linked via the `paired_payment` field.

## Important Implementation Notes

### Automatic Calculations

1. **Owed Amount Updates**: The `owed_amount` for bill participants is automatically recalculated when:
   - A new item is added to the bill
   - An item share is created or modified
   - The recalculate endpoint is called

2. **Paid Amount Calculation**: The `paid_amount` is always calculated in real-time from the sum of BILL type payments made by the participant.

3. **Balance Calculation**: The `balance` is a real-time calculation of `paid_amount - owed_amount`

### Concurrency Considerations

1. **Item Share Updates**: When multiple item shares are being created or updated simultaneously, the system ensures consistent owed amount calculations by:
   - Processing each share update sequentially
   - Recalculating the total owed amount for affected participants after each change

2. **Payment Processing**: Bill payments and settlements are processed atomically to ensure consistent balances.

### Best Practices

1. **Creating Bill Participants**: Create bill participants before adding item shares for them.

2. **Updating Shares**: After bulk updates to item shares, call the bill's recalculate_shares endpoint to ensure consistency.

3. **Monitoring Balances**: Use the bill details endpoint to get the most up-to-date view of all participants' balances.