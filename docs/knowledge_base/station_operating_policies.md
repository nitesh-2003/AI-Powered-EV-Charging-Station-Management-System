# VoltFlow EV Charging Network — Operating Policies & Reservation Rules

## 1. Slot Reservation & Arrival Grace Period
- **Advance Booking Window**: EV drivers can reserve a charging dispenser up to 7 days in advance for time increments between 30 minutes and 4 hours.
- **Grace Period**: Drivers are granted a **15-minute grace period** after their scheduled reservation start time. If the vehicle is not plugged in and the session has not commenced within 15 minutes of the start time, the reservation is automatically marked as `NO_SHOW` and released to public queue.
- **Overlapping Reservations**: The system enforces strict database-level concurrency protection. No two drivers may reserve the same dispenser for overlapping time intervals.

## 2. Cancellation Policy & Penalty Tiers
- **Free Cancellation**: Drivers may cancel their reservation at zero cost if cancelled **more than 60 minutes** prior to the reservation start window.
- **Late Cancellation (Within 60 minutes)**: A nominal processing fee equivalent to **20% of estimated session tariff** or flat $3.00 is assessed to prevent slot hoarding during high-demand hours.
- **No-Show Penalty**: A no-show forfeiture fee of $5.00 applies if the driver fails to arrive within the 15-minute grace window.

## 3. Anti-Idling Fee Policy
- **Idle Grace Period**: Once an EV reaches 100% State of Charge (SOC) or power delivery ceases, the driver has a **15-minute complimentary window** to unplug and relocate their vehicle.
- **Idle Fee Rate**: If the vehicle remains parked at an occupied dispenser after the 15-minute grace period has expired, an **Idling Fee of $0.50 per minute** ($30.00/hour) is billed to ensure fair hardware availability for waiting drivers.
- **Waiver**: Idling fees are waived during overnight off-peak hours (11:00 PM to 6:00 AM) at selected suburban plazas.

## 4. Operational Safety Standards
- **Emergency Shutdown**: In the event of smoke, electrical arcing, severe water ingress, or cable damage, drivers must press the red mushroom **Emergency Stop (E-Stop)** button located on each dispenser cabinet.
- **Automatic Thermal Shutdown**: Liquid-cooled cables automatically throttle power if internal temperatures reach 75°C and execute an emergency power disconnect if temperatures exceed 80°C.

