class IKRShipmentStatuses:
    COMING = 1
    ARRIVED = 2
    LATE = 3
    LAB = 4
    AGRO_MONITORING = 5
    APPROVED = 6
    DEPORTED = 7
    DESTROYED = 8
    READY_FOR_AKD = 9
    # REJECTED_BY_LAB = 10  #because of_documentation

    CHOICES = (
        (COMING, 'Приходящий'),
        (ARRIVED, 'Прибывший'),
        (LATE, 'Срок истек'),
        (LAB, 'Лаборатория'),
        (AGRO_MONITORING, 'Агро мониторинг'),
        (APPROVED, 'Одобренный'),
        (DEPORTED, 'Отказано'),
        (DESTROYED, 'Уничтожение'),
        (READY_FOR_AKD, 'Готов к АКД')
    )

    choices_for_inspector = {
        LAB: 'Лаборатория',
        DEPORTED: 'Отказано',
        DESTROYED: 'Уничтожение',
        ARRIVED: 'ARRIVED'
    }

    final_statuses = {
        APPROVED: 'Одобренный',
        DEPORTED: 'Отказано',
        DESTROYED: 'Уничтожение'
    }

    allowed_statuses_for_akd = {
        READY_FOR_AKD: 'Готов к АКД',
        ARRIVED: 'Прибывший'
    }

    editable_shipment_statuses = (COMING, LATE, ARRIVED, LAB)


class UserRoles:
    ROADWAY = 1
    AIRWAY = 2
    RAILWAY = 3
    POST = 4
    PORT = 5
    VED = 6
    LAB = 7
    CHOICES = ((ROADWAY, 'Avtomobil'),
               (AIRWAY, 'Havo yo`li'),
               (RAILWAY, 'Temir yo`li'),
               (RAILWAY, 'Pochta'),
               (PORT, 'Bandargoh'),
               (VED, 'ved'),
               (LAB, 'Lab'))


class UserStatuses:
    ACTIVE = 1
    FIRED = 2
    VACATION = 3
    SICK = 4
    INACTIVE = 5
    ONPROCESS = 6
    CHOICES = ((ACTIVE, 'АКТИВНЫЙ'),
               (FIRED, 'Уволенный'),
               (VACATION, 'ОТПУСК'),
               (SICK, 'БОЛЬНОЙ'),
               (INACTIVE, 'Неактивный'),
               (ONPROCESS, 'В ПРОЦЕССЕ'))


class TransPortTypes:
    railway = 1
    port = 2
    airway = 3
    roadway = 4
    container = 5
    luggage = 6
    post = 7
    unkown1 = 10

    choices = ((roadway, 'авто'),
               (airway, 'авиа'),
               (railway, 'Ж/Д'),
               (container, 'контейнер'),
               (luggage, 'ручная кладь'),
               (post, 'почта'),
               (port, 'морской'),
               (unkown1, '210'))
    names_ru = {
        railway: 'Ж/Д',
        port: 'морской',
        airway: 'авиа',
        roadway: 'авто',
        container: 'контейнер',
        luggage: 'ручная кладь',
        post: 'почта'
    }
    local_names = {
        railway: 'Temir yo\'li',
        port: 'Port',
        airway: 'Havo yo\'li',
        roadway: 'Avto',
        container: 'Konteyner',
        luggage: 'Qo\'l yuki',
        post: 'Pochta'
    }

    gtk_dictionary = {
        1: 'Ж/Д',
        2: 'морской',
        3: 'авиа',
        4: 'авто',
        5: 'контейнер',
        6: 'ручная кладь',
        7: 'почта',
        10: '210'
    }  # we use this dictionary when we send AKD to GTK via API
    dictionary_en = {
        1: 'railway',
        2: 'sea',
        3: 'air',
        4: 'auto',
        5: 'container',
        6: 'luggage',
        7: 'port',
        10: '210'
    }


