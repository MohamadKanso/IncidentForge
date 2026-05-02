# RCA Candidate Report

The incident is most likely caused by A backward-incompatible schema change introduced a poison message that repeatedly fails deserialization and stalls the payments consumer group.

Evidence:
- consumer_lag_spike: Lag rises from 180 to more than 52000 offsets after 10:08 UTC.
- deserialize_errors: Decode errors repeat for checkout.payment_authorized.v7.
- The affected service is payments-consumer.

Recommended response:
- skip poison message, rollback schema, add dead letter queue.
- Add a regression test and alert so this class of incident is caught earlier.
