class PPPProtocolStatuses:
    SAVED = 1
    PENDING = 2
    REJECTED = 3
    APPROVED = 4
    CHOICES = (
        (SAVED, 'Saved'),
        (PENDING, 'Pending'),
        (REJECTED, 'Rejected'),
        (APPROVED, 'Approved')
    )