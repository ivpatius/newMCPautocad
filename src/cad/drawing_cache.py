"""
Модуль ПОЛНОГО кэширования чертежа AutoCAD.
✅ Кэш сущностей для быстрого доступа по handle
✅ Использование dataclasses для структурированных данных
"""
import json
import os
import pythoncom
import logging
from typing import Dict, List, Any, Optional
from datetime import datetime
from .autocad_client import AutoCADClient
from .dataclasses import (
    EntityCache, EntityProperties, LayerInfo,
    BlockReference, TextEntity, DimensionEntity,
    DrawingMetadata, BoundingBox
)
from .geometry_analysis import GeometryAnalyzer

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

CACHE_FILE = "drawing_cache.json"


class DrawingCache:
    """
    Полный кэш данных чертежа AutoCAD.
    ✅ Быстрый доступ по handle
    ✅ Полная геометрия и bounding box для всех сущностей
    """

    def __init__(self, acad_client: AutoCADClient):
        self.client = acad_client
        self.entity_cache = EntityCache()

    def full_cache_update(self):
        """Полное обновление ВСЕХ данных чертежа."""
        logger.info("🔄 Starting full drawing scan...")
        pythoncom.CoInitialize()

        try:
            # Сброс кэша
            self.entity_cache = EntityCache()

            doc = self.client.doc

            # Сбор метаданных
            self.entity_cache.metadata = self.client.get_drawing_metadata()

            # Сбор слоёв
            layers = self.client.get_layers_info()
            self.entity_cache.layers = {l.name: l for l in layers}

            # Сбор всех сущностей с полной геометрией
            entities = self.client.get_all_entities_detailed(
                include_xdata=True,
                include_dict=True
            )
            self.entity_cache.entities = {e.handle: e for e in entities}

            # Разделение по типам
            self._categorize_entities(entities)

            # Генерация сводки
            self._generate_summary()

            self.entity_cache.last_updated = datetime.now()
            self._save_cache()

            logger.info(
                f"✅ Cache updated: {len(self.entity_cache.entities)} entities, "
                f"{len(self.entity_cache.blocks)} blocks, "
                f"{len(self.entity_cache.texts)} texts, "
                f"{len(self.entity_cache.dimensions)} dimensions."
            )

        except Exception as e:
            logger.error(f"❌ Cache update error: {e}", exc_info=True)
            self.entity_cache.last_updated = datetime.now()
            self._save_cache()
            logger.warning("⚠️ Cache partially saved.")
        finally:
            pythoncom.CoUninitialize()

    def _categorize_entities(self, entities: List[EntityProperties]):
        """Разделение сущностей по категориям."""
        for entity in entities:
            obj_name = entity.object_name

            if obj_name == "AcDbBlockReference":
                self.entity_cache.blocks[entity.handle] = self._convert_to_block(entity)
            elif obj_name in ["AcDbText", "AcDbMText"]:
                self.entity_cache.texts[entity.handle] = self._convert_to_text(entity)
            elif "AcDbDimension" in obj_name:
                self.entity_cache.dimensions[entity.handle] = self._convert_to_dimension(entity)

    def _convert_to_block(self, entity: EntityProperties) -> BlockReference:
        """Конвертация в BlockReference."""
        tp = entity.type_properties
        scale = tp.get("scale_factors", {"x": 1, "y": 1, "z": 1})
        return BlockReference(
            handle=entity.handle,
            name=tp.get("block_name", ""),
            effective_name=tp.get("effective_name", ""),
            layer=entity.layer,
            insertion_point=entity.coordinates.insertion or [0, 0, 0],
            scale_x=scale.get("x", 1),
            scale_y=scale.get("y", 1),
            scale_z=scale.get("z", 1),
            rotation=tp.get("rotation", 0),
            attributes=tp.get("attributes", [])
        )

    def _convert_to_text(self, entity: EntityProperties) -> TextEntity:
        """Конвертация в TextEntity."""
        tp = entity.type_properties
        return TextEntity(
            handle=entity.handle,
            text=tp.get("text_string", ""),
            layer=entity.layer,
            height=tp.get("height", 0),
            style=tp.get("style_name", ""),
            position=entity.coordinates.insertion or entity.coordinates.center or [0, 0, 0],
            rotation=tp.get("rotation", 0),
            width=tp.get("width"),
            attachment_point=tp.get("attachment_point")
        )

    def _convert_to_dimension(self, entity: EntityProperties) -> DimensionEntity:
        """Конвертация в DimensionEntity."""
        tp = entity.type_properties
        return DimensionEntity(
            handle=entity.handle,
            dim_type=tp.get("dimension_type", 0),
            measurement=tp.get("measurement", 0),
            text=tp.get("text_string", ""),
            style=tp.get("style_name", ""),
            scale_factor=tp.get("linear_scale_factor", 1),
            position=entity.coordinates.center or [0, 0, 0],
            rotation=tp.get("rotation", 0)
        )

    def _save_cache(self):
        """Сохранение кэша в файл."""
        try:
            with open(CACHE_FILE, 'w', encoding='utf-8') as f:
                json.dump(self.entity_cache.to_dict(), f, indent=2, ensure_ascii=False, default=str)
            logger.info(f"💾 Cache saved to {CACHE_FILE}")
        except Exception as e:
            logger.error(f"⚠️ Failed to save cache: {e}", exc_info=True)

    def _generate_summary(self):
        """Генерация сводной статистики."""
        stats = GeometryAnalyzer.calculate_statistics(
            list(self.entity_cache.entities.values())
        )
        self.entity_cache.metadata.drawing_name = self.entity_cache.metadata.drawing_name
        logger.info(f"Summary generated: {stats}")

    # ========== БЫСТРЫЙ ДОСТУП ПО HANDLE ==========

    def get_entity_by_handle(self, handle: str) -> Optional[EntityProperties]:
        """Быстрый поиск сущности по handle."""
        return self.entity_cache.get_entity_by_handle(handle)

    def get_entities_by_layer(self, layer: str) -> List[EntityProperties]:
        """Получить все сущности на слое."""
        return self.entity_cache.get_all_entities_by_layer(layer)

    def get_entities_by_type(self, object_name: str) -> List[EntityProperties]:
        """Получить все сущности по типу."""
        return self.entity_cache.get_all_entities_by_type(object_name)

    def find_in_bbox(self, bbox: BoundingBox) -> List[EntityProperties]:
        """Найти сущности в bounding box."""
        return self.entity_cache.find_entities_in_bbox(bbox)

    # ========== АНАЛИЗ ГЕОМЕТРИИ ==========

    def find_connected_lines(self, tolerance: float = 0.001) -> Dict[str, List[str]]:
        """Найти соединённые линии."""
        return GeometryAnalyzer.find_connected_lines(
            list(self.entity_cache.entities.values()),
            tolerance
        )

    def find_nearby_entities(self, point: tuple, distance: float) -> List[EntityProperties]:
        """Найти сущности вблизи точки."""
        return GeometryAnalyzer.find_nearby_entities(
            list(self.entity_cache.entities.values()),
            point,
            distance
        )

    # ========== ЗАГРУЗКА КЭША ==========

    @staticmethod
    def load_cache() -> Optional[Dict[str, Any]]:
        """Загружает кэш из файла."""
        if not os.path.exists(CACHE_FILE):
            logger.warning("Cache file not found.")
            return None

        try:
            with open(CACHE_FILE, 'r', encoding='utf-8') as f:
                data = json.load(f)

            if 'metadata' not in data:
                logger.warning("Invalid cache format.")
                return None

            return data
        except Exception as e:
            logger.error(f"Cache load error: {e}", exc_info=True)
            return None