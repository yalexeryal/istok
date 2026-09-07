# -*- coding: utf-8 -*-
import io
import os
import traceback
from uuid import UUID
from datetime import datetime, date
from typing import List, Dict, Optional
from collections import defaultdict

from fpdf import FPDF
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import matplotlib

matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import numpy as np

from app.models.tree import Tree
from app.models.person import Person, GenderEnum
from app.models.tree_person import TreePerson
from app.models.relation import Relation, RelationTypeEnum
from app.models.life_event import LifeEvent
from app.services.access_service import check_tree_access

FONT_PATH = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
FONT_PATH_BOLD = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
LOGO_PATH = "/app/app/assets/logo.png"


def _calculate_age(birth_date: Optional[date], death_date: Optional[date]) -> Optional[int]:
    if not birth_date:
        return None
    end_date = death_date or date.today()
    age = end_date.year - birth_date.year
    if (end_date.month, end_date.day) < (birth_date.month, birth_date.day):
        age -= 1
    return age


def _get_age_suffix(age: int) -> str:
    if 11 <= age % 100 <= 14:
        return " лет"
    last_digit = age % 10
    if last_digit == 1:
        return " год"
    elif 2 <= last_digit <= 4:
        return " года"
    else:
        return " лет"


def _format_full_name(person: Person) -> str:
    last_name = str(person.last_name) if person.last_name else "Неизвестно"
    first_name = str(person.first_name) if person.first_name else "Неизвестно"
    middle_name = str(person.middle_name) if person.middle_name else ""

    maiden_name = None
    if hasattr(person, 'maiden_name') and person.maiden_name:
        maiden_name = str(person.maiden_name)

    if maiden_name and maiden_name.lower() != "неизвестно":
        last_name_display = f"{last_name} ({maiden_name})"
    else:
        last_name_display = last_name

    full_name = f"{last_name_display} {first_name}"
    if middle_name:
        full_name += f" {middle_name}"
    return full_name.strip()


def _get_parents(person_id: UUID, relations: List[Relation], persons: List[Person]) -> List[Person]:
    person_dict = {p.id: p for p in persons}
    return [
        person_dict[rel.person_1_id]
        for rel in relations
        if rel.type == RelationTypeEnum.PARENT_CHILD and rel.person_2_id == person_id and rel.person_1_id in person_dict
    ]


def _get_children(person_id: UUID, relations: List[Relation], persons: List[Person]) -> List[Person]:
    person_dict = {p.id: p for p in persons}
    return [
        person_dict[rel.person_2_id]
        for rel in relations
        if rel.type == RelationTypeEnum.PARENT_CHILD and rel.person_1_id == person_id and rel.person_2_id in person_dict
    ]


def _get_spouse(person_id: UUID, relations: List[Relation], persons: List[Person]) -> Optional[Person]:
    person_dict = {p.id: p for p in persons}
    for rel in relations:
        if rel.type == RelationTypeEnum.SPOUSE:
            if rel.person_1_id == person_id and rel.person_2_id in person_dict:
                return person_dict[rel.person_2_id]
            elif rel.person_2_id == person_id and rel.person_1_id in person_dict:
                return person_dict[rel.person_1_id]
    return None


def _get_siblings(person_id: UUID, relations: List[Relation], persons: List[Person]) -> List[Person]:
    person_dict = {p.id: p for p in persons}
    parent_ids = {
        rel.person_1_id
        for rel in relations
        if rel.type == RelationTypeEnum.PARENT_CHILD and rel.person_2_id == person_id
    }
    if not parent_ids:
        return []

    siblings = []
    for rel in relations:
        if rel.type == RelationTypeEnum.PARENT_CHILD and rel.person_1_id in parent_ids:
            child_id = rel.person_2_id
            if child_id != person_id and child_id in person_dict and child_id not in [s.id for s in siblings]:
                siblings.append(person_dict[child_id])
    return siblings


