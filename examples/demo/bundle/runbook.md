# Kafka Checkout Consumer Lag Runbook

Incident: `ifg-dc5e156218`

## First Checks

Check consumer lag by group, inspect failed offsets, compare schema registry versions, and quarantine poison messages before restarting the consumer.

## Expected Evidence

- consumer_lag_spike: `sum(kafka_consumer_lag{group="payments-consumer"})` -> Lag rises from 180 to more than 52000 offsets after 10:08 UTC.
- deserialize_errors: `service="payments-consumer" "SchemaRegistryDecodeError"` -> Decode errors repeat for checkout.payment_authorized.v7.
- stable_broker_cpu: `avg(kafka_broker_cpu{cluster="orders-eu"})` -> Broker CPU remains below 42 percent, reducing broker saturation likelihood.

## Known Red Herrings

- A checkout-api deploy completed four minutes before the page fired. Reason to verify: The deploy only changed frontend validation and request volume stayed flat.
- A Kafka broker leader election occurred earlier in the hour. Reason to verify: Partition ISR recovered before the lag spike and broker health is normal.
