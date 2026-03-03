"""
Типизированные структуры данных для AutoCAD entities.
Использует dataclasses для строгой типизации и валидации.
"""
from dataclasses import dataclass, field
from typing import Optional, Dict, List, Any, Tuple
from datetime import datetime


@dataclass
class BoundingBox:
    """Ограничивающий прямоугольник 3D объекта."""
    min_x: float
    min_y: float
    min_z: float
    max_x: float
    max_y: float
    max_z: float

    @property
    def center(self) -> Tuple[float, float, float]:
        return (
            (self.min_x + self.max_x) / 2,
            (self.min_y + self.max_y) / 2,
            (self.min_z + self.max_z) / 2
        )

    @property
    def size(self) -> Tuple[float, float, float]:
        return (
            self.max_x - self.min_x,
            self.max_y - self.min_y,
            self.max_z - self.min_z
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "min": [self.min_x, self.min_y, self.min_z],
            "max": [self.max_x, self.max_y, self.max_z],
            "center": list(self.center),
            "size": list(self.size)
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "BoundingBox":
        min_pt = data.get("min", [0, 0, 0])
        max_pt = data.get("max", [0, 0, 0])
        return cls(
            min_x=float(min_pt[0]), min_y=float(min_pt[1]), min_z=float(min_pt[2]),
            max_x=float(max_pt[0]), max_y=float(max_pt[1]), max_z=float(max_pt[2])
        )


@dataclass
class Coordinates:
    """Координаты объекта в зависимости от типа."""
    start: Optional[List[float]] = None
    end: Optional[List[float]] = None
    center: Optional[List[float]] = None
    insertion: Optional[List[float]] = None
    vertices: List[List[float]] = field(default_factory=list)
    point: Optional[List[float]] = None

    def to_dict(self) -> Dict[str, Any]:
        result = {}
        for attr in ["start", "end", "center", "insertion", "vertices", "point"]:
            val = getattr(self, attr)
            if val:
                result[attr] = val
        return result


@dataclass
class EntityProperties:
    """Общие свойства всех AutoCAD объектов."""
    handle: str
    object_name: str
    layer: str
    color: int
    linetype: str
    lineweight: Optional[int] = None
    transparency: Optional[int] = None
    visible: bool = True
    bounding_box: Optional[BoundingBox] = None
    area: Optional[float] = None
    length: Optional[float] = None
    volume: Optional[float] = None
    coordinates: Coordinates = field(default_factory=Coordinates)
    xdata: Optional[Dict[str, Any]] = None
    extension_dict: Optional[Dict[str, Any]] = None
    type_properties: Dict[str, Any] = field(default_factory=dict)
    error: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "handle": self.handle,
            "object_name": self.object_name,
            "layer": self.layer,
            "color": self.color,
            "linetype": self.linetype,
            "lineweight": self.lineweight,
            "transparency": self.transparency,
            "visible": self.visible,
            "bounding_box": self.bounding_box.to_dict() if self.bounding_box else None,
            "area": self.area,
            "length": self.length,
            "volume": self.volume,
            "coordinates": self.coordinates.to_dict(),
            "xdata": self.xdata,
            "extension_dict": self.extension_dict,
            "type_properties": self.type_properties,
            "error": self.error
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "EntityProperties":
        bbox = None
        if data.get("bounding_box"):
            bbox = BoundingBox.from_dict(data["bounding_box"])

        coords = Coordinates()
        if data.get("coordinates"):
            coord_data = data["coordinates"]
            for attr in ["start", "end", "center", "insertion", "vertices", "point"]:
                if attr in coord_data:
                    setattr(coords, attr, coord_data[attr])

        return cls(
            handle=str(data.get("handle", "UNKNOWN")),
            object_name=str(data.get("object_name", "Unknown")),
            layer=str(data.get("layer", "0")),
            color=int(data.get("color", 7)),
            linetype=str(data.get("linetype", "ByLayer")),
            lineweight=data.get("lineweight"),
            transparency=data.get("transparency"),
            visible=bool(data.get("visible", True)),
            bounding_box=bbox,
            area=data.get("area"),
            length=data.get("length"),
            volume=data.get("volume"),
            coordinates=coords,
            xdata=data.get("xdata"),
            extension_dict=data.get("extension_dict"),
            type_properties=data.get("type_properties", {}),
            error=data.get("error")
        )


@dataclass
class LayerInfo:
    """Информация о слое."""
    name: str
    color: int
    linetype: str
    lineweight: int
    is_on: bool
    is_frozen: bool
    is_locked: bool
    viewport_frozen: bool = False
    plot: bool = True
    description: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "color": self.color,
            "linetype": self.linetype,
            "lineweight": self.lineweight,
            "on": self.is_on,
            "frozen": self.is_frozen,
            "locked": self.is_locked,
            "viewport_frozen": self.viewport_frozen,
            "plot": self.plot,
            "description": self.description
        }


