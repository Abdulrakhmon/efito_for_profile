class InvoiceServices:
    IKR = 1
    TBOTD = 2
    FUMIGATION = 3
    FSS = 4
    LocalFSS = 5
    LAB = 6
    RegistrationCertificateOfPPP = 7  # PPP -> plant protection products
    CHOICES = (
        (IKR, 'Карантинное разрешение'),
        (TBOTD, 'ТБД'),
        (FUMIGATION, 'Фумигация'),
        (FSS, 'ФСС'),
        (LocalFSS, 'Вн_ФСС'),
        (LAB, 'Лаборатория '),
        (RegistrationCertificateOfPPP, 'Оплата за регистрационное удостоверение ')
    )

    dictionary_ru = {
        1: "Карантинное разрешение",
        2: "Акт карантинного досмотра",
        3: "Акт обеззараживания (фумигация)",
        4: "Фитосанитарный сертификат",
        5: "Внутренний фитосанитарный сертификат",
        6: "Лаборатория",
        7: "Оплата за регистрационное удостоверение"
    }

    dictionary = {
        1: "КР",
        2: "ТБД",
        3: "Фумигация",
        4: "ФСС",
        5: "ИЧКИ ФСС",
        6: "Лаборатория",
        7: "Рўйхатга олиш гувохномаси учун тўлов"
    }

    munis_services = [IKR, TBOTD, FUMIGATION, FSS, LocalFSS, LAB, RegistrationCertificateOfPPP]


class MunisIntegrationResultCodes:
    successful = 0
    contract_number_not_found = 1
    details_are_incorrect = 2
    duplicate_blank_number = 3
    invalid_payment_amount = 4
    invalid_date = 5
    invalid_payment_type = 6
    payment_amount_exceeds_required_payment_amount = 7
    payment_amount_fully_refunded = 8
    rule_violation = 9

    definition_dict = {
        contract_number_not_found: 'Номер договора оферты не найден для данного типа услуги',
        duplicate_blank_number: 'Платеж с указанным уникальным номером уже существует',
        details_are_incorrect: 'Неизвестная информация получена',
        payment_amount_exceeds_required_payment_amount: 'Сумма платежа превышает требуемую сумму платежа',
        rule_violation: 'Нарушено правило взаимодействия',
    }


class InvoicePaymentStatuses:
    confirmed = 0
    not_confirmed = 1
    rejected = 2
    cancelled = 3
    choices = (
        (confirmed, 'Success'),
        (not_confirmed, 'Утверждено'),
        (rejected, 'Отклонено'),
        (cancelled, 'Отменено')
    )