class PointTypes:
    MAIN = 0
    ROADWAY = 1
    AIRWAY = 2
    RAILWAY = 3
    POST = 4
    PORT = 5
    VED = 6
    LAB = 7
    choices = ((MAIN, 'Main'),
               (ROADWAY, 'Avtomobil'),
               (AIRWAY, 'Havo yo`li'),
               (RAILWAY, 'Temir yo`li'),
               (POST, 'Pochta'),
               (PORT, 'Bandargoh'),
               (VED, 'ved'),
               (LAB, 'Lab'))


class PointStatuses:
    ACTIVE = True
    PASSIVE = False
    CHOICES = ((ACTIVE, 'Активный'), (PASSIVE, 'Пассивный'))


class Languages:
    UZBEK = 1
    ENGLISH = 2
    RUSSIAN = 3
    LANGUAGE_DICT = {
        'UZ': UZBEK,
        'EN': ENGLISH,
        'RU': RUSSIAN
    }
    dictionary = {
        'UZ': UZBEK,
        'EN': ENGLISH,
        'RU': RUSSIAN
    }
    language_code = {
        UZBEK: 'uz',
        RUSSIAN: 'ru',
        ENGLISH: 'en'
    }
    CHOICES = ((UZBEK, 'UZBEK'), (ENGLISH, 'ENGLISH'), (RUSSIAN, 'RUSSIAN'))


class CustomerType:
    INDIVIDUAL = 1
    LEGAL = 2
    CHOICES = ((INDIVIDUAL, 'Физическое лицо'), (LEGAL, 'Юридическое лицо'))
    dictionary = {
        1: 'Физическое лицо',
        2: 'Юридическое лицо'
    }


class HSCodeGTKColorStatus:
    GREEN = 1
    YELLOW = 2
    RED = 3
    CHOICES = ((GREEN, 'GREEN'), (YELLOW, 'YELLOW'), (RED, 'RED'))


class APIAction:
    ADDING = 1
    UPDATING = 2
    UNKNOWN = 3
    CHOICES = ((ADDING, 'Adding'), (UPDATING, 'Updating'), (UNKNOWN, 'NOT KNOWN'))


class WrongAKDErrorTypes:
    LOCAL_EXCEPTION = 1
    API_ERROR = 2
    ERROR_TYPES = ((LOCAL_EXCEPTION, 'Local exception'), (API_ERROR, 'API error'))


class BlankTypes:
    IKR = 1
    TBOTD = 2
    AKD = 3
    FSS = 4
    LocalFSS = 5
    Fumigation = 6
    CHOICES = ((FSS, 'FSS'), (LocalFSS, 'Local FSS'))


class SMSNotificationStatuses:
    WRONG_NUMBER = 0
    REQUESTED = 1
    TRANSMITTED = 2
    DELIVERED = 3
    NOT_DELIVERED = 4
    REJECTED = 5
    FAILED = 6
    EXPIRED = 7
    CHOICES = (
        (WRONG_NUMBER, 'Wong NUmber'),
        (REQUESTED, 'Requested'),
        (TRANSMITTED, 'Transmitted'),
        (DELIVERED, 'Delivered'),
        (NOT_DELIVERED, 'Not Delivered'),
        (REJECTED, 'Rejected'),
        (FAILED, 'Failed'),
        (EXPIRED, 'Expired'),
    )

    DICT = {
        'Requested': REQUESTED,
        'Transmitted': TRANSMITTED,
        'Delivered': DELIVERED,
        'NotDelivered': NOT_DELIVERED,
        'Rejected': REJECTED,
        'Failed': FAILED,
        'Expired': EXPIRED
    }


