# VoltFlow EV Charging Network — Connector Standards & Technical Guide

## 1. Supported Hardware Connector Types
- **CCS2 (Combined Charging System Type 2)**:
  - European, Indian, and Global standard for high-power DC fast charging.
  - Combines AC Type 2 pins with two heavy DC power pins below.
  - Power Output: Up to 350 kW DC.
  - Compatible with most modern EVs (Tesla with CCS adapter, Hyundai, Kia, BMW, Audi, Porsche, Tata, MG).
- **Type 2 (Mennekes / IEC 62196)**:
  - AC single-phase and three-phase charging connector.
  - Power Output: 7.4 kW (single phase, 32A) to 22 kW (three phase, 32A).
  - Used for daily overnight charging and destination parking.
- **CHAdeMO**:
  - Japanese fast-charging standard developed by CHAdeMO Association.
  - Power Output: Up to 62.5 kW DC.
  - Used predominantly by Nissan Leaf, Mitsubishi Outlander PHEV, and select Japanese imports.

## 2. Battery Charging Chemistry: Constant Current / Constant Voltage (CC-CV)
- **Fast Charging Range (10% to 80% SOC)**:
  - Operated in **Constant Current (CC)** mode.
  - The vehicle Battery Management System (BMS) accepts maximum power from the dispenser.
- **Tapering Phase (80% to 100% SOC)**:
  - Operated in **Constant Voltage (CV)** mode.
  - Power decreases progressively to prevent lithium plating and thermal stress on battery cells.
  - Charging from 80% to 100% often takes as long as charging from 20% to 80%. Drivers are advised to stop at 80% during road trips.

## 3. Communication Protocols
- Network dispensers support **OCPP 1.6J** and **OCPP 2.0.1** (Open Charge Point Protocol) via secure WebSockets for telemetry transmission, remote start/stop, and tariff profile synchronization.

