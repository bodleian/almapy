# Configuration

Reached as `client.config`, a container exposing five sub-namespaces over Alma's
`/conf` endpoints.

`client.config.code_tables` is the one to reach for when another method wants a
code you do not have to hand:

```python
table = await client.config.code_tables.get_code_table("POLineCancellationReasons")
valid = [r.code for r in table.row if r.enabled == "true"]
```

## `client.config`

::: almapy._config.AlmaClientConfigNS

## `client.config.sets`

::: almapy._config.AlmaClientConfigSetsNS

## `client.config.libraries`

::: almapy._config.AlmaClientConfigLibrariesNS

## `client.config.letters`

::: almapy._config.AlmaClientConfigLettersNS

## `client.config.jobs`

::: almapy._config.AlmaClientConfigJobsNS

## `client.config.code_tables`

::: almapy._config.AlmaClientConfigCodeTablesNS