class SMSNotificationPurposes:
    IKR_SHIPMENT = 1
    AKD = 2
    EXPORT_FSS = 3
    IKR = 4
    OLD_AKD = 5
    LOCAL_FSS = 6
    LAB = 7
    PPP = 8
    CHOICES = (
        (IKR_SHIPMENT, 'IKR shipment'),
        (AKD, 'AKD'),
        (EXPORT_FSS, 'Export FSS'),
        (IKR, 'IKR'),
        (OLD_AKD, 'Old AKD'),
        (LOCAL_FSS, 'Local FSS'),
        (LAB, 'Lab'),
        (PPP, 'ЎСИМЛИКЛАРНИ ҲИМОЯ ҚИЛИШНИНГ КИМЁВИЙ ВА БИОЛОГИК ВОСИТАЛАРИ ҲАМДА МИНЕРАЛ ВА МИКРОБИОЛОГИК ЎҒИТЛАРНИ РЎЙХАТГА ОЛИНГАНЛИК ТЎҒРИСИДА ГУВОҲНОМА'),
    )


class ExpertiseType:
    ENTOMOLOGY = 1
    # PHYTOPATHOLOGY = 2
    GERBOLOG = 3
    BACTERIOLOGIST = 4
    HELMINTHOLOGIST = 5
    VIROLOGIST = 6
    MIKOLOG = 7
    CHOICES = (
        (ENTOMOLOGY, 'Энтомолог'),
        # (PHYTOPATHOLOGY, 'Фитопотолог'), # commented because it is not used anymore, so it causes problems when it is sent to experts
        (GERBOLOG, 'Герболог'),
        (BACTERIOLOGIST, 'Бактериолог'),
        (HELMINTHOLOGIST, 'Фитогельментолог'),
        (VIROLOGIST, 'Вирусолог'),
        (MIKOLOG, 'Миколог')
    )

    dictionary = {
        1: "Энтомолог",
        2: "Фитопотолог",
        3: "Герболог",
        4: "Бактериолог",
        5: "Гельминтолог",
        6: "Вирусолог",
        7: "Миколог"
    }


class IntegratedDataType:
    IKR = 1
    AKD_STATUS = 2
    AKD = 3
    EXPORT_FSS_STATUS = 4
    EXPORT_FSS = 5
    IKR_STATUS = 6
    IKR_RENEWAL = 7
    IKR_RENEWAL_STATUS = 8
    LOCAL_FSS_STATUS = 9
    LOCAL_FSS = 10
    CHOICES = (
        (IKR, 'Карантинное разрешение'),
        (AKD_STATUS, 'АКД Статус'),
        (AKD, 'АКД'),
        (EXPORT_FSS_STATUS, 'ФСС Статус'),
        (EXPORT_FSS, 'ФСС'),
        (IKR_STATUS, 'КР Статус'),
        (IKR_RENEWAL, 'КР(продление)'),
        (IKR_RENEWAL_STATUS, 'КР(продление) Статус'),
        (LOCAL_FSS_STATUS, 'Внутренние ФСС Статус'),
        (LOCAL_FSS, 'Внутренние ФСС'),
    )

    dictionary = {
        1: "Карантинное разрешение",
        2: "АКД Статус",
        3: "АКД",
        4: "ФСС Статус",
        5: "ФСС",
        6: "КР Статус",
        7: "КР (продление)",
        8: "КР (продление) Статус",
        9: "Внутренние ФСС Статус",
        10: "Внутренние ФСС"
    }


class ImpExpLocChoices:
    Export = 1
    Import = 2
    Local = 3
    CHOICES = (
        (Export, 'Экспорт'),
        (Import, 'Импорт'),
        (Local, 'Внутренний')
    )

    dictionary = {
        1: "Экспорт",
        2: "Импорт",
        3: "Внутренний"
    }


class ContentTypes:
    json = 1
    xml = 2
    choices = (
        (json, 'JSON'),
        (xml, 'XML')
    )


class DisinfestationType:
    FUMIGATION = 1
    WETPROCESSING = 2
    HEATTREATMENT = 3
    AEROSOLTREATMENT = 4
    CHOICES = (
        (FUMIGATION, 'Фумигация'),
        (WETPROCESSING, 'Влажная Обработка'),
        (HEATTREATMENT, 'Термическая обработка'),
        (AEROSOLTREATMENT, 'Аэрозольная обработка')
    )

    dictionary_ru = {
        1: "Фумигация",
        2: "Влажная Обработка",
        3: "Термическая обработка",
        4: "Аэрозольная обработка"
    }

    dictionary_en = {
        1: "Fumigation",
        2: "Wet Processing",
        3: "Heat treatment",
        4: "Aerosol Treatment"
    }


