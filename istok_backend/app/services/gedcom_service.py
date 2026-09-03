from uuid import uuid4, UUID
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from gedcom.parser import Parser

from app.models.person import Person, GenderEnum
from app.models.tree_person import TreePerson
from app.models.relation import Relation, RelationTypeEnum
from app.services.access_service import check_tree_access


async def import_gedcom_to_tree(
        db: AsyncSession,
        tree_id: UUID,
        user_id: UUID,
        gedcom_file_path: str
) -> dict:
    """Импортирует данные из GEDCOM файла в указанное дерево."""

    # 1. Проверка прав доступа
    if not await check_tree_access(db, tree_id, user_id):
        raise ValueError("У вас нет доступа к этому дереву")

    # 2. Инициализация парсера
    gedcom_parser = Parser()
    gedcom_parser.parse_file(gedcom_file_path)

    stats = {"persons_created": 0, "relations_created": 0}
    id_mapping = {}  # Словарь для сопоставления GEDCOM ID (@I1@) с нашими UUID

    elements = gedcom_parser.get_element_list()

    # 3. Парсинг персон (INDI)
    for element in elements:
        if element.get_tag() == 'INDI':
            gedcom_id = element.get_pointer()  # Например, "@I1@"

            # Извлекаем имя (возвращает кортеж: (имя, фамилия))
            name = element.get_name()
            if isinstance(name, tuple) and len(name) >= 2:
                first_name = name[0] or "Неизвестно"
                last_name = name[1].strip("/") if name[1] else "Неизвестно"
            else:
                first_name = "Неизвестно"
                last_name = "Неизвестно"

            # Извлекаем дату и место рождения
            birth_data = element.get_birth_data()
            birth_date_str = birth_data[0] if birth_data and len(birth_data) > 0 and birth_data[0] else None
            birth_place = birth_data[1] if birth_data and len(birth_data) > 1 and birth_data[1] else None

            # Преобразуем дату (простой парсинг)
            birth_date = None
            if birth_date_str:
                try:
                    birth_date = datetime.strptime(birth_date_str, "%d %b %Y").date()
                except ValueError:
                    try:
                        birth_date = datetime.strptime(birth_date_str, "%Y").date()
                    except ValueError:
                        pass

            # Определяем пол
            gender_str = element.get_gender().lower() if element.get_gender() else 'u'
            gender = GenderEnum.MALE if gender_str == 'm' else (
                GenderEnum.FEMALE if gender_str == 'f' else GenderEnum.UNKNOWN)

            # Создаем персону в БД
            person_id = uuid4()
            id_mapping[gedcom_id] = person_id

            new_person = Person(
                id=person_id,
                first_name=first_name,
                last_name=last_name,
                birth_date=birth_date,
                birth_place=birth_place,
                gender=gender,
                created_by=user_id  # <-- ИСПРАВЛЕНО: добавлено обязательное поле
            )
            db.add(new_person)

            # Привязываем персону к дереву
            db.add(TreePerson(tree_id=tree_id, person_id=person_id, added_by=user_id))
            stats["persons_created"] += 1

    await db.flush()  # Получаем реальные ID перед созданием связей

    # 4. Парсинг семей (FAM) для создания связей
    for element in elements:
        if element.get_tag() == 'FAM':
            husband_ptr = None
            wife_ptr = None
            children_ptrs = []

            # Проходим по дочерним элементам семьи
            for child in element.get_child_elements():
                tag = child.get_tag()
                value = child.get_value()
                if tag == 'HUSB':
                    husband_ptr = value
                elif tag == 'WIFE':
                    wife_ptr = value
                elif tag == 'CHIL':
                    children_ptrs.append(value)

            # Связь "Супруги"
            if husband_ptr and wife_ptr:
                husband_id = id_mapping.get(husband_ptr)
                wife_id = id_mapping.get(wife_ptr)

                if husband_id and wife_id:
                    # Проверяем, не создана ли уже такая связь
                    exists = await db.execute(
                        select(Relation).where(
                            ((Relation.person_1_id == husband_id) & (Relation.person_2_id == wife_id)) |
                            ((Relation.person_1_id == wife_id) & (Relation.person_2_id == husband_id))
                        )
                    )
                    if not exists.scalar_one_or_none():
                        db.add(Relation(
                            person_1_id=husband_id,  # <-- ИСПРАВЛЕНО: person_1_id
                            person_2_id=wife_id,  # <-- ИСПРАВЛЕНО: person_2_id
                            type=RelationTypeEnum.SPOUSE,  # <-- ИСПРАВЛЕНО: type вместо relation_type
                            created_by=user_id  # <-- ИСПРАВЛЕНО: добавлено обязательное поле
                        ))
                        stats["relations_created"] += 1

            # Связь "Родитель-Ребенок"
            for child_ptr in children_ptrs:
                child_id = id_mapping.get(child_ptr)
                if not child_id:
                    continue

                # Если есть отец
                if husband_ptr:
                    father_id = id_mapping.get(husband_ptr)
                    if father_id:
                        db.add(Relation(
                            person_1_id=father_id,  # <-- ИСПРАВЛЕНО
                            person_2_id=child_id,  # <-- ИСПРАВЛЕНО
                            type=RelationTypeEnum.PARENT_CHILD,  # <-- ИСПРАВЛЕНО
                            created_by=user_id  # <-- ИСПРАВЛЕНО
                        ))
                        stats["relations_created"] += 1

                # Если есть мать
                if wife_ptr:
                    mother_id = id_mapping.get(wife_ptr)
                    if mother_id:
                        db.add(Relation(
                            person_1_id=mother_id,  # <-- ИСПРАВЛЕНО
                            person_2_id=child_id,  # <-- ИСПРАВЛЕНО
                            type=RelationTypeEnum.PARENT_CHILD,  # <-- ИСПРАВЛЕНО
                            created_by=user_id  # <-- ИСПРАВЛЕНО
                        ))
                        stats["relations_created"] += 1

    await db.commit()
    return stats