def _generate_family_graph(persons: List[Person], relations: List[Relation]):
    try:
        fig, ax = plt.subplots(figsize=(10, 8))
        n = len(persons)
        if n == 0:
            return None
        angles = np.linspace(0, 2 * np.pi, n, endpoint=False)
        radius = 3
        positions = {}
        for i, person in enumerate(persons):
            x = float(radius * np.cos(angles[i]))
            y = float(radius * np.sin(angles[i]))
            positions[person.id] = (x, y)
            gender_val = str(person.gender).lower() if person.gender else ""
            color = '#3498db' if 'male' in gender_val else '#e74c3c'
            circle = plt.Circle((x, y), 0.3, color=color, alpha=0.7, zorder=2)
            ax.add_patch(circle)
            name = f"{str(person.first_name)}\n{str(person.last_name)}"
            ax.text(x, y, str(name), ha='center', va='center', fontsize=8, fontweight='bold', zorder=3)
        for rel in relations:
            if rel.person_1_id in positions and rel.person_2_id in positions:
                x1, y1 = positions[rel.person_1_id]
                x2, y2 = positions[rel.person_2_id]
                rel_type = str(rel.type).lower()
                if 'spouse' in rel_type:
                    ax.plot([x1, x2], [y1, y2], 'k-', linewidth=2, alpha=0.6, zorder=1)
                else:
                    ax.plot([x1, x2], [y1, y2], 'g--', linewidth=1.5, alpha=0.6, zorder=1)
        ax.set_xlim(-4, 4)
        ax.set_ylim(-4, 4)
        ax.set_aspect('equal')
        ax.axis('off')
        legend_elements = [
            mpatches.Patch(color='#3498db', label='Мужчина'),
            mpatches.Patch(color='#e74c3c', label='Женщина'),
            plt.Line2D([0], [0], color='k', linewidth=2, label='Супруги'),
            plt.Line2D([0], [0], color='g', linestyle='--', linewidth=1.5, label='Родитель-ребёнок')
        ]
        ax.legend(handles=legend_elements, loc='upper right', fontsize=9)
        ax.set_title('Граф семьи', fontsize=16, fontweight='bold', pad=20)
        return fig
    except Exception as e:
        print(f"Ошибка генерации графа: {e}")
        return None


