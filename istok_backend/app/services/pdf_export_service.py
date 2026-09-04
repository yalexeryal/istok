import os
import traceback
from uuid import UUID
from datetime import datetime
from typing import List

from fpdf import FPDF
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import numpy as np

from app.models.tree import Tree
from app.models.person import Person
from app.models.tree_person import TreePerson
from app.models.relation import Relation, RelationTypeEnum
from app.services.access_service import check_tree_access

FONT_PATH = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
FONT_PATH_BOLD = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"


class FamilyBookPDF(FPDF):
    def __init__(self, tree_name: str):
        super().__init__()
        self.tree_name = str(tree_name) if tree_name else "Без названия"

    def header(self):
        if self.page_no() > 1:
            self.set_font('DejaVu', '', 8)
            self.set_text_color(128, 128, 128)
            self.cell(0, 10, f'Книга рода: {self.tree_name}', 0, 0, 'L')
            self.cell(0, 10, f'Стр. {self.page_no()}', 0, 1, 'R')
            self.ln(5)

    def footer(self):
        self.set_y(-15)
        self.set_font('DejaVu', '', 8)
        self.set_text_color(128, 128, 128)
        self.cell(0, 10, f'Создано в Исток API • {datetime.now().strftime("%d.%m.%Y")}', 0, 0, 'C')


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

        pdf = FamilyBookPDF(tree_name=str(tree.name))

        if os.path.exists(FONT_PATH):
            pdf.add_font('DejaVu', '', FONT_PATH, uni=True)
        if os.path.exists(FONT_PATH_BOLD):
            pdf.add_font('DejaVu', 'B', FONT_PATH_BOLD, uni=True)

        # Титульная страница
        pdf.add_page()
        pdf.set_font('DejaVu', 'B', 32)
        pdf.set_text_color(44, 62, 80)
        pdf.ln(60)
        pdf.cell(0, 20, str(tree.name), 0, 1, 'C')

        pdf.set_font('DejaVu', '', 14)
        pdf.set_text_color(127, 140, 141)
        pdf.cell(0, 10, 'Книга рода', 0, 1, 'C')
        pdf.ln(20)

        pdf.set_font('DejaVu', '', 12)
        pdf.set_text_color(52, 73, 94)
        pdf.cell(0, 10, f'Количество персон: {len(persons)}', 0, 1, 'C')
        pdf.cell(0, 10, f'Количество связей: {len(relations)}', 0, 1, 'C')

        created_at_str = tree.created_at.strftime("%d.%m.%Y") if tree.created_at else "—"
        pdf.cell(0, 10, f'Дата создания: {created_at_str}', 0, 1, 'C')

        # Граф семьи
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

        # Карточки персон
        for person in persons:
            pdf.add_page()
            _add_person_card(pdf, person, relations, persons)

        pdf_bytes = pdf.output()
        if isinstance(pdf_bytes, bytearray):
            return bytes(pdf_bytes)
        return pdf_bytes

    except Exception as e:
        tb = traceback.format_exc()
        print(f"=== PDF GENERATION ERROR ===\n{tb}\n==============================")
        raise ValueError(f"Ошибка генерации PDF: {str(e)}\n\nТрассировка:\n{tb}")


def _generate_family_graph(persons: List[Person], relations: List[Relation]):
    try:
        fig, ax = plt.subplots(figsize=(10, 8))
        person_dict = {p.id: p for p in persons}

        n = len(persons)
        if n == 0:
            return None

        angles = np.linspace(0, 2 * np.pi, n, endpoint=False)
        radius = 3

        positions = {}
        for i, person in enumerate(persons):
            x = radius * np.cos(angles[i])
            y = radius * np.sin(angles[i])
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


def _add_person_card(pdf: FamilyBookPDF, person: Person, relations: List[Relation], all_persons: List[Person]):
    pdf.set_font('DejaVu', 'B', 20)
    pdf.set_text_color(44, 62, 80)

    last_name = str(person.last_name) if person.last_name else "Неизвестно"
    first_name = str(person.first_name) if person.first_name else "Неизвестно"
    middle_name = str(person.middle_name) if person.middle_name else ""

    full_name = f"{last_name} {first_name}"
    if middle_name:
        full_name += f" {middle_name}"

    pdf.cell(0, 15, str(full_name.strip()), 0, 1, 'L')

    if person.photo_url:
        photo_path = f"/app/{str(person.photo_url).lstrip('/')}"
        if os.path.exists(photo_path):
            try:
                pdf.image(photo_path, x=10, y=pdf.get_y(), w=40)
                pdf.set_x(60)
            except Exception:
                pdf.set_x(10)
        else:
            pdf.set_x(10)
    else:
        pdf.set_x(10)

    pdf.set_font('DejaVu', '', 11)
    pdf.set_text_color(52, 73, 94)

    gender_text = "Не указан"
    if person.gender:
        gender_val = str(person.gender.value).lower() if hasattr(person.gender, 'value') else str(person.gender).lower()
        if gender_val == 'male':
            gender_text = "Мужской"
        elif gender_val == 'female':
            gender_text = "Женский"

    pdf.cell(100, 8, f"Пол: {gender_text}", 0, 1)

    birth_text = str(person.birth_date.strftime("%d.%m.%Y")) if person.birth_date else "—"
    pdf.cell(100, 8, f"Дата рождения: {birth_text}", 0, 1)

    birth_place = str(person.birth_place) if person.birth_place else "—"
    pdf.cell(100, 8, f"Место рождения: {birth_place}", 0, 1)

    if person.death_date:
        death_text = str(person.death_date.strftime("%d.%m.%Y"))
        pdf.cell(100, 8, f"Дата смерти: {death_text}", 0, 1)

    pdf.ln(10)

    pdf.set_font('DejaVu', 'B', 14)
    pdf.set_text_color(44, 62, 80)
    pdf.cell(0, 10, 'Связи:', 0, 1)

    pdf.set_font('DejaVu', '', 11)
    pdf.set_text_color(52, 73, 94)

    person_dict = {p.id: p for p in all_persons}
    has_relations = False

    for rel in relations:
        related_person = None
        relation_type_text = ""

        if rel.person_1_id == person.id:
            related_person = person_dict.get(rel.person_2_id)
            rel_type = str(rel.type).lower()
            relation_type_text = "Супруг(а)" if 'spouse' in rel_type else "Ребёнок"
        elif rel.person_2_id == person.id:
            related_person = person_dict.get(rel.person_1_id)
            rel_type = str(rel.type).lower()
            relation_type_text = "Супруг(а)" if 'spouse' in rel_type else "Родитель"

        if related_person:
            has_relations = True
            rel_last = str(related_person.last_name) if related_person.last_name else ""
            rel_first = str(related_person.first_name) if related_person.first_name else ""
            related_name = f"{rel_last} {rel_first}".strip()
            pdf.cell(0, 8, f"• {relation_type_text}: {related_name}", 0, 1)

    if not has_relations:
        pdf.cell(0, 8, "• Связи не указаны", 0, 1)