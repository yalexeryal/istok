"""
Сервис для генерации отчеств на разных языках Евразии.
"""


def generate_patronymic(father_first_name: str, child_gender: str, culture: str = "ru") -> str | None:
    """
    Генерирует отчество на основе имени отца, пола ребенка и культуры.

    Поддерживаемые культуры:
    - ru: русский
    - uk: украинский
    - be: белорусский
    - pl: польский
    - kk: казахский
    - ky: кыргызский
    - uz: узбекский
    - az: азербайджанский
    - sv: шведский
    - no: норвежский
    - da: датский
    - is: исландский
    """
    if not father_first_name:
        return None

    name = father_first_name.strip()

    # Маршрутизация по культуре
    if culture in ["ru", "uk", "be"]:  # Славянские
        return _generate_slavic_patronymic(name, child_gender, culture)
    elif culture == "pl":  # Польский
        return _generate_polish_patronymic(name, child_gender)
    elif culture in ["kk", "ky", "uz"]:  # Тюркские
        return _generate_turkic_patronymic(name, child_gender, culture)
    elif culture == "az":  # Азербайджанский
        return _generate_azerbaijani_patronymic(name, child_gender)
    elif culture in ["sv", "no", "da"]:  # Скандинавские
        return _generate_scandinavian_patronymic(name, child_gender, culture)
    elif culture == "is":  # Исландский
        return _generate_icelandic_patronymic(name, child_gender)
    else:
        # По умолчанию используем русскую логику
        return _generate_slavic_patronymic(name, child_gender, "ru")


def _generate_slavic_patronymic(name: str, gender: str, culture: str = "ru") -> str | None:
    """Генерация отчества для славянских языков."""
    name_lower = name.lower()
    last_letter = name_lower[-1]

    # Исключения для нестандартных склонений
    exceptions = {
        'никита': 'никит',
        'лука': 'лук',
        'илья': 'иль',
        'фома': 'фом',
        'лев': 'льв',
        'павел': 'павл',
        'пётр': 'петр',
    }

    base = exceptions.get(name_lower, name_lower)

    if base.endswith('ь'):
        base = base[:-1]

    if culture == "uk":  # Украинский
        if gender == 'male':
            if last_letter == 'й':
                result = base[:-1] + 'ійович' if base.endswith('й') else base + 'ович'
            elif last_letter in ['а', 'я']:
                result = base + 'ич'
            else:
                result = base + 'ович'
        else:  # female
            if last_letter == 'й':
                result = base[:-1] + 'ійвна' if base.endswith('й') else base + 'вна'
            elif last_letter in ['а', 'я']:
                result = base + 'инична'
            else:
                result = base + 'вна'
    else:  # Русский и белорусский
        if gender == 'male':
            if last_letter == 'й':
                result = base[:-1] + 'евич'
            elif last_letter in ['а', 'я']:
                result = base + 'ич'
            else:
                result = base + 'ович'
        else:  # female
            if last_letter == 'й':
                result = base[:-1] + 'евна'
            elif last_letter in ['а', 'я']:
                result = base + 'инична'
            else:
                result = base + 'овна'

    return result.capitalize()


def _generate_polish_patronymic(name: str, gender: str) -> str | None:
    """Генерация отчества для польского языка."""
    name_lower = name.lower()

    # Польские отчества: -owicz/-ówna, -ewicz/-ówna
    if name_lower.endswith('a'):
        base = name_lower[:-1]
    else:
        base = name_lower

    if gender == 'male':
        if base.endswith('e'):
            result = base + 'wicz'
        else:
            result = base + 'owicz'
    else:  # female
        if base.endswith('e'):
            result = base + 'wna'
        else:
            result = base + 'ówna'

    return result.capitalize()


def _generate_turkic_patronymic(name: str, gender: str, culture: str) -> str | None:
    """Генерация отчества для тюркских языков."""
    name_lower = name.lower()

    if culture == "kk":  # Казахский: -улы (сын), -кызы (дочь)
        if gender == 'male':
            result = name_lower + 'ұлы'
        else:
            result = name_lower + 'қызы'
    elif culture == "ky":  # Кыргызский: -уулу (сын), -кызы (дочь)
        if gender == 'male':
            result = name_lower + 'уулу'
        else:
            result = name_lower + 'кызы'
    else:  # Узбекский и другие: -o'g'li (сын), -qizi (дочь)
        if gender == 'male':
            result = name_lower + " o'g'li"
        else:
            result = name_lower + ' qizi'

    return result.capitalize()


def _generate_azerbaijani_patronymic(name: str, gender: str) -> str | None:
    """Генерация отчества для азербайджанского языка."""
    name_lower = name.lower()

    # Азербайджанский: -oğlu (сын), -qızı (дочь)
    if gender == 'male':
        result = name_lower + 'oğlu'
    else:
        result = name_lower + 'qızı'

    return result.capitalize()


def _generate_scandinavian_patronymic(name: str, gender: str, culture: str) -> str | None:
    """Генерация отчества для скандинавских языков."""
    name_lower = name.lower()

    if culture == "sv":  # Шведский: -son (сын), -dotter (дочь)
        if gender == 'male':
            result = name_lower + 'son'
        else:
            result = name_lower + 'dotter'
    elif culture in ["no", "da"]:  # Норвежский/датский: -sen (сын), -datter (дочь)
        if gender == 'male':
            result = name_lower + 'sen'
        else:
            result = name_lower + 'datter'
    else:
        return None

    return result.capitalize()


def _generate_icelandic_patronymic(name: str, gender: str) -> str | None:
    """Генерация отчества для исландского языка."""
    name_lower = name.lower()

    # Исландский: -son (сын), -dóttir (дочь)
    if gender == 'male':
        result = name_lower + 'son'
    else:
        result = name_lower + 'dóttir'

    return result.capitalize()