def _add_person_card(pdf: FPDF, person: Person, relations: List[Relation],
                     all_persons: List[Person], life_events: List[LifeEvent]):
    """Добавляет страницу с карточкой персоны. Фото сверху по центру, ФИО под фото."""

    # === ФОТО ПЕРСОНЫ (если есть) ===
    photo_added = False
    if person.photo_url:
        photo_path = f"/app/app/{str(person.photo_url).lstrip('/')}"
        if os.path.exists(photo_path):
            try:
                # Фото по центру страницы, ширина 60мм
                photo_x = 75  # (210 - 60) / 2 = 75
                pdf.image(photo_path, x=photo_x, y=pdf.get_y(), w=60)
                # Перенос после фото (высота фото ~60мм + отступ)
                pdf.ln(65)
                photo_added = True
            except Exception as e:
                print(f"Ошибка добавления фото: {e}")

    # Если фото не добавлено, делаем небольшой отступ сверху
    if not photo_added:
        pdf.ln(5)

    # === ФИО ПЕРСОНЫ ===
    pdf.set_font('DejaVu', 'B', 20)
    pdf.set_text_color(44, 62, 80)
    full_name = _format_full_name(person)
    pdf.cell(0, 15, str(full_name), 0, 1, 'C')  # По центру
    pdf.ln(5)

    # === ОСНОВНАЯ ИНФОРМАЦИЯ ===
    pdf.set_font('DejaVu', '', 11)
    pdf.set_text_color(52, 73, 94)

    gender_text = "Не указан"
    if person.gender:
        gender_val = str(person.gender.value).lower() if hasattr(person.gender, 'value') else str(person.gender).lower()
        if gender_val == 'male':
            gender_text = "Мужской"
        elif gender_val == 'female':
            gender_text = "Женский"
    pdf.cell(100, 8, str(f"Пол: {gender_text}"), 0, 1)

    birth_text = str(person.birth_date.strftime("%d.%m.%Y")) if person.birth_date else "—"
    pdf.cell(100, 8, str(f"Дата рождения: {birth_text}"), 0, 1)

    birth_place = str(person.birth_place) if person.birth_place else "—"
    pdf.cell(100, 8, str(f"Место рождения: {birth_place}"), 0, 1)

    age = _calculate_age(person.birth_date, person.death_date)
    if age and 0 < age < 120:
        pdf.cell(100, 8, str(f"Возраст: {age}{_get_age_suffix(age)}"), 0, 1)

    if person.death_date:
        death_text = str(person.death_date.strftime("%d.%m.%Y"))
        pdf.cell(100, 8, str(f"Дата смерти: {death_text}"), 0, 1)
        if hasattr(person, 'burial_place') and person.burial_place:
            pdf.cell(100, 8, str(f"Место погребения: {person.burial_place}"), 0, 1)

    pdf.ln(5)

    # === РОДИТЕЛИ ===
    parents = _get_parents(person.id, relations, all_persons)
    if parents:
        pdf.set_font('DejaVu', 'B', 14)
        pdf.set_text_color(44, 62, 80)
        pdf.cell(0, 8, 'Родители:', 0, 1)
        pdf.set_font('DejaVu', '', 11)
        pdf.set_text_color(52, 73, 94)
        for parent in parents:
            pdf.cell(0, 8, str(f"• {_format_full_name(parent)}"), 0, 1)
        pdf.ln(3)

    # === СУПРУГ(А) ===
    spouse = _get_spouse(person.id, relations, all_persons)
    if spouse:
        pdf.set_font('DejaVu', 'B', 14)
        pdf.set_text_color(44, 62, 80)
        pdf.cell(0, 8, 'Супруг(а):', 0, 1)
        pdf.set_font('DejaVu', '', 11)
        pdf.set_text_color(52, 73, 94)
        pdf.cell(0, 8, str(f"• {_format_full_name(spouse)}"), 0, 1)
        pdf.ln(3)

    # === ДЕТИ ===
    children = _get_children(person.id, relations, all_persons)
    if children:
        pdf.set_font('DejaVu', 'B', 14)
        pdf.set_text_color(44, 62, 80)
        pdf.cell(0, 8, 'Дети:', 0, 1)
        pdf.set_font('DejaVu', '', 11)
        pdf.set_text_color(52, 73, 94)
        for child in children:
            pdf.cell(0, 8, str(f"• {_format_full_name(child)}"), 0, 1)
        pdf.ln(3)

    # === БРАТЬЯ И СЁСТРЫ ===
    siblings = _get_siblings(person.id, relations, all_persons)
    if siblings:
        pdf.set_font('DejaVu', 'B', 14)
        pdf.set_text_color(44, 62, 80)
        pdf.cell(0, 8, 'Братья и сёстры:', 0, 1)
        pdf.set_font('DejaVu', '', 11)
        pdf.set_text_color(52, 73, 94)
        for sibling in siblings:
            pdf.cell(0, 8, str(f"• {_format_full_name(sibling)}"), 0, 1)
        pdf.ln(3)

    # === ЖИЗНЕННЫЕ СОБЫТИЯ ===
    person_events = [e for e in life_events if e.person_id == person.id]
    if person_events:
        pdf.ln(5)
        pdf.set_font('DejaVu', 'B', 14)
        pdf.set_text_color(44, 62, 80)
        pdf.cell(0, 10, 'Жизненные события:', 0, 1)
        pdf.set_font('DejaVu', '', 11)
        pdf.set_text_color(52, 73, 94)

        event_types = {
            'education': 'Образование',
            'military_service': 'Военная служба',
            'work': 'Работа',
            'relocation': 'Переезд',
            'award': 'Награда',
            'other': 'Другое',
        }

        sorted_events = sorted(person_events, key=lambda e: e.date or date.min)
        for event in sorted_events:
            event_name = event_types.get(event.event_type, event.event_type)
            date_str = event.date.strftime("%d.%m.%Y") if event.date else "—"
            place_str = f" ({event.place})" if event.place else ""
            desc_str = f" — {event.description}" if event.description else ""
            approx_str = " (приблизительно)" if hasattr(event, 'date_approx') and event.date_approx else ""

            line = f"• {event_name}: {date_str}{approx_str}{place_str}{desc_str}"
            pdf.cell(0, 8, str(line), 0, 1)


class FamilyBookPDF(FPDF):
    def __init__(self, tree_name: str):
        super().__init__()
        self.tree_name = str(tree_name) if tree_name else "Без названия"

    def header(self):
        if self.page_no() > 1:
            self.set_font('DejaVu', '', 8)
            self.set_text_color(128, 128, 128)
            self.cell(0, 10, str(f'Книга рода: {self.tree_name}'), 0, 0, 'L')
            self.cell(0, 10, str(f'Стр. {self.page_no()}'), 0, 1, 'R')
            self.ln(5)

    def footer(self):
        self.set_y(-15)
        self.set_font('DejaVu', '', 8)
        self.set_text_color(128, 128, 128)
        self.cell(0, 10, str(f'Создано в Исток API • {datetime.now().strftime("%d.%m.%Y")}'), 0, 0, 'C')


