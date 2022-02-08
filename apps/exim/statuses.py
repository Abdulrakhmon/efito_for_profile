class SynchronisationStatus:
    not_synchronised = 1
    synchronisation_pending = 2
    synchronised = 3
    synchronisation_failed = 4

    choices = (
        (not_synchronised, 'not_synchronised'),
        (synchronisation_pending, 'synchronisation_pending'),
        (synchronised, 'synchronised'),
        (synchronisation_failed, 'synchronisation_failed')
    )
