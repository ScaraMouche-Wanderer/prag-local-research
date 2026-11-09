# PRAG demonstration component

This is an original synthetic document for a public software demonstration.

## Component definition

The demo component is called BeaconDesk. BeaconDesk groups simulated device observations into an operator-readable event list. It runs only inside this fictional example.

## Processing rule

Each observation has a device label and an event category. Repeated observations with the same device label and category are grouped into one event. A category change creates a separate event.

## Example command option

The fictional BeaconDesk CLI documents this option.

--group-events: Group observations that share a device label and event category.

## Limits

This document specifies no radio hardware, security guarantee, measured latency, temperature range, battery lifetime, or deployment result. Those facts are unknown.

## Example

Two observations labeled device-alpha with category status are grouped together. An observation labeled device-alpha with category warning appears as a separate event.
