"""
Модуль анализа геометрии: поиск связей между объектами,
расчёт bounding boxes, пространственные запросы.
"""
import logging
from typing import List, Dict, Any, Optional, Tuple, Set
from .dataclasses import EntityProperties, BoundingBox

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class GeometryAnalyzer:
    """
    Анализ геометрии AutoCAD объектов.
    ✅ Поиск связей между объектами
    ✅ Расчёт bounding boxes
    ✅ Пространственные запросы
    """

    @staticmethod
    def calculate_combined_bbox(entities: List[EntityProperties]) -> Optional[BoundingBox]:
        """Вычислить объединённый bounding box для списка сущностей."""
        if not entities:
            return None

        valid_boxes = [e.bounding_box for e in entities if e.bounding_box]
        if not valid_boxes:
            return None

        min_x = min(b.min_x for b in valid_boxes)
        min_y = min(b.min_y for b in valid_boxes)
        min_z = min(b.min_z for b in valid_boxes)
        max_x = max(b.max_x for b in valid_boxes)
        max_y = max(b.max_y for b in valid_boxes)
        max_z = max(b.max_z for b in valid_boxes)

        return BoundingBox(min_x, min_y, min_z, max_x, max_y, max_z)

    @staticmethod
    def find_intersecting_entities(entities: List[EntityProperties],
                                   target: EntityProperties) -> List[EntityProperties]:
        """Найти сущности, пересекающиеся с целевой (по bounding box)."""
        if not target.bounding_box:
            return []

        result = []
        for entity in entities:
            if entity.handle == target.handle:
                continue
            if entity.bounding_box and GeometryAnalyzer._bbox_intersects(
                    target.bounding_box, entity.bounding_box
            ):
                result.append(entity)

        logger.info(f"Found {len(result)} entities intersecting with {target.handle}")
        return result

    @staticmethod
    def _bbox_intersects(box1: BoundingBox, box2: BoundingBox) -> bool:
        """Проверка пересечения двух bounding boxes."""
        return not (
                box1.max_x < box2.min_x or box1.min_x > box2.max_x or
                box1.max_y < box2.min_y or box1.min_y > box2.max_y or
                box1.max_z < box2.min_z or box1.min_z > box2.max_z
        )

    @staticmethod
    def find_nearby_entities(entities: List[EntityProperties],
                             point: Tuple[float, float, float],
                             distance: float) -> List[EntityProperties]:
        """Найти сущности вблизи указанной точки."""
        result = []
        x, y, z = point

        for entity in entities:
            if entity.bounding_box:
                bb = entity.bounding_box
                # Быстрая проверка по bounding box
                if (bb.min_x - distance <= x <= bb.max_x + distance and
                        bb.min_y - distance <= y <= bb.max_y + distance and
                        bb.min_z - distance <= z <= bb.max_z + distance):
                    result.append(entity)

        logger.info(f"Found {len(result)} entities within {distance} units of point {point}")
        return result

    @staticmethod
    def find_entities_by_layer(entities: List[EntityProperties],
                               layer: str) -> List[EntityProperties]:
        """Найти все сущности на указанном слое."""
        result = [e for e in entities if e.layer == layer]
        logger.info(f"Found {len(result)} entities on layer '{layer}'")
        return result

    @staticmethod
    def find_entities_by_type(entities: List[EntityProperties],
                              object_name: str) -> List[EntityProperties]:
        """Найти все сущности указанного типа."""
        result = [e for e in entities if e.object_name == object_name]
        logger.info(f"Found {len(result)} entities of type '{object_name}'")
        return result

    @staticmethod
    def find_connected_lines(entities: List[EntityProperties],
                             tolerance: float = 0.001) -> Dict[str, List[str]]:
        """
        Найти соединённые линии (конечная точка одной = начальная другой).
        Возвращает словарь: handle -> list of connected handles.
        """
        lines = [e for e in entities if e.object_name == "AcDbLine"]
        connections: Dict[str, List[str]] = {}

        for line in lines:
            connections[line.handle] = []
            if not line.coordinates or not line.coordinates.start or not line.coordinates.end:
                continue

            start = line.coordinates.start
            end = line.coordinates.end

            for other in lines:
                if other.handle == line.handle:
                    continue
                if not other.coordinates or not other.coordinates.start or not other.coordinates.end:
                    continue

                other_start = other.coordinates.start
                other_end = other.coordinates.end

                # Проверка соединения
                if (GeometryAnalyzer._points_near(end, other_start, tolerance) or
                        GeometryAnalyzer._points_near(end, other_end, tolerance) or
                        GeometryAnalyzer._points_near(start, other_start, tolerance) or
                        GeometryAnalyzer._points_near(start, other_end, tolerance)):
                    connections[line.handle].append(other.handle)

        logger.info(f"Found connections for {len(connections)} lines")
        return connections

    @staticmethod
    def _points_near(p1: List[float], p2: List[float], tolerance: float) -> bool:
        """Проверка близости двух точек."""
        if len(p1) < 3 or len(p2) < 3:
            return False
        return (abs(p1[0] - p2[0]) < tolerance and
                abs(p1[1] - p2[1]) < tolerance and
                abs(p1[2] - p2[2]) < tolerance)

    @staticmethod
    def group_entities_by_spatial_proximity(entities: List[EntityProperties],
                                            max_distance: float) -> List[List[EntityProperties]]:
        """
        Сгруппировать сущности по пространственной близости.
        Использует простой алгоритм кластеризации.
        """
        if not entities:
            return []

        valid_entities = [e for e in entities if e.bounding_box]
        if not valid_entities:
            return []

        groups: List[List[EntityProperties]] = []
        used: Set[str] = set()

        for entity in valid_entities:
            if entity.handle in used:
                continue

            group = [entity]
            used.add(entity.handle)

            for other in valid_entities:
                if other.handle in used:
                    continue

                if GeometryAnalyzer._entities_near(entity, other, max_distance):
                    group.append(other)
                    used.add(other.handle)

            groups.append(group)

        logger.info(f"Grouped {len(valid_entities)} entities into {len(groups)} clusters")
        return groups

    @staticmethod
    def _entities_near(e1: EntityProperties, e2: EntityProperties,
                       max_distance: float) -> bool:
        """Проверка близости двух сущностей по их bounding boxes."""
        if not e1.bounding_box or not e2.bounding_box:
            return False

        b1, b2 = e1.bounding_box, e2.bounding_box

        # Минимальное расстояние между bounding boxes
        dx = max(0, max(b1.min_x - b2.max_x, b2.min_x - b1.max_x))
        dy = max(0, max(b1.min_y - b2.max_y, b2.min_y - b1.max_y))
        dz = max(0, max(b1.min_z - b2.max_z, b2.min_z - b1.max_z))

        distance = (dx ** 2 + dy ** 2 + dz ** 2) ** 0.5
        return distance <= max_distance

    @staticmethod
    def calculate_statistics(entities: List[EntityProperties]) -> Dict[str, Any]:
        """Расчёт статистики по сущностям."""
        stats = {
            "total_count": len(entities),
            "by_type": {},
            "by_layer": {},
            "total_area": 0.0,
            "total_length": 0.0,
            "entities_with_bbox": 0
        }

        for entity in entities:
            # По типу
            type_name = entity.object_name
            stats["by_type"][type_name] = stats["by_type"].get(type_name, 0) + 1

            # По слою
            layer_name = entity.layer
            stats["by_layer"][layer_name] = stats["by_layer"].get(layer_name, 0) + 1

            # Площадь и длина
            if entity.area:
                stats["total_area"] += entity.area
            if entity.length:
                stats["total_length"] += entity.length

            # Bounding box
            if entity.bounding_box:
                stats["entities_with_bbox"] += 1

        logger.info(f"Statistics calculated for {len(entities)} entities")
        return stats