from uuid import uuid4, UUID
from datetime import datetime, date
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from gedcom.parser import Parser

from app.models.person import Person, GenderEnum
from app.models.tree_person import TreePerson
from app.models.relation import Relation, RelationTypeEnum
from app.services.access_service import check_tree_access


def parse_gedcom_date(date_str: str) -> Optional[date]:
    """Парсит дату из GEDCOM, игнорируя префиксы вроде ABT, CAL, EST."""
    if not date_str:
        return None

    clean_date = date_str.upper().strip()
    # Убираем стандартные GEDCOM-префиксы
    for prefix in ["ABT ", "CAL ", "EST ", "BEF ", "AFT ", "FROM ", "TO "]:
        if clean_date.startswith(prefix):
            clean_date = clean_date[len(prefix):].strip()

    if not clean_date:
        return None

    formats = [
        "%d %b %Y",  # 15 JUL 2024
        "%d %B %Y",  # 15 July 2024
        "%Y",  # 1965
        "%b %Y",  # JUL 2024
        "%d %m %Y",  # 15 07 2024
        "%d.%m.%Y",  # 15.07.2024
    ]

    for fmt in formats:
        try:
            return datetime.strptime(clean_date, fmt).date()
        except ValueError:
            continue

    return None


async def import_gedcom_to_tree(
        db: AsyncSession,
        tree_id: UUID,
        user_id: UUID,
        gedcom_file_path: str
) -> dict:
    """Импортирует данные из GEDCOM файла в указанное дерево."""

    if not await check_tree_access(db, tree_id, user_id):
        raise ValueError("У вас нет доступа к этому дереву")

    gedcom_parser = Parser()
    gedcom_parser.parse_file(gedcom_file_path)

    stats = {"persons_created": 0, "relations_created": 0}
    id_mapping = {}

    elements = gedcom_parser.get_element_list()

    # 1. Парсинг персон (INDI)
    for element in elements:
        if element.get_tag() == 'INDI':
            gedcom_id = element.get_pointer()

            first_name = "Неизвестно"
            last_name = "Неизвестно"
            maiden_name = None

            givn_val = None
            surn_val = None
            marnm_val = None

            # Сначала пытаемся прочитать из специфичных тегов
            for child in element.get_child_elements():
                tag = child.get_tag()
                val = child.get_value().strip().strip("/") if child.get_value() else ""
                if not val or val.lower() in ["неизвестно", "unknown", ""]:
                    val = None

                if tag == 'GIVN':
                    givn_val = val
                elif tag == 'SURN':
                    surn_val = val
                elif tag == '_MARNM':
                    marnm_val = val

            # Логика распределения фамилий
            if givn_val:
                first_name = givn_val

            if marnm_val:
                # Если есть фамилия в браке, она становится актуальной
                last_name = marnm_val
                if surn_val:
                    maiden_name = surn_val  # А SURN становится девичьей
            else:
                # Если фамилии в браке нет, SURN считается актуальной
                if surn_val:
                    last_name = surn_val
                else:
                    # Fallback к стандартному тегу NAME (если подтегов нет)
                    parsed = element.get_name()
                    if isinstance(parsed, tuple) and len(parsed) >= 2:
                        if not givn_val and parsed[0]:
                            first_name = parsed[0].strip()
                        if not surn_val and parsed[1]:
                            last_name = parsed[1].strip("/")

            # Дата и место рождения
            birth_data = element.get_birth_data()
            birth_date_str = birth_data[0] if birth_data and len(birth_data) > 0 else None
            birth_place = birth_data[1] if birth_data and len(birth_data) > 1 else None

            birth_date = parse_gedcom_date(birth_date_str)

            # Пол
            gender_str = element.get_gender().lower() if element.get_gender() else 'u'
            gender = GenderEnum.MALE if gender_str == 'm' else (
                GenderEnum.FEMALE if gender_str == 'f' else GenderEnum.UNKNOWN)

            person_id = uuid4()
            id_mapping[gedcom_id] = person_id

            new_person = Person(
                id=person_id,
                first_name=first_name,
                last_name=last_name,
                maiden_name=maiden_name,
                birth_date=birth_date,
                birth_place=birth_place,
                gender=gender,
                created_by=user_id
            )
            db.add(new_person)
            db.add(TreePerson(tree_id=tree_id, person_id=person_id, added_by=user_id))
            stats["persons_created"] += 1

    await db.flush()

    # 2. Парсинг семей (FAM)
    for element in elements:
        if element.get_tag() == 'FAM':
            husband_ptr = None
            wife_ptr = None
            children_ptrs = []
            marriage_date_str = None

            for child in element.get_child_elements():
                tag = child.get_tag()
                value = child.get_value()
                if tag == 'HUSB':
                    husband_ptr = value
                elif tag == 'WIFE':
                    wife_ptr = value
                elif tag == 'CHIL':
                    children_ptrs.append(value)
                elif tag == 'MARR':
                    for sub_child in child.get_child_elements():
                        if sub_child.get_tag() == 'DATE':
                            marriage_date_str = sub_child.get_value()
                            break

            marriage_date = parse_gedcom_date(marriage_date_str)

            # Связь "Супруги"
            if husband_ptr and wife_ptr:
                husband_id = id_mapping.get(husband_ptr)
                wife_id = id_mapping.get(wife_ptr)

                if husband_id and wife_id:
                    exists = await db.execute(
                        select(Relation).where(
                            ((Relation.person_1_id == husband_id) & (Relation.person_2_id == wife_id)) |
                            ((Relation.person_1_id == wife_id) & (Relation.person_2_id == husband_id))
                        )
                    )
                    if not exists.scalar_one_or_none():
                        db.add(Relation(
                            person_1_id=husband_id,
                            person_2_id=wife_id,
                            type=RelationTypeEnum.SPOUSE,
                            event_date=marriage_date,
                            created_by=user_id
                        ))
                        stats["relations_created"] += 1

            # Связь "Родитель-Ребенок"
            for child_ptr in children_ptrs:
                child_id = id_mapping.get(child_ptr)
                if not child_id:
                    continue

                if husband_ptr:
                    father_id = id_mapping.get(husband_ptr)
                    if father_id:
                        db.add(Relation(
                            person_1_id=father_id,
                            person_2_id=child_id,
                            type=RelationTypeEnum.PARENT_CHILD,
                            created_by=user_id
                        ))
                        stats["relations_created"] += 1

                if wife_ptr:
                    mother_id = id_mapping.get(wife_ptr)
                    if mother_id:
                        db.add(Relation(
                            person_1_id=mother_id,
                            person_2_id=child_id,
                            type=RelationTypeEnum.PARENT_CHILD,
                            created_by=user_id
                        ))
                        stats["relations_created"] += 1

    await db.commit()
    return stats