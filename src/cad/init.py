"""
CAD module for AutoCAD integration.
"""
from .autocad_client import AutoCADClient
from .drawing_cache import DrawingCache
from .dataclasses import (
    EntityProperties, BoundingBox, Coordinates,
    LayerInfo, BlockReference, TextEntity,
    DimensionEntity, DrawingMetadata, EntityCache
)
from .geometry_analysis import GeometryAnalyzer

__all__ = [
    'AutoCADClient',
    'DrawingCache',
    'EntityProperties',
    'BoundingBox',
    'Coordinates',
    'LayerInfo',
    'BlockReference',
    'TextEntity',
    'DimensionEntity',
    'DrawingMetadata',
    'EntityCache',
    'GeometryAnalyzer'
]