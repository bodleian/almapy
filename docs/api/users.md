# Users

Reached as `client.users`, which carries the user-record methods themselves plus
three sub-namespaces for loans, fines and requests.

!!! note "User identifiers"

    Almost every method here takes a `user_id` together with a `user_id_type`
    that defaults to `all_unique`, meaning Alma matches the value against any of
    the user's unique identifiers — primary ID, barcode, institution ID and so
    on. That is convenient but ambiguous when the same string is in use as two
    different kinds of ID; pass an explicit type such as `BARCODE` when
    precision matters.

## `client.users`

::: almapy._users.AlmaClientUserNS

## `client.users.loans`

::: almapy._users.AlmaClientUserLoansNS

## `client.users.fines`

Also available as `client.users.fees` — Alma's own API calls these "fees", so
both spellings refer to the same object.

::: almapy._users.AlmaClientUserFinesNS

## `client.users.requests`

::: almapy._users.AlmaClientUserRequestsNS
