# Advanced

The rate-limiting internals. You do not need these to use the library –
`AlmaClient` builds and drives them for you – but they are documented because
the behaviour they implement is worth understanding when tuning `rate_limit`, or
when reading the `almapy.throttle` log output.

See [Rate limiting](../guide/rate-limiting.md) for the narrative version.

## Token bucket

::: almapy._throttle.TokenBucket

## Adaptive controller

::: almapy._throttle.AdaptiveController
