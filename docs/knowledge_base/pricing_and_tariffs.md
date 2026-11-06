# VoltFlow EV Charging Network — Pricing & Tariff Structure

## 1. Energy Tariff Fundamentals
- **Billing Basis**: Energy consumption is billed strictly based on certified digital energy meter accumulators using the formula:
  $$\text{Total Cost} = (\text{Final Meter kWh} - \text{Initial Meter kWh}) \times \text{Tariff Rate per kWh}$$
- **Currency & Precision**: All financial records are stored and calculated using fixed-point decimal arithmetic with standard two-decimal currency precision.

## 2. Standard Tariff Rate Bands
- **AC Slow/Normal Charging (Type 2, 7.4 kW - 22 kW)**:
  - Base Rate: **$12.00 to $16.00 per kWh** (ideal for workplace or multi-hour destination parking).
- **DC Fast Charging (CCS2, 50 kW - 90 kW)**:
  - Base Rate: **$16.50 to $22.00 per kWh**.
- **DC Ultra-Fast Charging (CCS2, 120 kW - 350 kW)**:
  - Base Rate: **$22.50 to $28.00 per kWh** (delivers 100 km of driving range in approximately 7 minutes).

## 3. Time-of-Use (TOU) & Dynamic Peak Hours
- **Off-Peak Discount Window (11:00 PM – 6:00 AM)**: 25% discount applied across all network stations to incentivize overnight grid balancing.
- **Normal Commute Window (6:00 AM – 5:00 PM and 9:00 PM – 11:00 PM)**: Standard base tariff applies.
- **Peak Surge Window (5:00 PM – 9:00 PM on weekdays)**: 15% demand surcharge applies at high-congestion urban plazas to encourage load shifting.

## 4. Payment Simulation & Invoicing
- **Transaction Records**: Completed sessions automatically generate a simulated transaction reference (e.g. `SIM-PAY-XXXX`) linked one-to-one with the session ID.
- **Itemized Receipts**: Drivers can view detailed breakdown invoices containing initial meter reading, closing meter reading, duration in minutes, power delivery curve, and billed amount.

