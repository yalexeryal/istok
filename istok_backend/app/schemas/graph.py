from pydantic import BaseModel
from typing import List, Optional

class GraphNode(BaseModel):
    id: str
    first_name: str
    last_name: str
    middle_name: Optional[str] = None
    birth_date: Optional[str] = None
    death_date: Optional[str] = None
    gender: Optional[str] = None
    photo_url: Optional[str] = None

class GraphEdge(BaseModel):
    id: str
    source: str  # UUID родителя или первого супруга
    target: str  # UUID ребенка или второго супруга
    type: str    # parent_child, spouse, sibling

class TreeGraphResponse(BaseModel):
    nodes: List[GraphNode]
    edges: List[GraphEdge]