async def generate_family_book_pdf(
        db: AsyncSession,
        tree_id: UUID,
        user_id: UUID
) -> bytes:
    try:
        tree_result = await db.execute(select(Tree).where(Tree.id == tree_id))
        tree = tree_result.scalar_one_or_none()
        if not tree:
            raise ValueError("Дерево не найдено")

        if not await check_tree_access(db, tree_id, user_id):
            raise ValueError("У вас нет доступа к этому дереву")

        tree_persons_result = await db.execute(
            select(Person)
            .join(TreePerson, TreePerson.person_id == Person.id)
            .where(TreePerson.tree_id == tree_id)
        )
        persons: List[Person] = list(tree_persons_result.scalars().all())

        person_ids = [p.id for p in persons]
        relations_result = await db.execute(
            select(Relation).where(
                (Relation.person_1_id.in_(person_ids)) |
                (Relation.person_2_id.in_(person_ids))
            )
        )
        relations: List[Relation] = list(relations_result.scalars().all())

        events_result = await db.execute(
            select(LifeEvent).where(LifeEvent.person_id.in_(person_ids))
        )
        life_events: List[LifeEvent] = list(events_result.scalars().all())

        pdf = FamilyBookPDF(tree_name=str(tree.name))

        if os.path.exists(FONT_PATH):
            pdf.add_font('DejaVu', '', FONT_PATH, uni=True)
        if os.path.exists(FONT_PATH_BOLD):
            pdf.add_font('DejaVu', 'B', FONT_PATH_BOLD, uni=True)

        # Титульная страница
        pdf.add_page()
        if os.path.exists(LOGO_PATH):
            try:
                pdf.image(LOGO_PATH, x=75, y=20, w=60)
            except Exception as e:
                print(f"Ошибка добавления логотипа: {e}")

        pdf.set_y(115)
        pdf.set_font('DejaVu', 'B', 32)
        pdf.set_text_color(44, 62, 80)
        pdf.cell(0, 20, str(tree.name), 0, 1, 'C')

        pdf.set_font('DejaVu', '', 16)
        pdf.set_text_color(127, 140, 141)
        pdf.cell(0, 12, 'Книга рода', 0, 1, 'C')
        pdf.ln(15)

        pdf.set_font('DejaVu', '', 12)
        pdf.set_text_color(52, 73, 94)
        pdf.cell(0, 10, str(f'Количество персон: {len(persons)}'), 0, 1, 'C')
        pdf.cell(0, 10, str(f'Количество связей: {len(relations)}'), 0, 1, 'C')

        created_at_str = tree.created_at.strftime("%d.%m.%Y") if tree.created_at else "—"
        pdf.cell(0, 10, str(f'Дата создания: {created_at_str}'), 0, 1, 'C')

        pdf.ln(10)
        pdf.set_font('DejaVu', '', 10)
        pdf.set_text_color(127, 140, 141)
        pdf.cell(0, 10, str(f'Создано в Исток API • {datetime.now().strftime("%d.%m.%Y")}'), 0, 1, 'C')

        if persons:
            graph_image = _generate_family_graph(persons, relations)
            pdf.add_page()
            pdf.set_font('DejaVu', 'B', 20)
            pdf.set_text_color(44, 62, 80)
            pdf.cell(0, 15, 'Граф семьи', 0, 1, 'C')
            pdf.ln(5)

            if graph_image:
                temp_graph_path = "/tmp/family_graph.png"
                graph_image.savefig(temp_graph_path, dpi=150, bbox_inches='tight',
                                    facecolor='white', edgecolor='none')
                plt.close(graph_image)

                pdf.image(temp_graph_path, x=10, y=pdf.get_y(), w=190)

                if os.path.exists(temp_graph_path):
                    os.remove(temp_graph_path)

        for person in persons:
            pdf.add_page()
            _add_person_card(pdf, person, relations, persons, life_events)

        pdf_bytes = pdf.output()
        if isinstance(pdf_bytes, bytearray):
            return bytes(pdf_bytes)
        return pdf_bytes

    except Exception as e:
        tb = traceback.format_exc()
        print(f"=== PDF GENERATION ERROR ===\n{tb}\n==============================")
        raise ValueError(f"Ошибка генерации PDF: {str(e)}\n\nТрассировка:\n{tb}")