# Normal extraction vs OCR

- Original: `data/employee_policy.pdf`, page 3, read with PyMuPDF
- Scanned: `data/policy_mixed.pdf`, page 3, read with ocr (pdf2image and pytesseract)
- Word match: **134/138 words (97.1%)**
- Missed or misread words: allowed, leave, not, sick

## Normal extraction

```
Northwind Software - Employee Policy Handbook v4.1
Page 3
Leave Policy
Every employee gets the following paid leave in each calendar year. Leave is added at the
start of the year for existing employees and on a pro-rata basis for new joiners.
Type of leave
Days per year
Carry forward
Earned leave
18
up to 30 days
Sick leave
10
not allowed
Casual leave
6
not allowed
Applying for leave
Apply for earned and casual leave in the HR portal at least 7 days in advance. Your manager
approves or rejects the request within 2 working days.
Sick leave
Sick leave can be taken without approval in advance, but you must tell your manager before 10
am on the first day. For sick leave of more than 2 days in a row, a medical certificate is
needed.
```

## OCR

```
Leave Policy

Every employee gets the following paid leave in each calendar year. Leave is added at the
start of the year for existing employees and on a pro-rata basis for new joiners.

Type of leave Days per year Carry forward

Earned leave | 18 | up to 30 days
'Sickleave 10 “notallowed
| Casual leave | 6 ___| not allowed
Applying for leave

Apply for earned and casual leave in the HR portal at least 7 days in advance. Your manager
approves or rejects the request within 2 working days.
Sick leave

Sick leave can be taken without approval in advance, but you must tell your manager before 10
am on the first day. For sick leave of more than 2 days in a row, a medical certificate is
needed.

Northwind Software - Employee Policy Handbook v4.1 Page 3
```
