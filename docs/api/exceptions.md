# Exceptions

Every exception almapy raises descends from `AlmapyError`, so a single
`except AlmapyError` catches anything originating in the library.

See [Errors](../guide/errors.md) for how Alma's numeric codes map onto these
classes and which ones you should expect to catch in practice.

::: almapy.exceptions
    options:
      show_root_heading: false
      members_order: source