class BioIndicatorType:
    BARNPEST = 1
    TEST = 2
    CHOICES = (
        (BARNPEST, 'Амбарные вредитель'),
        (TEST, 'Test'),
    )

    dictionary_ru = {
        1: "Амбарные вредитель",
        2: "TEST",
    }

    dictionary_en = {
        1: "Barn Pest",
        2: "TEST",
    }


class OrganizationType:
    BUDGET = 1
    OTHERS = 2
    CHOICES = (
        (BUDGET, 'Бюджет'),
        (OTHERS, 'Другие')
    )

    dictionary_en = {
        1: "Бюджет",
        2: "Другие"
    }

    dictionary_ru = {
        1: "Budget",
        2: "Others"
    }


class ApplicationStatuses:
    ONE_ZERO_ZERO = 1
    ZERO_ZERO_SEVEN = 2
    ONE_ZERO_SEVEN = 3
    ONE_ZERO_ONE = 4
    ZERO_ONE_ZERO = 5
    ONE_ONE_THREE = 6
    ONE_ZERO_TWO = 7
    ZERO_ONE_NINE = 8
    ONE_ZERO_SIX = 9
    ONE_ZERO_FIVE = 10
    THREE_ZERO_FIVE = 11
    ZERO_ZERO_TWO = 12
    CHOICES = (
        (ONE_ZERO_ZERO, 'Прием'),
        (ZERO_ZERO_SEVEN, 'Уведомление об исправлении при приеме'),
        (ONE_ZERO_SEVEN, 'Прием исправлений'),
        (ONE_ZERO_ONE, 'Распределение на рассмотрение'),
        (ZERO_ONE_ZERO, 'Уведомление об исправлении при рассмотрение'),
        (ONE_ONE_THREE, 'Рассмотрение исправленного заявления на внесение изменений'),
        (ONE_ZERO_TWO, 'Рассмотрение документов'),
        (ZERO_ONE_NINE, 'Уведомление об отказе в одобрении'),
        (ONE_ZERO_SIX, 'Одобрение'),
        (ONE_ZERO_FIVE, 'Распределение на ЛАБ'),
        (THREE_ZERO_FIVE, 'Получили результаты лабораторных исследований'),
        (ZERO_ZERO_TWO, 'заявлению на получения')
    )

    dictionary = {'100': 1,
                  '007': 2,
                  '107': 3,
                  '101': 4,
                  '010': 5,
                  '113': 6,
                  '102': 7,
                  '019': 8,
                  '106': 9,
                  '105': 10,
                  '305': 11,
                  '002': 12
                  }

    gtk_status_dictionary = {1: '100',
                             2: '007',
                             3: '107',
                             4: '101',
                             5: '010',
                             6: '113',
                             7: '102',
                             8: '019',
                             9: '106',
                             10: '105',
                             11: '305',
                             12: '002'
                             }


class ApplicationTypes:
    IKR = 1
    IKR_RENEWAL = 2
    AKD = 3
    EXPORT_FSS = 4
    LOCAL_FSS = 5
    CHOICES = (
        (IKR, 'КР'),
        (IKR_RENEWAL, 'КР (продление)'),
        (AKD, 'АКД'),
        (EXPORT_FSS, 'ФСС'),
        (LOCAL_FSS, 'Внутренние ФСС')
    )

    dictionary = {
        1: "КР",
        2: "КР (продление)",
        3: "АКД",
        4: "ФСС",
        5: "Внутренние ФСС",
    }


class TemporarilyStoppedShipmentStatuses:
    ON_PROCESS = 1
    APPROVED = 2
    REJECTED = 3
    CHOICES = (
        (ON_PROCESS, 'В процессе'),
        (APPROVED, 'Одобренный'),
        (REJECTED, 'Отклоненный')
    )