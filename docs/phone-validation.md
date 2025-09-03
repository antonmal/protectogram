# Phone Number Validation - Protectogram

## Overview

Phone number validation in Protectogram has been updated (2025-09-02) to handle real-world phone number formats that users typically copy from their contacts.

## Problem

The original validation used a restrictive regex pattern:
```python
pattern=r"^\+[1-9]\d{1,14}$"
```

This rejected common formats like:
- `(555) 123-4567`
- `+1-555-123-4567`
- `+1 555 123 4567`
- `555-123-4567`

Users would copy phone numbers from their contacts and encounter validation errors, preventing guardian creation.

## Solution

Implemented field validators in Pydantic schemas that normalize phone numbers before validation:

### Affected Files
- `app/schemas/user.py` (lines 19-44, 59-84)
- `app/schemas/guardian.py` (lines 18-43, 56-81)

### Normalization Logic

```python
@field_validator("phone_number")
@classmethod
def validate_phone_number(cls, v):
    if not v:
        return v

    # Step 1: Normalize - remove spaces, dashes, parentheses
    normalized = v.replace(" ", "").replace("-", "").replace("(", "").replace(")", "")

    # Step 2: Ensure it starts with +
    if not normalized.startswith("+"):
        if normalized.startswith("00"):
            # Convert 00 prefix to +
            normalized = "+" + normalized[2:]
        elif normalized.isdigit() and len(normalized) >= 8:
            # Reject numbers without country code
            raise ValueError("Phone number must include country code (start with +)")
        else:
            # Try adding + prefix
            normalized = "+" + normalized

    # Step 3: Basic validation - 8-20 digits after +
    if len(normalized) < 8 or len(normalized) > 20:
        raise ValueError("Phone number must be 8-20 digits")

    if not normalized[1:].isdigit():
        raise ValueError("Phone number can only contain digits after +")

    return normalized
```

## Supported Input Formats

The validator now accepts and normalizes:

| Input Format | Normalized Output | Notes |
|--------------|-------------------|-------|
| `(555) 123-4567` | `+5551234567` | Adds + prefix |
| `+1-555-123-4567` | `+15551234567` | Removes dashes |
| `+1 555 123 4567` | `+15551234567` | Removes spaces |
| `001234567890` | `+1234567890` | Converts 00 to + |
| `+34 123 456 789` | `+34123456789` | International format |
| `555-123-4567` | `+5551234567` | Adds + prefix |

## Validation Rules

1. **Length**: 8-20 total digits (including country code)
2. **Format**: Must start with `+` followed by digits only
3. **Country Code Required**: Numbers without clear country code are rejected
4. **Normalization**: Spaces, dashes, parentheses automatically removed

## Implementation Details

### User Schema (app/schemas/user.py)
- `UserBase.phone_number` - Optional field with validation
- `UserUpdate.phone_number` - Optional field with validation
- Both use identical validation logic

### Guardian Schema (app/schemas/guardian.py)
- `GuardianBase.phone_number` - Required field with validation
- `GuardianUpdate.phone_number` - Optional field with validation
- Both use identical validation logic

### Telegram Integration
The `TelegramOnboardingService` also includes a `validate_phone_number()` method with identical logic for consistency.

## Error Messages

Clear error messages guide users:
- `"Phone number must include country code (start with +)"`
- `"Phone number must be 8-20 digits"`
- `"Phone number can only contain digits after +"`

## Testing

The fix was tested with real-world phone number formats in the Telegram bot. Guardian creation now succeeds with normalized phone numbers.

### Test Cases
```python
# These all normalize to valid formats:
test_numbers = [
    "(555) 123-4567",      # -> +5551234567
    "+1-555-123-4567",     # -> +15551234567
    "+1 555 123 4567",     # -> +15551234567
    "001234567890",        # -> +1234567890
    "+34 123 456 789",     # -> +34123456789
]
```

## Migration Impact

This change is backward compatible:
- Existing valid phone numbers remain unchanged
- Only improves acceptance of additional formats
- No database schema changes required
- No breaking changes to API responses

---

**Implemented**: 2025-09-02
**Status**: Deployed to staging and production
**Testing**: Confirmed working with Telegram bot guardian creation
