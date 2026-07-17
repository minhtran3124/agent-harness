Refactor how the notifications and billing subsystems both compute a user's monthly quota.
Update both services, their repositories, and the shared internal quota helper so they use one
consistent calculation. No API changes, no schema changes — purely internal.
