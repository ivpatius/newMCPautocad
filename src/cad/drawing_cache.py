"""
Модуль кэширования данных чертежа AutoCAD.
Использует AutoCADClient из autocad_client.py
"""
import json
import os
from typing import Dict, List, Any, Optional
from datetime import datetime
from .autocad_client import AutoCADClient

CACHE_FILE = "drawing_cache.json"

class DrawingCache:
    """Кэш данных чертежа AutoCAD."""

    def __init__(self, acad_client: AutoCADClient):
        self.client = acad_client
        self.cache_data = {
            "last_update": None,
            "entities": [],
            "summary": {}
        }

    def collect_all_entities(self) -> List[Dict[str, Any]]:
        """Собирает все примитивы из пространства модели."""
        entities = []
        try:
            doc = self.client.doc  # предполагается, что у AutoCADClient есть атрибут doc
            model_space = doc.ModelSpace

            for ent in model_space:
                entity_info = {
                    "handle": ent.Handle,
                    "object_name": ent.ObjectName,
                    "layer": ent.Layer,
                    "color": ent.Color,
                    "linetype": ent.Linetype,
                    "coordinates": self._extract_coordinates(ent)
                }
                # Типозависимые поля
                if ent.ObjectName == "AcDbLine":
                    entity_info["length"] = ent.Length
                    entity_info["angle"] = ent.Angle
                elif ent.ObjectName == "AcDbCircle":
                    entity_info["radius"] = ent.Radius
                    entity_info["center"] = [ent.Center[0], ent.Center[1], ent.Center[2]]
                elif ent.ObjectName == "AcDbArc":
                    entity_info["radius"] = ent.Radius
                    entity_info["start_angle"] = ent.StartAngle
                    entity_info["end_angle"] = ent.EndAngle
                # Добавьте другие типы при необходимости

                entities.append(entity_info)
        except Exception as e:
            print(f"[DrawingCache] Ошибка сбора данных: {e}")
        return entities

    def _extract_coordinates(self, entity) -> Dict:
        """Извлекает координаты в зависимости от типа объекта."""
        try:
            if hasattr(entity, 'StartPoint') and hasattr(entity, 'EndPoint'):
                return {
                    "start": [entity.StartPoint[0], entity.StartPoint[1], entity.StartPoint[2]],
                    "end": [entity.EndPoint[0], entity.EndPoint[1], entity.EndPoint[2]]
                }
            elif hasattr(entity, 'Center'):
                return {
                    "center": [entity.Center[0], entity.Center[1], entity.Center[2]]
                }
            elif hasattr(entity, 'InsertionPoint'):
                return {
                    "insertion": [entity.InsertionPoint[0], entity.InsertionPoint[1], entity.InsertionPoint[2]]
                }
            elif hasattr(entity, 'Coordinates'):
                return {"coordinates": list(entity.Coordinates)}
        except:
            pass
        return {}

    def generate_summary(self, entities: List[Dict]) -> Dict:
        """Сводка: кол-во объектов, типы, слои."""
        summary = {
            "total_entities": len(entities),
            "by_type": {},
            "by_layer": {},
            "bounds": self._get_drawing_bounds()
        }
        for ent in entities:
            obj_type = ent["object_name"]
            layer = ent["layer"]
            summary["by_type"][obj_type] = summary["by_type"].get(obj_type, 0) + 1
            summary["by_layer"][layer] = summary["by_layer"].get(layer, 0) + 1
        return summary

    def _get_drawing_bounds(self) -> Optional[Dict]:
        """Границы чертежа (Limits)."""
        try:
            doc = self.client.doc
            limmin = doc.GetVariable("LIMMIN")
            limmax = doc.GetVariable("LIMMAX")
            return {
                "min": [limmin[0], limmin[1]],
                "max": [limmax[0], limmax[1]]
            }
        except:
            return None

    def update_cache(self):
        """Основной метод: обновить кэш и сохранить в файл."""
        print("Обновление кэша чертежа...")
        self.cache_data["entities"] = self.collect_all_entities()
        self.cache_data["summary"] = self.generate_summary(self.cache_data["entities"])
        self.cache_data["last_update"] = datetime.now().isoformat()

        with open(CACHE_FILE, 'w', encoding='utf-8') as f:
            json.dump(self.cache_data, f, indent=2, ensure_ascii=False)
        print(f"Кэш сохранён: {len(self.cache_data['entities'])} объектов.")

    @staticmethod
    def load_cache() -> Dict:
        """Загрузить кэш из файла."""
        if os.path.exists(CACHE_FILE):
            with open(CACHE_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        return {"last_update": None, "entities": [], "summary": {}}