@dataclass
class BlockReference:
    """Вхождение блока."""
    handle: str
    name: str
    effective_name: str
    layer: str
    insertion_point: List[float]
    scale_x: float
    scale_y: float
    scale_z: float
    rotation: float
    attributes: List[Dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "handle": self.handle,
            "name": self.name,
            "effective_name": self.effective_name,
            "layer": self.layer,
            "insertion_point": self.insertion_point,
            "scale": {"x": self.scale_x, "y": self.scale_y, "z": self.scale_z},
            "rotation": self.rotation,
            "attributes": self.attributes
        }


@dataclass
class TextEntity:
    """Текстовый объект."""
    handle: str
    text: str
    layer: str
    height: float
    style: str
    position: List[float]
    alignment: Any = None
    rotation: float = 0
    width: Optional[float] = None
    attachment_point: Optional[int] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "handle": self.handle,
            "text": self.text,
            "layer": self.layer,
            "height": self.height,
            "style": self.style,
            "position": self.position,
            "alignment": self.alignment,
            "rotation": self.rotation,
            "width": self.width,
            "attachment_point": self.attachment_point
        }


@dataclass
class DimensionEntity:
    """Размерный объект."""
    handle: str
    dim_type: int
    measurement: float
    text: str
    style: str
    scale_factor: float
    position: List[float]
    rotation: float = 0
    center: Optional[List[float]] = None
    radius: Optional[float] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "handle": self.handle,
            "dim_type": self.dim_type,
            "measurement": self.measurement,
            "text": self.text,
            "style": self.style,
            "scale_factor": self.scale_factor,
            "position": self.position,
            "rotation": self.rotation,
            "center": self.center,
            "radius": self.radius
        }


@dataclass
class DrawingMetadata:
    """Метаданные чертежа."""
    drawing_name: Optional[str] = None
    drawing_path: Optional[str] = None
    last_update: Optional[str] = None
    acad_version: Optional[str] = None
    created_by: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "drawing_name": self.drawing_name,
            "drawing_path": self.drawing_path,
            "last_update": self.last_update,
            "acad_version": self.acad_version,
            "created_by": self.created_by
        }


@dataclass
class EntityCache:
    """Кэш сущностей с быстрым доступом по handle."""
    entities: Dict[str, EntityProperties] = field(default_factory=dict)
    blocks: Dict[str, BlockReference] = field(default_factory=dict)
    texts: Dict[str, TextEntity] = field(default_factory=dict)
    dimensions: Dict[str, DimensionEntity] = field(default_factory=dict)
    layers: Dict[str, LayerInfo] = field(default_factory=dict)
    metadata: DrawingMetadata = field(default_factory=DrawingMetadata)
    last_updated: Optional[datetime] = None

    def get_entity_by_handle(self, handle: str) -> Optional[EntityProperties]:
        """Быстрый поиск сущности по handle."""
        return self.entities.get(handle)

    def get_all_entities_by_layer(self, layer: str) -> List[EntityProperties]:
        """Получить все сущности на слое."""
        return [e for e in self.entities.values() if e.layer == layer]

    def get_all_entities_by_type(self, object_name: str) -> List[EntityProperties]:
        """Получить все сущности по типу."""
        return [e for e in self.entities.values() if e.object_name == object_name]

    def find_entities_in_bbox(self, bbox: BoundingBox) -> List[EntityProperties]:
        """Найти все сущности в ограничивающем прямоугольнике."""
        result = []
        for entity in self.entities.values():
            if entity.bounding_box:
                eb = entity.bounding_box
                if not (eb.max_x < bbox.min_x or eb.min_x > bbox.max_x or
                        eb.max_y < bbox.min_y or eb.min_y > bbox.max_y or
                        eb.max_z < bbox.min_z or eb.min_z > bbox.max_z):
                    result.append(entity)
        return result

    def to_dict(self) -> Dict[str, Any]:
        return {
            "metadata": self.metadata.to_dict(),
            "last_updated": self.last_updated.isoformat() if self.last_updated else None,
            "entities": [e.to_dict() for e in self.entities.values()],
            "blocks": [b.to_dict() for b in self.blocks.values()],
            "texts": [t.to_dict() for t in self.texts.values()],
            "dimensions": [d.to_dict() for d in self.dimensions.values()],
            "layers": [l.to_dict() for l in self.layers.values()]
        }