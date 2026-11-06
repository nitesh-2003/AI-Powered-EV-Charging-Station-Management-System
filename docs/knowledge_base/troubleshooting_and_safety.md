# VoltFlow EV Charging Network — Troubleshooting & Safety Guide

## 1. Cable Lock Release Failures
- **Issue**: Charging cable remains locked in the vehicle port after session termination.
- **Resolution Steps**:
  1. Ensure the session has been terminated in the mobile app or web portal.
  2. Unlock vehicle doors with your key fob twice (many EV models automatically release the port lock solenoid when doors are unlocked).
  3. Look for the manual cable release pull-cord inside the vehicle trunk or under the hood near the charging flap.
  4. Never yank or forcefully pry the connector, which can damage pins and trigger electrical arc faults.

## 2. Session Activation Failures
- **Issue**: Dispenser fails to deliver power after initiating session.
- **Causes & Diagnostics**:
  - **Handshake Protocol Timeout**: Ensure the connector is fully inserted until you hear an audible click before tapping 'Start Session'.
  - **Incompatible Connector / Power State**: Check if dispenser status is `FAULTED` in the station directory.
  - **Vehicle Pre-conditioning**: Some EVs delay charge initiation while warming or cooling battery packs.

## 3. Wet Weather Charging Guidelines
- **IP67 Ingress Protection**: All network dispensers and cable couplers meet IP67 weather sealing and are completely safe to use during rain, snow, or fog.
- **Precaution**: Never attempt charging if the connector nozzle is visibly submerged in standing water or if ice has formed inside the electrical pin cavities.

## 4. Refund & Billing Inquiries
- **Billing Dispute Window**: Drivers may submit billing adjustment claims within 14 days of session completion.
- **Automatic Reimbursement**: Sessions disrupted due to grid power brownouts or hardware faults automatically trigger a full tariff refund back to the customer's account balance.

